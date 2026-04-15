# """
# Per-session ChromaDB vector store management.

# Each chat session gets its own isolated ChromaDB collection stored at:
#   backend/data/vector_stores/{session_id}/

# Vector stores are created only when a PDF is uploaded to a session.
# Sessions without notes have no vector store (retrieve_chunks returns "no_notes").
# """

# import os
# import shutil
# from pathlib import Path

# from langchain_chroma import Chroma
# from langchain_core.documents import Document
# from langchain_core.embeddings import Embeddings


# # Base directory for all session vector stores
# VECTOR_STORES_DIR = os.path.join(
#     os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
#     "data",
#     "vector_stores",
# )


# def _get_session_store_path(session_id: str) -> str:
#     """Get the filesystem path for a session's vector store."""
#     return os.path.join(VECTOR_STORES_DIR, session_id)


# def create_session_vectorstore(
#     session_id: str,
#     documents: list[Document],
#     embedding_fn: Embeddings,
# ) -> Chroma:
#     """
#     Create a new ChromaDB vector store for a session and index documents into it.

#     Args:
#         session_id: The chat session ID (used as collection name + directory name).
#         documents: List of LangChain Document objects to index.
#         embedding_fn: The EmbeddingGemmaLangChain instance for encoding.

#     Returns:
#         The Chroma vector store instance.
#     """
#     store_path = _get_session_store_path(session_id)
#     os.makedirs(store_path, exist_ok=True)

#     print(f"Creating vector store for session {session_id} at {store_path}")
#     print(f"Indexing {len(documents)} documents...")

#     vector_store = Chroma.from_documents(
#         documents=documents,
#         embedding=embedding_fn,
#         collection_name=session_id,
#         persist_directory=store_path,
#     )

#     count = vector_store._collection.count()
#     print(f"Vector store created — {count} vectors stored")
#     return vector_store


# def load_session_vectorstore(
#     session_id: str,
#     embedding_fn: Embeddings,
# ) -> Chroma | None:
#     """
#     Reconnect to an existing session's ChromaDB vector store.

#     Args:
#         session_id: The chat session ID.
#         embedding_fn: The EmbeddingGemmaLangChain instance (needed for queries).

#     Returns:
#         The Chroma instance, or None if the session has no vector store.
#     """
#     store_path = _get_session_store_path(session_id)

#     if not os.path.exists(store_path):
#         return None

#     # Check if the directory actually has ChromaDB data
#     if not os.path.exists(os.path.join(store_path, "chroma.sqlite3")):
#         return None

#     vector_store = Chroma(
#         collection_name=session_id,
#         embedding_function=embedding_fn,
#         persist_directory=store_path,
#     )
#     count = vector_store._collection.count()
#     print(f"Loaded vector store for session {session_id} — {count} vectors")
#     return vector_store


# def add_documents_to_session(
#     session_id: str,
#     documents: list[Document],
#     embedding_fn: Embeddings,
# ) -> Chroma:
#     """
#     Add new documents to an existing session's vector store.
#     If no store exists yet, creates one.

#     Returns:
#         The updated Chroma instance.
#     """
#     existing = load_session_vectorstore(session_id, embedding_fn)

#     if existing is None:
#         return create_session_vectorstore(session_id, documents, embedding_fn)

#     existing.add_documents(documents)
#     new_count = existing._collection.count()
#     print(f"Added {len(documents)} documents — total now: {new_count}")
#     return existing


# def delete_session_vectorstore(session_id: str) -> bool:
#     """
#     Recursively delete a session's vector store directory.

#     Returns:
#         True if deleted, False if directory didn't exist.
#     """
#     store_path = _get_session_store_path(session_id)

#     if os.path.exists(store_path):
#         shutil.rmtree(store_path)
#         print(f"Deleted vector store for session {session_id}")
#         return True

#     return False

"""
Per-session ChromaDB vector store management.

Each chat session gets its own isolated ChromaDB collection stored at:
  backend/data/vector_stores/{session_id}/

Windows note: ChromaDB holds SQLite file handles open. We cache open
instances and reuse them instead of closing/reopening, which corrupts
the internal state. For deletion, we drop references and use retry logic.
"""

import gc
import os
import shutil
import time

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


# Base directory for all session vector stores
VECTOR_STORES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "vector_stores",
)

# Cache of open Chroma instances — session_id → Chroma object
# We REUSE these instead of closing and reopening.
# Closing a ChromaDB client corrupts its internal state on the same path.
_open_stores: dict[str, Chroma] = {}


