"""
Agentic loop for the PDF-QA system.

Provides:
  - build_system_prompt() — constructs the system prompt with topics, memory, thinking
  - execute_tool_call() — runs a single tool call and returns a ToolMessage
  - run_agent_streaming() — the async agentic loop that streams via WebSocket

The loop pattern:
  1. Send message history to Gemma via astream()
  2. If Gemma returns tool_calls → execute each → append results → repeat
  3. If Gemma returns text content → that's the final answer → stop
  4. MAX_ITERATIONS=6 safety guard

Mermaid detection: after final content is assembled, regex-match
```mermaid ... ``` blocks and send as {"type": "diagram"} events.
"""

import re
import json
import asyncio
from typing import Optional

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)


MAX_ITERATIONS = 6

# Regex to detect mermaid code blocks in the final answer
MERMAID_PATTERN = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def build_system_prompt(
    topics_data: dict | None,
    memory_data: dict,
    has_notes: bool,
    enable_thinking: bool = False,
) -> str:
    """
    Build the system prompt for a chat session.

    Args:
        topics_data: Output from list_topics() if notes exist, else None.
        memory_data: Dict of user memories from load_memory().
        has_notes: Whether this session has PDF notes indexed.
        enable_thinking: If True, prepend <|think|> token for Gemma thinking mode.

    Returns:
        The complete system prompt string.
    """
    parts = []

    # Thinking mode trigger
    if enable_thinking:
        parts.append("<|think|>")

    # Base identity
    parts.append(
        "You are an expert academic assistant capable of helping across multiple subjects.\n"
    )

    # Knowledge base section
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
            "syntax wrapped in ```mermaid``` code fences.\n"
            "7. Call `save_memory` when the user states an important preference or fact to remember.\n"
        )
    else:
        parts.append(
            "No PDF notes have been uploaded for this session.\n"
            "You can answer questions using web search.\n"
            "The user can upload PDF notes at any time via the sidebar.\n\n"
            "## Tool Usage Rules\n"
            "1. Use `web_search` to find information for the user's questions.\n"
            "2. Call `save_memory` when the user states an important preference or fact to remember.\n"
            "3. If the user uploads notes later, `retrieve_chunks` will become available.\n"
        )

    # Response style
    parts.append(
        "\n## Response Style\n"
        "- Be concise and academically accurate.\n"
        "- Structure your answers with clear headings when appropriate.\n"
        "- If you used retrieve_chunks, base your answer ONLY on what was retrieved.\n"
        "- If you used web_search, mention that the information came from the web.\n"
        "- Never make up information that wasn't in the retrieved content.\n"
    )

    # Inject user memories
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
    """
    Execute a single tool call from Gemma's response.

    Args:
        tool_call: Dict with "name", "args", and optional "id".
        tool_map: Dict mapping tool names to callable functions.

    Returns:
        A LangChain ToolMessage with the execution result.
    """
    tool_name = tool_call.get("name", "unknown")
    tool_args = tool_call.get("args", {})
    tool_call_id = tool_call.get("id", tool_name)

    if tool_name not in tool_map:
        result = json.dumps({
            "status": "error",
            "error": f"Unknown tool '{tool_name}'. Available: {list(tool_map.keys())}",
        })
    else:
        try:
            result = tool_map[tool_name](**tool_args)
        except TypeError as e:
            result = json.dumps({
                "status": "error",
                "error": f"Invalid arguments for {tool_name}: {str(e)}",
            })
        except Exception as e:
            result = json.dumps({
                "status": "error",
                "error": f"Tool execution failed: {str(e)}",
            })

    return ToolMessage(
        content=result,
        tool_call_id=tool_call_id,
    )


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
    Run the agentic loop with streaming for one user message.

    Streams events to the WebSocket as JSON:
      {"type": "thinking", "content": "..."}
      {"type": "tool_call", "tool": "...", "args": {...}}
      {"type": "tool_result", "tool": "...", "result": "..."}
      {"type": "content", "content": "..."}
      {"type": "diagram", "mermaid_code": "..."}
      {"type": "done", "session_id": "..."}
      {"type": "error", "message": "..."}

    Args:
        user_message_content: String or list (for multimodal) — the user's input.
        chat_history: Existing LangChain message history for the session.
        system_prompt: The full system prompt.
        llm_with_tools: ChatOllama with tools bound.
        tool_map: Dict of tool_name → callable.
        websocket: The WebSocket connection to stream to.
        enable_verbose: Whether to send tool_call/tool_result events.
        session_id: Current session ID.

    Returns:
        (final_answer: str, updated_chat_history: list)
    """
    # Append user message to history
    chat_history.append(HumanMessage(content=user_message_content))

    # Build full message list: system + history
    messages = [SystemMessage(content=system_prompt)] + chat_history

    final_answer = ""
    thinking_content = ""

    for iteration in range(MAX_ITERATIONS):
        # Accumulate the full response via streaming
        full_content = ""
        tool_calls = []
        tool_call_chunks = {}

        try:
            async for chunk in llm_with_tools.astream(messages):
                # Accumulate tool calls
                if chunk.tool_call_chunks:
                    for tc_chunk in chunk.tool_call_chunks:
                        idx = tc_chunk.get("index", 0)
                        if idx not in tool_call_chunks:
                            tool_call_chunks[idx] = {
                                "name": "",
                                "args": "",
                                "id": "",
                            }
                        if tc_chunk.get("name"):
                            tool_call_chunks[idx]["name"] += tc_chunk["name"]
                        if tc_chunk.get("args"):
                            tool_call_chunks[idx]["args"] += tc_chunk["args"]
                        if tc_chunk.get("id"):
                            tool_call_chunks[idx]["id"] += tc_chunk["id"]

                # Accumulate content
                if chunk.content:
                    full_content += chunk.content

                    # Check for thinking content delimiters
                    # Ollama/Gemma may output thinking inside <|channel>thought\n...<channel|>
                    # For now, stream content as-is; we'll parse thinking after
                    await websocket.send_json({
                        "type": "content",
                        "content": chunk.content,
                    })

            # Parse tool calls from accumulated chunks
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

        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": f"LLM streaming error: {str(e)}",
            })
            chat_history.append(
                AIMessage(content="I encountered an error while generating a response.")
            )
            return "I encountered an error while generating a response.", chat_history

        # ── Case 1: Tool calls ───────────────────────────────────────────────
        if tool_calls:
            # Build an AIMessage with the tool calls for history
            ai_msg = AIMessage(
                content=full_content,
                tool_calls=[
                    {
                        "name": tc["name"],
                        "args": tc["args"],
                        "id": tc["id"],
                    }
                    for tc in tool_calls
                ],
            )
            messages.append(ai_msg)
            chat_history.append(ai_msg)

            # Execute each tool call
            for tc in tool_calls:
                if enable_verbose:
                    await websocket.send_json({
                        "type": "tool_call",
                        "tool": tc["name"],
                        "args": tc["args"],
                    })

                # Run sync tool in thread pool
                tool_msg = await asyncio.to_thread(
                    execute_tool_call, tc, tool_map
                )

                if enable_verbose:
                    # Send truncated result preview
                    result_preview = tool_msg.content[:500]
                    await websocket.send_json({
                        "type": "tool_result",
                        "tool": tc["name"],
                        "result": result_preview,
                    })

                messages.append(tool_msg)
                chat_history.append(tool_msg)

            # Continue loop — Gemma will read the tool results
            continue

        # ── Case 2: Final answer ─────────────────────────────────────────────
        final_answer = full_content.strip()

        if final_answer:
            # Check for mermaid diagrams in the response
            mermaid_matches = MERMAID_PATTERN.findall(final_answer)
            for mermaid_code in mermaid_matches:
                await websocket.send_json({
                    "type": "diagram",
                    "mermaid_code": mermaid_code.strip(),
                })

            # Strip thinking content before storing in history
            # (Ollama may include thinking blocks — clean them from stored history)
            clean_answer = final_answer
            # Remove <|channel>thought\n...<channel|> blocks if present
            clean_answer = re.sub(
                r"<\|channel>thought\n.*?<channel\|>",
                "",
                clean_answer,
                flags=re.DOTALL,
            ).strip()

            chat_history.append(AIMessage(content=clean_answer))

            await websocket.send_json({
                "type": "done",
                "session_id": session_id,
            })

            return final_answer, chat_history

        # ── Case 3: Empty response ───────────────────────────────────────────
        messages.append(
            HumanMessage(
                content="Please provide your answer based on the retrieved information."
            )
        )

    # Max iterations exhausted
    fallback = (
        "I was unable to generate a complete answer after multiple attempts. "
        "Please try rephrasing your question."
    )
    chat_history.append(AIMessage(content=fallback))
    await websocket.send_json({"type": "content", "content": fallback})
    await websocket.send_json({"type": "done", "session_id": session_id})
    return fallback, chat_history
