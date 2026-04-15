"""
WebSocket chat router.

Handles:
  - WebSocket /ws/chat/{session_id}
  - Loads session, vector store, and memories on connect
  - Sends {"type": "ready"} before accepting messages
  - Builds session-scoped tools via make_tools() closure factory
  - Runs the agentic loop with streaming
  - Auto-titles session on first message (first 50 chars, no LLM call)
  - Persists updated chat history after each exchange
"""

import os
import json
import uuid
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.tools import make_tools
from core.llm import get_llm_with_tools
from core.vectorstore import load_session_vectorstore, release_session_store
from core.memory import load_memory
from core.agent import build_system_prompt, run_agent_streaming


router = APIRouter(tags=["chat"])


# ── Paths ────────────────────────────────────────────────────────────────────

CHATS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "chats",
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _read_session(session_id: str) -> dict | None:
    """Read a session JSON file."""
    path = os.path.join(CHATS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_session(session_id: str, data: dict) -> None:
    """Write a session JSON file."""
    os.makedirs(CHATS_DIR, exist_ok=True)
    path = os.path.join(CHATS_DIR, f"{session_id}.json")
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _rebuild_langchain_history(messages: list) -> list:
    """
    Reconstruct LangChain message objects from persisted session messages.
    Only user and assistant messages are needed for the LLM context.
    """
    from langchain_core.messages import HumanMessage, AIMessage

    history = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user" and content:
            history.append(HumanMessage(content=content))
        elif role == "assistant" and content:
            history.append(AIMessage(content=content))
    return history


def _serialize_message(
    role: str,
    content: str,
    attachments: list = None,
    tool_calls: list = None,
    thinking: str = None,
    diagrams: list = None,
) -> dict:
    """Create a message dict matching the session JSON format."""
    return {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attachments": attachments or [],
        "tool_calls": tool_calls or [],
        "thinking": thinking,
        "diagrams": diagrams or [],
    }


# ── WebSocket endpoint ───────────────────────────────────────────────────────


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    Main chat WebSocket.

    Flow:
      1. Accept connection
      2. Load session JSON + vector store + memories
      3. Send {"type": "ready", "has_notes": bool}
      4. Enter message loop: receive → agentic loop → stream → persist
      5. On disconnect: release_session_store()
    """
    await websocket.accept()

    try:
        # ── Load session ─────────────────────────────────────────────────
        session = await asyncio.to_thread(_read_session, session_id)
        if session is None:
            await websocket.send_json({
                "type": "error",
                "message": f"Session '{session_id}' not found.",
            })
            await websocket.close()
            return

        app = websocket.app
        has_notes = session.get("has_notes", False)

        # ── Load session's vector store (or None) ────────────────────────
        session_vs = None
        if has_notes:
            session_vs = await asyncio.to_thread(
                load_session_vectorstore,
                session_id,
                app.state.embedding_fn,
            )

        # ── Load memories (NOT a tool — injected into system prompt) ─────
        memories = await asyncio.to_thread(load_memory)

        # ── Send ready event ─────────────────────────────────────────────
        await websocket.send_json({
            "type": "ready",
            "has_notes": has_notes,
        })

        # ── Message loop ─────────────────────────────────────────────────
        while True:
            raw = await websocket.receive_text()

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON payload.",
                })
                continue

            message_text = payload.get("message", "").strip()
            image_base64 = payload.get("image_base64")
            enable_thinking = payload.get("enable_thinking", False)
            enable_verbose = payload.get("enable_verbose", False)
            enable_web_search = payload.get("enable_web_search", True)

            if not message_text and not image_base64:
                await websocket.send_json({
                    "type": "error",
                    "message": "Empty message.",
                })
                continue

            # ── Build multimodal content ─────────────────────────────────
            # Per Gemma 4 docs: image before text
            if image_base64:
                user_content = [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                        },
                    },
                    {"type": "text", "text": message_text},
                ]
            else:
                user_content = message_text

            # ── Build session-scoped tools via closures ──────────────────
            tools_list = make_tools(
                vector_store=session_vs,
                exa_client=app.state.exa_client,
                session_id=session_id,
                enable_web_search=enable_web_search,
            )
            llm_with_tools = get_llm_with_tools(app.state.llm, tools_list)

            # Tool map for execute_tool_call
            tool_map = {t.name: t for t in tools_list}

            # ── Build system prompt ──────────────────────────────────────
            # Get topics data if notes exist
            topics_data = None
            if session_vs is not None:
                from core.tools import list_topics_impl
                topics_json = await asyncio.to_thread(
                    list_topics_impl, session_vs
                )
                topics_data = json.loads(topics_json)

            system_prompt = build_system_prompt(
                topics_data=topics_data,
                memory_data=memories,
                has_notes=has_notes,
                enable_thinking=enable_thinking,
            )

            # ── Rebuild chat history from persisted messages ──────────────
            chat_history = _rebuild_langchain_history(session.get("messages", []))

            # ── Persist user message ─────────────────────────────────────
            attachments = []
            if image_base64:
                attachments.append({
                    "type": "image",
                    "base64": image_base64[:100] + "...",  # Truncate in stored JSON
                    "filename": "uploaded_image.jpg",
                })

            user_msg = _serialize_message(
                role="user",
                content=message_text,
                attachments=attachments,
            )
            session["messages"].append(user_msg)

            # ── Auto-title on first message ──────────────────────────────
            if len(session["messages"]) == 1:
                title = message_text[:50].strip()
                if len(message_text) > 50:
                    title += "..."
                session["title"] = title

            # ── Run the agentic loop ─────────────────────────────────────
            try:
                final_answer, updated_history = await run_agent_streaming(
                    user_message_content=user_content,
                    chat_history=chat_history,
                    system_prompt=system_prompt,
                    llm_with_tools=llm_with_tools,
                    tool_map=tool_map,
                    websocket=websocket,
                    enable_verbose=enable_verbose,
                    session_id=session_id,
                )
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Agent error: {str(e)}",
                })
                # Still persist what we have
                await asyncio.to_thread(_write_session, session_id, session)
                continue

            # ── Persist assistant message ────────────────────────────────
            # Extract thinking and diagrams from the final answer
            import re
            thinking = None
            thinking_match = re.search(
                r"<\|channel>thought\n(.*?)<channel\|>",
                final_answer,
                re.DOTALL,
            )
            if thinking_match:
                thinking = thinking_match.group(1).strip()

            # Extract mermaid diagrams
            from core.agent import MERMAID_PATTERN
            mermaid_matches = MERMAID_PATTERN.findall(final_answer)
            diagrams = [{"mermaid_code": m.strip()} for m in mermaid_matches]

            # Clean answer for storage (strip thinking blocks)
            clean_answer = re.sub(
                r"<\|channel>thought\n.*?<channel\|>",
                "",
                final_answer,
                flags=re.DOTALL,
            ).strip()

            assistant_msg = _serialize_message(
                role="assistant",
                content=clean_answer,
                thinking=thinking,
                diagrams=diagrams,
            )
            session["messages"].append(assistant_msg)

            # ── Persist session ──────────────────────────────────────────
            await asyncio.to_thread(_write_session, session_id, session)

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {str(e)}",
            })
        except Exception:
            pass
    finally:
        # Drop the Python reference without calling _system.stop()
        release_session_store(session_id)
