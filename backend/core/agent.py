"""
Agentic loop for the PDF-QA system.

Provides:
  - build_system_prompt()
  - execute_tool_call()
  - run_agent_streaming() — single-pass astream() loop

The loop pattern:
  1. astream() the messages — accumulate full response
  2. If response has tool_calls → execute → append → loop back to 1
  3. If response is text only → it was already streamed live → done
  4. MAX_ITERATIONS=6 safety guard
"""

import re
import json
import asyncio
import traceback
from typing import Optional

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)


MAX_ITERATIONS = 6

MERMAID_PATTERN = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


def build_system_prompt(
    topics_data: dict | None,
    memory_data: dict,
    has_notes: bool,
    enable_thinking: bool = False,
) -> str:
    parts = []

    if enable_thinking:
        parts.append("<|think|>")

    parts.append(
        "You are an expert academic assistant capable of helping across multiple subjects.\n"
    )

    if has_notes and topics_data and topics_data.get("status") == "success":
        units = topics_data.get("units", [])
        topics = topics_data.get("topics", [])
        types = topics_data.get("types", [])
        n_chunks = topics_data.get("total_chunks", 0)

        units_str = ", ".join(units) if units else "N/A"
        topics_str = "\n  - ".join(topics) if topics else "N/A"
        types_str = ", ".join(types) if types else "N/A"

        parts.append(
            f"You have access to a structured knowledge base built from handwritten student notes (PDF).\n\n"
            f"## Knowledge Base Overview\n"
            f"- Total chunks indexed: {n_chunks}\n"
            f"- Units covered: {units_str}\n"
            f"- Knowledge types: {types_str}\n"
            f"- Topics available:\n  - {topics_str}\n"
        )

        parts.append(
            "\n## Tool Usage Rules — STRICTLY FOLLOW THIS ORDER\n"
            "1. ALWAYS call `retrieve_chunks` first for any academic question.\n"
            "2. Use the `filter_type` parameter when the question is clearly about "
            "a definition, process, advantages, disadvantages, or diagram.\n"
            "3. Use the `filter_unit` parameter when the user specifies a unit.\n"
            "4. Only call `web_search` if retrieve_chunks returns no useful results "
            "OR the user explicitly asks for external/recent information.\n"
            "5. Call `list_topics` only if the user asks what topics are covered.\n"
            "6. Call `generate_diagram` when the user asks for a diagram, flowchart, "
            "or visualization. After receiving the chunks, generate valid Mermaid.js "
            "syntax wrapped in ```mermaid``` code fences. Use simple node IDs (A, B, C) "
            "with labels in brackets. Example:\n"
            "```mermaid\n"
            "flowchart TD\n"
            "  A[Start] --> B[Process]\n"
            "  B --> C[End]\n"
            "```\n"
            "7. Call `save_memory` when the user states an important preference, fact, "
            "or anything they explicitly ask you to remember. Examples:\n"
            '   - "Remember that I prefer bullet points" → save_memory(key="preferred_style", value="bullet points")\n'
            '   - "My exam is on May 15" → save_memory(key="exam_date", value="May 15")\n'
            '   - "Remember my name is Alex" → save_memory(key="user_name", value="Alex")\n'
        )
    else:
        parts.append(
            "No PDF notes have been uploaded for this session.\n"
            "You can answer questions using web search.\n"
            "The user can upload PDF notes at any time via the sidebar.\n\n"
            "## Tool Usage Rules\n"
            "1. Use `web_search` to find information for the user's questions.\n"
            "2. Call `save_memory` when the user states an important preference, fact, "
            "or anything they explicitly ask you to remember. Examples:\n"
            '   - "Remember that I prefer bullet points" → save_memory(key="preferred_style", value="bullet points")\n'
            '   - "My exam is on May 15" → save_memory(key="exam_date", value="May 15")\n'
            "3. If the user uploads notes later, `retrieve_chunks` will become available.\n"
        )

    parts.append(
        "\n## Response Style\n"
        "- Be concise and academically accurate.\n"
        "- Structure your answers with clear headings when appropriate.\n"
        "- If you used retrieve_chunks, base your answer ONLY on what was retrieved.\n"
        "- If you used web_search, mention that the information came from the web.\n"
        "- Never make up information that wasn't in the retrieved content.\n"
    )

    if memory_data:
        memory_lines = []
        for key, val in memory_data.items():
            if isinstance(val, dict):
                memory_lines.append(f"- {key}: {val.get('value', val)}")
            else:
                memory_lines.append(f"- {key}: {val}")
        memory_str = "\n".join(memory_lines)
        parts.append(f"\n## User Context (Saved Memories)\n{memory_str}\n")

    return "\n".join(parts)


