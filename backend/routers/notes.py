"""
Notes upload router — polling-based progress tracking.

Endpoints:
  POST /notes/upload                       — start PDF processing, returns {task_id}
  GET  /notes/upload/status/{task_id}      — poll progress (frontend polls every 1s)
  GET  /notes/topics                       — list topics for a session's vector store
  DELETE /notes/{session_id}               — remove notes and reset session

Progress is tracked in a module-level dict. No SSE, no event streams.
"""

import os
import json
import uuid
import asyncio

from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException

from core.pdf_pipeline import process_pdf
from core.vectorstore import load_session_vectorstore, delete_session_vectorstore
from core.tools import list_topics_impl


router = APIRouter(prefix="/notes", tags=["notes"])


# ── Paths ────────────────────────────────────────────────────────────────────

PDFS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "uploads",
    "pdfs",
)

CHATS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "chats",
)


# ── In-memory upload task tracker ────────────────────────────────────────────
# Format: {task_id: {stage, progress, message, status, result}}

_upload_tasks: dict[str, dict] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _read_session(session_id: str) -> dict | None:
    path = os.path.join(CHATS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_session(session_id: str, data: dict) -> None:
    from datetime import datetime, timezone
    path = os.path.join(CHATS_DIR, f"{session_id}.json")
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/upload")
async def upload_notes(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """
    Start PDF processing. Returns {task_id} immediately.
    Frontend polls GET /notes/upload/status/{task_id} every 1 second.
    """
    # Validate file
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Validate session exists
    session = await asyncio.to_thread(_read_session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Read file bytes
    pdf_bytes = await file.read()
    filename = file.filename

    # Save PDF to disk
    os.makedirs(PDFS_DIR, exist_ok=True)
    pdf_id = str(uuid.uuid4())
    pdf_path = os.path.join(PDFS_DIR, f"{pdf_id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Create task entry
    task_id = str(uuid.uuid4())
    _upload_tasks[task_id] = {
        "stage": "queued",
        "progress": 0,
        "message": "Queued for processing...",
        "status": "running",
        "result": None,
    }

    # Launch background processing
    embedding_fn = request.app.state.embedding_fn
    asyncio.create_task(
        _process_in_background(
            task_id=task_id,
            pdf_bytes=pdf_bytes,
            filename=filename,
            session_id=session_id,
            embedding_fn=embedding_fn,
        )
    )

    return {"task_id": task_id}


@router.get("/upload/status/{task_id}")
async def get_upload_status(task_id: str):
    """
    Poll the progress of a PDF upload/processing task.
    Frontend calls this every 1 second.

    Returns:
        {stage, progress, message, status, result}
        status is "running", "done", or "error"
    """
    if task_id not in _upload_tasks:
        raise HTTPException(status_code=404, detail="Task not found.")

    task = _upload_tasks[task_id]

    # Clean up completed tasks after they've been polled
    # (keep for 60 seconds after completion to avoid race conditions)
    return task


@router.get("/topics")
async def get_topics(session_id: str, request: Request):
    """List all topics for a session's vector store."""
    session = await asyncio.to_thread(_read_session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    if not session.get("has_notes", False):
        return {"status": "no_notes", "message": "No notes uploaded."}

    vs = await asyncio.to_thread(
        load_session_vectorstore,
        session_id,
        request.app.state.embedding_fn,
    )

    if vs is None:
        return {"status": "no_notes", "message": "Vector store not found."}

    result_json = await asyncio.to_thread(list_topics_impl, vs)
    return json.loads(result_json)


@router.delete("/{session_id}")
async def delete_notes(session_id: str):
    """Remove notes from a session and reset has_notes flag."""
    session = await asyncio.to_thread(_read_session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Delete vector store
    await asyncio.to_thread(delete_session_vectorstore, session_id)

    # Reset session fields
    session["has_notes"] = False
    session["vector_store_path"] = None
    session["note_metadata"] = None
    await asyncio.to_thread(_write_session, session_id, session)

    return {"status": "deleted", "session_id": session_id}


# ── Background processing ───────────────────────────────────────────────────


async def _process_in_background(
    task_id: str,
    pdf_bytes: bytes,
    filename: str,
    session_id: str,
    embedding_fn,
):
    """
    Run the full PDF pipeline in the background, updating progress in
    the _upload_tasks dict for polling.
    """

    async def progress_callback(stage: str, progress: int, message: str):
        _upload_tasks[task_id] = {
            "stage": stage,
            "progress": progress,
            "message": message,
            "status": "running" if stage != "done" else "done",
            "result": _upload_tasks[task_id].get("result"),
        }

    try:
        result = await process_pdf(
            pdf_bytes=pdf_bytes,
            filename=filename,
            session_id=session_id,
            embedding_fn=embedding_fn,
            progress_callback=progress_callback,
        )

        # Update session JSON
        session = _read_session(session_id)
        if session:
            vs_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data",
                "vector_stores",
                session_id,
            )
            session["has_notes"] = True
            session["vector_store_path"] = vs_path
            session["note_metadata"] = {
                "filename": filename,
                "topic_count": result.get("topic_count", 0),
                "chunk_count": result.get("chunk_count", 0),
                "created_at": result.get("created_at", ""),
            }
            _write_session(session_id, session)

        _upload_tasks[task_id] = {
            "stage": "done",
            "progress": 100,
            "message": "Done!",
            "status": "done",
            "result": {
                "chunk_count": result.get("chunk_count", 0),
                "topic_count": result.get("topic_count", 0),
                "filename": filename,
            },
        }

    except Exception as e:
        _upload_tasks[task_id] = {
            "stage": "error",
            "progress": 0,
            "message": f"Error: {str(e)}",
            "status": "error",
            "result": None,
        }
