"""
Memory management for the PDF-QA system.

Provides:
  - save_memory(key, value, session_id) — persists a user preference/fact
  - load_memory() — reads all stored memories
  - delete_memory(key) — removes a memory
  - summarize_session(session_id, llm) — generates a session summary via Gemma

save_memory is a tool (callable by Gemma via closures).
load_memory is NOT a tool — called at session start, injected into system prompt.
summarize_session is NOT a tool — triggered only via POST /sessions/{id}/summarize.
"""

import os
import json
import asyncio
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage


# Path to the persistent memory file
MEMORY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "memory.json",
)

# Path to session data directories
CHATS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "chats",
)

SESSIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "sessions",
)

# Async lock for thread-safe file operations
_memory_lock = asyncio.Lock()


def _read_memory_file() -> dict:
    """Read the memory JSON file synchronously."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _write_memory_file(data: dict) -> None:
    """Write the memory JSON file synchronously."""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── save_memory ──────────────────────────────────────────────────────────────


def save_memory_impl(key: str, value: str, session_id: str = "") -> str:
    """
    Save a user preference or fact to persistent memory.

    Args:
        key: Short identifier for the memory (e.g. "preferred_style").
        value: The value to remember (e.g. "bullet points over paragraphs").
        session_id: The session that created this memory.

    Returns:
        JSON string confirming the save.
    """
    memories = _read_memory_file()

    memories[key] = {
        "value": value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
    }

    _write_memory_file(memories)

    return json.dumps({
        "status": "success",
        "key": key,
        "saved": True,
    })


# ── load_memory ──────────────────────────────────────────────────────────────


def load_memory() -> dict:
    """
    Read all stored memories.

    NOT a tool — called at session start, injected into system prompt as:
      "User preferences and context: {memories}"

    Returns:
        Dict of {key: {value, timestamp, session_id}}.
    """
    return _read_memory_file()


# ── delete_memory ────────────────────────────────────────────────────────────


def delete_memory(key: str) -> bool:
    """
    Remove a memory by key.

    Returns:
        True if deleted, False if key didn't exist.
    """
    memories = _read_memory_file()

    if key not in memories:
        return False

    del memories[key]
    _write_memory_file(memories)
    return True


# ── summarize_session ────────────────────────────────────────────────────────


def _load_session_messages(session_id: str) -> list[dict]:
    """Load the messages array from a session file."""
    session_file = os.path.join(CHATS_DIR, f"{session_id}.json")
    if not os.path.exists(session_file):
        return []

    with open(session_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("messages", [])


async def summarize_session(session_id: str, llm) -> str:
    """
    Generate a 3-5 sentence summary of a chat session using Gemma.

    NOT a tool — triggered only via POST /sessions/{id}/summarize.

    Args:
        session_id: The session to summarize.
        llm: The ChatOllama instance.

    Returns:
        JSON string with the summary.
    """
    messages = _load_session_messages(session_id)

    if not messages:
        return json.dumps({
            "status": "error",
            "message": "No messages found in session.",
        })

    # Build a condensed conversation text for the summarizer
    conversation_lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            # Truncate very long messages
            truncated = content[:500] + "..." if len(content) > 500 else content
            conversation_lines.append(f"{role.upper()}: {truncated}")

    conversation_text = "\n".join(conversation_lines)

    # Prompt Gemma for a summary
    summary_prompt = (
        "Summarize the following conversation in exactly 3-5 sentences. "
        "Focus on the main topics discussed and key information exchanged.\n\n"
        f"CONVERSATION:\n{conversation_text}"
    )

    try:
        response = await asyncio.to_thread(
            llm.invoke,
            [
                SystemMessage(content="You are a concise summarizer."),
                HumanMessage(content=summary_prompt),
            ],
        )
        summary = response.content.strip()
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to generate summary: {e}",
        })

    # Save summary to sessions directory
    summary_file = os.path.join(SESSIONS_DIR, f"{session_id}_summary.json")
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "session_id": session_id,
            "summary": summary,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2, ensure_ascii=False)

    # Also update the session file's summary field
    session_file = os.path.join(CHATS_DIR, f"{session_id}.json")
    if os.path.exists(session_file):
        with open(session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)
        session_data["summary"] = summary
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    return json.dumps({
        "status": "success",
        "session_id": session_id,
        "summary": summary,
    })