def execute_tool_call(tool_call: dict, tool_map: dict) -> ToolMessage:
    tool_name = tool_call.get("name", "unknown")
    tool_args = tool_call.get("args", {})
    tool_call_id = tool_call.get("id", tool_name)

    print(f"  [TOOL] Executing: {tool_name}({tool_args})")

    if tool_name not in tool_map:
        result = json.dumps({
            "status": "error",
            "error": f"Unknown tool '{tool_name}'. Available: {list(tool_map.keys())}",
        })
        print(f"  [TOOL] ERROR: Unknown tool '{tool_name}'")
    else:
        try:
            tool_fn = tool_map[tool_name]
            result = tool_fn.invoke(tool_args)
            print(f"  [TOOL] {tool_name} returned {len(result)} chars")
        except TypeError as e:
            result = json.dumps({
                "status": "error",
                "error": f"Invalid arguments for {tool_name}: {str(e)}",
            })
            print(f"  [TOOL] TypeError for {tool_name}: {e}")
            traceback.print_exc()
        except Exception as e:
            result = json.dumps({
                "status": "error",
                "error": f"Tool execution failed: {str(e)}",
            })
            print(f"  [TOOL] Exception for {tool_name}: {e}")
            traceback.print_exc()

    return ToolMessage(
        content=result,
        tool_call_id=tool_call_id,
    )


def _truncate_tool_result(content: str, max_chars: int = 1500) -> str:
    """Truncate tool results to avoid blowing up the context window."""
    if len(content) <= max_chars:
        return content
    try:
        data = json.loads(content)
        # For web search results, truncate highlights
        if isinstance(data, dict) and "results" in data:
            for r in data.get("results", []):
                if "highlights" in r and isinstance(r["highlights"], list):
                    r["highlights"] = [h[:300] for h in r["highlights"][:2]]
            truncated = json.dumps(data, ensure_ascii=False)
            if len(truncated) <= max_chars:
                return truncated
        # For chunk results, truncate content
        if isinstance(data, dict) and "chunks" in data:
            for c in data.get("chunks", []):
                if "content" in c and len(c["content"]) > 300:
                    c["content"] = c["content"][:300] + "..."
            truncated = json.dumps(data, ensure_ascii=False)
            if len(truncated) <= max_chars:
                return truncated
    except (json.JSONDecodeError, TypeError):
        pass
    return content[:max_chars] + "\n...[truncated]"


