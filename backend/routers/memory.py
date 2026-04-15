"""
Memory REST router.

Endpoints:
  GET    /memory          — list all saved memories
  POST   /memory          — save a memory {key, value}
  DELETE /memory/{key}    — delete a memory by key
"""

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.memory import load_memory, save_memory_impl, delete_memory


router = APIRouter(prefix="/memory", tags=["memory"])


class MemorySaveRequest(BaseModel):
    key: str
    value: str


@router.get("")
async def list_memories():
    """Return all saved memories."""
    memories = await asyncio.to_thread(load_memory)
    return {"memories": memories}


@router.post("")
async def save(body: MemorySaveRequest):
    """Save a memory key-value pair."""
    import json
    result_json = await asyncio.to_thread(
        save_memory_impl,
        key=body.key,
        value=body.value,
        session_id="manual",
    )
    return json.loads(result_json)


@router.delete("/{key}")
async def remove_memory(key: str):
    """Delete a memory by key."""
    deleted = await asyncio.to_thread(delete_memory, key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory key '{key}' not found.")
    return {"status": "deleted", "key": key}
