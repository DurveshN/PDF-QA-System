# BACKEND KNOWLEDGE BASE

## OVERVIEW
FastAPI backend for PDF ingestion, RAG retrieval, and LLM orchestration via Ollama.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `routers/` | Import router and mount in `main.py` |
| Modify RAG logic | `core/agent.py` | Strict rule: `retrieve_chunks` MUST be called first |
| Change embeddings | `core/` | Embedding model and chunking logic |
| Database / vector store | `data/` | ChromaDB + SQLite files |
| Uploaded PDFs | `uploads/` | Ephemeral storage, never commit |
| Environment config | `.env` | Secrets and model names, never commit |
| Start server | `main.py` | Uvicorn runs inside `if __name__ == "__main__"` |

## CONVENTIONS
- **Dependencies**: `requirements.txt` only. No `pyproject.toml`, `setup.py`, or `setup.cfg`.
- **No tests**: There is no test infrastructure. Add from scratch if needed.
- **Entry point**: Run with `python main.py`, not `uvicorn main:app`.
- **Secrets**: Use `.env` file; never commit it.
- **No packaging**: This is not a distributable Python package.

## ANTI-PATTERNS
- **Do NOT call tools out of order**: `core/agent.py` enforces `retrieve_chunks` MUST be called first for academic questions. Violating this breaks the agent flow.
- **Do NOT commit `.env`**, `data/`, or `uploads/` directories.
- **Do NOT use deprecated Exa params**: `useAutoprompt`, `numSentences`, `highlightsPerUrl`, `livecrawl: "always"`.
- **Do NOT add `pyproject.toml`**: The project intentionally uses `requirements.txt` only.

## NOTES
- No CI/CD, no Docker, no Python lock file. Keep it simple.
- `jupyter/` has its own isolated `venv/` — do not mix dependencies.