def _get_session_store_path(session_id: str) -> str:
    """Get the filesystem path for a session's vector store."""
    return os.path.join(VECTOR_STORES_DIR, session_id)


def create_session_vectorstore(
    session_id: str,
    documents: list[Document],
    embedding_fn: Embeddings,
) -> Chroma:
    """
    Create a new ChromaDB vector store for a session and index documents.
    If a store already exists in cache, evict it first.
    """
    store_path = _get_session_store_path(session_id)

    # Evict any cached instance for this session (not closing, just dropping ref)
    if session_id in _open_stores:
        del _open_stores[session_id]
        gc.collect()

    os.makedirs(store_path, exist_ok=True)

    print(f"Creating vector store for session {session_id} at {store_path}")
    print(f"Indexing {len(documents)} documents...")

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embedding_fn,
        collection_name=session_id,
        persist_directory=store_path,
    )

    # Cache the instance for reuse
    _open_stores[session_id] = vector_store

    count = vector_store._collection.count()
    print(f"Vector store created — {count} vectors stored")
    return vector_store


def load_session_vectorstore(
    session_id: str,
    embedding_fn: Embeddings,
) -> Chroma | None:
    """
    Reconnect to an existing session's ChromaDB vector store.
    Returns cached instance if already open — avoids reopening same path.

    Returns:
        The Chroma instance, or None if the session has no vector store.
    """
    store_path = _get_session_store_path(session_id)

    if not os.path.exists(store_path):
        return None

    if not os.path.exists(os.path.join(store_path, "chroma.sqlite3")):
        return None

    # Return cached instance if available — critical on Windows
    # Reopening the same path after _system.stop() corrupts ChromaDB state
    if session_id in _open_stores:
        count = _open_stores[session_id]._collection.count()
        print(f"Reusing cached vector store for session {session_id} — {count} vectors")
        return _open_stores[session_id]

    # No cached instance — open fresh
    vector_store = Chroma(
        collection_name=session_id,
        embedding_function=embedding_fn,
        persist_directory=store_path,
    )

    # Cache for reuse
    _open_stores[session_id] = vector_store

    count = vector_store._collection.count()
    print(f"Loaded vector store for session {session_id} — {count} vectors")
    return vector_store


def add_documents_to_session(
    session_id: str,
    documents: list[Document],
    embedding_fn: Embeddings,
) -> Chroma:
    """
    Add new documents to an existing session's vector store.
    If no store exists yet, creates one.
    """
    existing = load_session_vectorstore(session_id, embedding_fn)

    if existing is None:
        return create_session_vectorstore(session_id, documents, embedding_fn)

    existing.add_documents(documents)
    new_count = existing._collection.count()
    print(f"Added {len(documents)} documents — total now: {new_count}")
    return existing


def release_session_store(session_id: str) -> None:
    """
    Drop the cached Chroma instance for a session without deleting files.
    Call this when a WebSocket disconnects to free memory.
    Does NOT close the ChromaDB client — just removes the Python reference.
    """
    if session_id in _open_stores:
        del _open_stores[session_id]
        gc.collect()
        print(f"Released cached store for session {session_id}")


def delete_session_vectorstore(session_id: str) -> bool:
    store_path = _get_session_store_path(session_id)

    if not os.path.exists(store_path):
        return False

    # 🚨 STEP 1: Force stop Chroma internal system
    if session_id in _open_stores:
        try:
            vs = _open_stores[session_id]

            # 🔥 THIS IS THE CRITICAL LINE
            vs._client._system.stop()

            print(f"Stopped Chroma system for {session_id}")
        except Exception as e:
            print(f"Warning: failed to stop Chroma system: {e}")

        del _open_stores[session_id]

    # 🚨 STEP 2: Extra cleanup
    import gc, time
    for _ in range(3):
        gc.collect()
        time.sleep(0.3)

    # 🚨 STEP 3: Delete with retry
    last_error = None
    for attempt in range(5):
        try:
            shutil.rmtree(store_path)
            print(f"Deleted vector store for session {session_id}")
            return True
        except PermissionError as e:
            last_error = e
            print(f"Delete attempt {attempt+1}/5 failed — retrying...")
            time.sleep(1)

    raise RuntimeError(
        f"Could not delete vector store for session '{session_id}' "
        f"Path: {store_path} | Error: {last_error}"
    )


def close_all_stores() -> None:
    """
    Drop all cached Chroma instances.
    Call this in FastAPI lifespan shutdown.
    Does NOT call _system.stop() — just clears Python references.
    """
    count = len(_open_stores)
    _open_stores.clear()
    gc.collect()
    print(f"Released {count} cached vector store(s)")