def _strip_thinking(text: str) -> str:
    """Remove all thinking blocks from text for storage."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<\|channel>thought\n.*?<channel\|>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


def _extract_thinking(text: str) -> str | None:
    """Extract thinking content from text."""
    match = re.search(r"<think>(.*?)</think>", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"<\|channel>thought\n(.*?)<channel\|>", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


async def run_agent_streaming(
    user_message_content,
    chat_history: list,
    system_prompt: str,
    llm_with_tools,
    tool_map: dict,
    websocket,
    enable_verbose: bool = False,
    session_id: str = "",
) -> tuple[str, list]:
    """
    Single-pass astream() agent loop.

    Every iteration uses astream() so tokens arrive at the frontend immediately.
    If the streamed response contains tool_calls, we execute them and loop.
    If it's pure text, the user already saw it live — we just finalize.
    """
    chat_history.append(HumanMessage(content=user_message_content))
    messages = [SystemMessage(content=system_prompt)] + chat_history

    final_answer = ""

    for iteration in range(MAX_ITERATIONS):
        print(f"\n--- Agent iteration {iteration + 1}/{MAX_ITERATIONS} ---")

        full_content = ""
        tool_call_chunks: dict[int, dict] = {}
        in_thinking = False
        thinking_buffer = ""
        streamed_any_content = False

        try:
            async for chunk in llm_with_tools.astream(messages):
                # ── Accumulate tool call fragments ───────────────────────
                if chunk.tool_call_chunks:
                    for tc_chunk in chunk.tool_call_chunks:
                        idx = tc_chunk.get("index", 0)
                        if idx not in tool_call_chunks:
                            tool_call_chunks[idx] = {"name": "", "args": "", "id": ""}
                        if tc_chunk.get("name"):
                            tool_call_chunks[idx]["name"] += tc_chunk["name"]
                        if tc_chunk.get("args"):
                            tool_call_chunks[idx]["args"] += tc_chunk["args"]
                        if tc_chunk.get("id"):
                            tool_call_chunks[idx]["id"] += tc_chunk["id"]

                # ── Stream text content live ─────────────────────────────
                token = chunk.content or ""
                if not token:
                    continue

                full_content += token

                # Route tokens through thinking parser
                remaining = token
                while remaining:
                    if in_thinking:
                        close_idx = remaining.lower().find("</think>")
                        if close_idx != -1:
                            thinking_buffer += remaining[:close_idx]
                            remaining = remaining[close_idx + len("</think>"):]
                            in_thinking = False
                            if thinking_buffer.strip():
                                try:
                                    await websocket.send_json({
                                        "type": "thinking",
                                        "content": thinking_buffer.strip(),
                                    })
                                except Exception:
                                    pass
                            thinking_buffer = ""
                        else:
                            thinking_buffer += remaining
                            remaining = ""
                    else:
                        open_idx = remaining.lower().find("<think>")
                        if open_idx != -1:
                            before = remaining[:open_idx]
                            if before:
                                streamed_any_content = True
                                try:
                                    await websocket.send_json({
                                        "type": "content",
                                        "content": before,
                                    })
                                except Exception:
                                    pass
                            remaining = remaining[open_idx + len("<think>"):]
                            in_thinking = True
                        else:
                            streamed_any_content = True
                            try:
                                await websocket.send_json({
                                    "type": "content",
                                    "content": remaining,
                                })
                            except Exception:
                                pass
                            remaining = ""

        except Exception as e:
            error_msg = f"LLM error: {str(e)}"
            print(f"  [ERROR] {error_msg}")
            traceback.print_exc()
            try:
                await websocket.send_json({"type": "error", "message": error_msg})
            except Exception:
                pass
            chat_history.append(
                AIMessage(content="I encountered an error while generating a response.")
            )
            return "I encountered an error while generating a response.", chat_history

        # Flush any remaining thinking buffer
        if in_thinking and thinking_buffer.strip():
            try:
                await websocket.send_json({
                    "type": "thinking",
                    "content": thinking_buffer.strip(),
                })
            except Exception:
                pass

        # ── Parse tool calls from accumulated chunks ─────────────────────
        tool_calls = []
        if tool_call_chunks:
            for idx in sorted(tool_call_chunks.keys()):
                tc = tool_call_chunks[idx]
                try:
                    args = json.loads(tc["args"]) if tc["args"] else {}
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({
                    "name": tc["name"],
                    "args": args,
                    "id": tc["id"] or tc["name"],
                })

        # ── Case 1: Tool calls ───────────────────────────────────────────
        if tool_calls:
            print(f"  [AGENT] Got {len(tool_calls)} tool call(s)")

            ai_msg = AIMessage(
                content=full_content,
                tool_calls=[
                    {"name": tc["name"], "args": tc["args"], "id": tc["id"]}
                    for tc in tool_calls
                ],
            )
            messages.append(ai_msg)
            chat_history.append(ai_msg)

            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tool_id = tc["id"]

                if enable_verbose:
                    try:
                        await websocket.send_json({
                            "type": "tool_call",
                            "tool": tool_name,
                            "args": tool_args,
                        })
                    except Exception:
                        pass

                tool_msg = await asyncio.to_thread(
                    execute_tool_call,
                    {"name": tool_name, "args": tool_args, "id": tool_id},
                    tool_map,
                )

                if enable_verbose:
                    try:
                        await websocket.send_json({
                            "type": "tool_result",
                            "tool": tool_name,
                            "result": tool_msg.content[:500],
                        })
                    except Exception:
                        pass

                # Truncate tool results before adding to context
                # to prevent context window overflow on next iteration
                truncated_content = _truncate_tool_result(tool_msg.content)
                truncated_msg = ToolMessage(
                    content=truncated_content,
                    tool_call_id=tool_msg.tool_call_id,
                )

                messages.append(truncated_msg)
                chat_history.append(truncated_msg)

            continue

        # ── Case 2: Final text answer (already streamed live) ────────────
        final_answer = full_content.strip()
        clean_answer = _strip_thinking(final_answer)

        print(f"  [AGENT] Streamed {len(final_answer)} chars (clean: {len(clean_answer)})")

        if clean_answer:
            # Check for mermaid diagrams
            mermaid_matches = MERMAID_PATTERN.findall(clean_answer)
            for mermaid_code in mermaid_matches:
                try:
                    await websocket.send_json({
                        "type": "diagram",
                        "mermaid_code": mermaid_code.strip(),
                    })
                except Exception:
                    pass

            chat_history.append(AIMessage(content=clean_answer))
            return final_answer, chat_history

        # ── Case 3: Empty response ───────────────────────────────────────
        print("  [AGENT] Empty response, nudging...")
        messages.append(
            HumanMessage(
                content="Please provide your answer based on the retrieved information."
            )
        )

    fallback = (
        "I was unable to generate a complete answer after multiple attempts. "
        "Please try rephrasing your question."
    )
    chat_history.append(AIMessage(content=fallback))
    try:
        await websocket.send_json({"type": "content", "content": fallback})
    except Exception:
        pass
    return fallback, chat_history
