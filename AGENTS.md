# PROJECT KNOWLEDGE BASE

**Generated:** Thu May 07 2026
**Commit:** 62b2377
**Branch:** main

## OVERVIEW
Full-stack PDF-QA system. FastAPI backend serves a React SPA that performs RAG over uploaded PDFs using local Ollama (Gemma) + ChromaDB, with Exa API fallback for web search.

## STRUCTURE
```
PDF-QA system/
├── backend/       # FastAPI app + core AI modules
│   ├── routers/   # API route handlers
│   ├── core/      # RAG, agent, embedding logic
│   ├── data/      # ChromaDB + SQLite storage
│   └── uploads/   # Uploaded PDF files
├── frontend/      # Vite + React SPA
│   ├── src/       # pages, components, hooks, store, types, lib
│   └── dist/      # Build output
├── jupyter/       # Prototyping notebooks + isolated venv
└── docs/          # Reference: Exa, Gemma, LangChain integration
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `backend/routers/` | Mount in `backend/main.py` |
| Modify RAG/agent logic | `backend/core/agent.py` | Contains strict ordering rules |
| Add UI page | `frontend/src/pages/` | Register route in App.tsx |
| Add shared component | `frontend/src/components/` | Follow existing directory structure |
| Add global state | `frontend/src/store/` | Uses Zustand |
| Environment / secrets | `backend/.env` or `frontend/.env` | Never commit `.env` files |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `app` | FastAPI | `backend/main.py` | Entry point, lifespan, router mounts |
| `retrieve_chunks` | function | `backend/core/agent.py` | MUST be called first per strict rule |
| `main.tsx` | TSX | `frontend/src/main.tsx` | React bootstrap |
| `App.tsx` | TSX | `frontend/src/App.tsx` | Root component with routing |

## CONVENTIONS
- **Python backend**: No `pyproject.toml`; deps managed via `requirements.txt` only
- **Frontend**: TypeScript strict mode, React JSX transform, Vite dev server on port 5173
- **Styling**: Tailwind CSS v3 with custom `surface` / `accent` color scales, `darkMode: 'class'`
- **State**: Zustand for global state in `frontend/src/store/`
- **No ESLint config file** — `eslint` is in `package.json` devDependencies but no explicit config exists

## ANTI-PATTERNS (THIS PROJECT)
- **Do NOT call tools out of order**: `backend/core/agent.py` enforces `retrieve_chunks` MUST be called first for academic questions
- **Do NOT use deprecated Exa params**: `useAutoprompt`, `numSentences`, `highlightsPerUrl`, `livecrawl: "always"` (see `docs/exa/exa.md`)
- **Do NOT commit `.env` files** or `backend/data/`, `backend/uploads/`
- **Do NOT add CI/CD to this repo** — none exists; add from scratch if needed

## UNIQUE STYLES
- Backend runs via `python main.py` (uvicorn called inside `if __name__ == "__main__"` block), not standard `uvicorn main:app` CLI
- `jupyter/` has its own `venv/` — isolated from backend dependencies

## COMMANDS
```bash
# Backend
cd backend && python main.py          # http://localhost:8000

# Frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
cd frontend && npm run build          # Production build
cd frontend && npm run lint           # ESLint (no explicit config file)
```

## NOTES
- No CI/CD, no Docker, no tests, no Python packaging standard
- Reproducible npm builds via `package-lock.json`; Python side has no lock file
