"""
FastAPI application entry point for the PDF-QA system.

Lifespan:
  - Startup: Load EmbeddingGemma, init ChatOllama, init Exa client, check Ollama
  - Shutdown: Release all cached vector stores

Mounts routers: chat, sessions, upload, notes, memory
CORS: http://localhost:5173
Health check: GET /health
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from core.embeddings import EmbeddingGemmaLangChain, load_embedding_model
from core.llm import get_llm, check_ollama_status
from core.vectorstore import close_all_stores

from routers import chat, sessions, upload, notes, memory


# ── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle.

    Startup:
      1. Load EmbeddingGemma-300M model (~30s first time)
      2. Wrap in EmbeddingGemmaLangChain
      3. Check Ollama is running and model is available
      4. Init ChatOllama
      5. Init Exa client
    Shutdown:
      1. Release all cached vector store references
    """
    print("=" * 60)
    print("PDF-QA System — Starting up...")
    print("=" * 60)

    # ── 1. Load EmbeddingGemma ───────────────────────────────────────────
    try:
        raw_model = await asyncio.to_thread(load_embedding_model)
        app.state.embedding_fn = EmbeddingGemmaLangChain(model=raw_model)
        print("[OK] EmbeddingGemma loaded")
    except Exception as e:
        print(f"[FAIL] Failed to load EmbeddingGemma: {e}")
        sys.exit(1)

    # ── 2. Check Ollama ──────────────────────────────────────────────────
    try:
        ollama_info = await check_ollama_status()
        print(f"[OK] Ollama OK -- model: {ollama_info['model']}")
    except (ConnectionError, ValueError) as e:
        print(f"[WARN] Ollama check failed: {e}")
        print("[WARN] Server will start but chat will not work until Ollama is running.")

    # ── 3. Init ChatOllama ───────────────────────────────────────────────
    app.state.llm = get_llm()
    print("[OK] ChatOllama initialized")

    # ── 4. Init Exa client ───────────────────────────────────────────────
    exa_api_key = os.getenv("EXA_API_KEY")
    if exa_api_key:
        from exa_py import Exa
        app.state.exa_client = Exa(api_key=exa_api_key)
        print("[OK] Exa client initialized")
    else:
        app.state.exa_client = None
        print("[WARN] EXA_API_KEY not set -- web search disabled")

    print("=" * 60)
    print("Server ready!")
    print("=" * 60)

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    print("Shutting down — releasing vector stores...")
    close_all_stores()
    print("Shutdown complete.")


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PDF-QA System",
    description="AI-powered PDF Question-Answering with Gemma 4",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routers ────────────────────────────────────────────────────────────

app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(upload.router)
app.include_router(notes.router)
app.include_router(memory.router)


# ── Health check ─────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    """Health check endpoint."""
    # Count sessions
    chats_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "chats",
    )
    sessions_count = 0
    if os.path.exists(chats_dir):
        sessions_count = len([
            f for f in os.listdir(chats_dir) if f.endswith(".json")
        ])

    return {
        "status": "ok",
        "ollama": True,
        "model": os.getenv("OLLAMA_MODEL", "gemma4:e2b"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "google/embeddinggemma-300M"),
        "sessions_count": sessions_count,
    }


# ── Main ─────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
