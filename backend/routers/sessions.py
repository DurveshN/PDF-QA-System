"""
Session CRUD router.

Endpoints:
  GET    /sessions                        — list all sessions
  POST   /sessions                        — create new session
  GET    /sessions/{session_id}           — get session with full history
  DELETE /sessions/{session_id}           — delete session + vector store
  PUT    /sessions/{session_id}/title     — rename session
  POST   /sessions/{session_id}/summarize — trigger LLM summary
"""

import os
import json
import uuid
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from core.vectorstore import delete_session_vectorstore
from core.memory import summarize_session


router = APIRouter(prefix="/sessions", tags=["sessions"])


# ── Paths ────────────────────────────────────────────────────────────────────

CHATS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "chats",
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _new_session_dict(session_id: str) -> dict:
    """Create a fresh session JSON object."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "session_id": session_id,
        "title": "New Chat",
        "created_at": now,
        "updated_at": now,
        "model": os.getenv("OLLAMA_MODEL", "gemma4:e2b"),
        "has_notes": False,
        "vector_store_path": None,
        "messages": [],
        "summary": None,
        "memory_keys": [],
        "note_metadata": None,
    }


def _read_session(session_id: str) -> dict | None:
    """Read a session JSON file. Returns None if not found."""
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


def _list_session_files() -> list[dict]:
    """List all sessions sorted by updated_at desc."""
    os.makedirs(CHATS_DIR, exist_ok=True)
    sessions = []
    for filename in os.listdir(CHATS_DIR):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(CHATS_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({
                "session_id": data.get("session_id", ""),
                "title": data.get("title", "New Chat"),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "has_notes": data.get("has_notes", False),
                "message_count": len(data.get("messages", [])),
                "summary": data.get("summary"),
            })
        except (json.JSONDecodeError, IOError):
            continue

    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions


# ── Request models ───────────────────────────────────────────────────────────


class TitleUpdate(BaseModel):
    title: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("")
async def list_sessions():
    """List all chat sessions sorted by most recently updated."""
    sessions = await asyncio.to_thread(_list_session_files)
    return {"sessions": sessions}


@router.post("")
async def create_session():
    """Create a new chat session and return its metadata."""
    session_id = str(uuid.uuid4())
    session_data = _new_session_dict(session_id)
    await asyncio.to_thread(_write_session, session_id, session_data)
    return {
        "session_id": session_id,
        "title": session_data["title"],
        "created_at": session_data["created_at"],
    }


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get a session's full data including chat history."""
    session = await asyncio.to_thread(_read_session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session file AND its vector store directory recursively."""
    # Delete session JSON file
    session_file = os.path.join(CHATS_DIR, f"{session_id}.json")
    if os.path.exists(session_file):
        os.remove(session_file)

    # Delete vector store (handles Windows file locks internally)
    await asyncio.to_thread(delete_session_vectorstore, session_id)

    return {"status": "deleted", "session_id": session_id}


@router.put("/{session_id}/title")
async def update_title(session_id: str, body: TitleUpdate):
    """Rename a session."""
    session = await asyncio.to_thread(_read_session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session["title"] = body.title
    await asyncio.to_thread(_write_session, session_id, session)
    return {"session_id": session_id, "title": body.title}


@router.post("/{session_id}/summarize")
async def summarize(session_id: str, request: Request):
    """
    Generate a 3-5 sentence summary of the session using Gemma.
    NOT a Gemma tool — only triggered via this REST endpoint.
    """
    session = await asyncio.to_thread(_read_session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    llm = request.app.state.llm
    result_json = await summarize_session(session_id, llm)
    result = json.loads(result_json)

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))

    return result
