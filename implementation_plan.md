# PDF-QA System — Full Stack Implementation Plan (v2)

## Overview

Build a complete full-stack AI-powered PDF Question-Answering system by porting the working Jupyter notebook into a **FastAPI backend** + **Vite/React/TypeScript frontend** with a Claude-like chat interface.

**Existing assets** (untouched — reference only):
- `jupyter/chroma_langchain_db/` — 49 vectors (reference only, NOT used by backend)
- `jupyter/data/notes.json` — 49 knowledge objects (reference for format)
- `jupyter/.env` — API keys (HF_TOKEN, GEMINI_API_KEY, EXA_API_KEY)
- `jupyter/PDF-QA_system.ipynb` — reference implementation

---

## Key Architecture Decision: Per-Session Vector Stores

> [!IMPORTANT]
> Each chat session gets its own **isolated ChromaDB collection**. There is no global vector store. The `jupyter/chroma_langchain_db` is NOT used by the backend — it remains as reference only.

| Concept | Design |
|---|---|
| **Storage path** | `backend/data/vector_stores/{session_id}/` |
| **Created when** | A PDF is uploaded to that specific session via `POST /notes/upload` |
| **Session JSON fields** | `has_notes: bool` (default `false`), `vector_store_path: str \| null` |
| **No notes uploaded** | `retrieve_chunks` returns `{status: "no_notes"}`, Gemma falls back to `web_search` |
| **Session deletion** | `DELETE /sessions/{session_id}` also deletes `backend/data/vector_stores/{session_id}/` recursively |
| **System prompt** | Adjusts based on `has_notes` — if false: *"No notes uploaded. Web search available."* |

---

## Resolved Decisions (From User Feedback)

| Decision | Resolution |
|---|---|
| Python environment | **New venv** in `backend/` |
| Tailwind version | **v3** (not v4) |
| UI components | **Custom Tailwind** components — no shadcn/ui CLI |
| Audio support | **Removed entirely** — no audio upload, no audio in messages |
| ChromaDB path | **Absolute path** in `.env`: `E:/Python/PDF-QA system/jupyter/chroma_langchain_db` (reference only) |
| `generate_diagram` tool | **No nested LLM call** — only calls `retrieve_chunks`, returns raw chunks. The outer agentic loop generates Mermaid syntax. |
| Frontend first load | Auto-creates a session via `POST /sessions` if no `activeSessionId` |
| `huggingface_hub` | Added to `requirements.txt` |

---

## Proposed Changes

### Phase 1: Backend Core (`backend/core/`)

Port the notebook's Python logic into clean, modular files. All 7 tools, embeddings, vector store management, and the agentic loop.

---

#### [NEW] [requirements.txt](file:///e:/Python/PDF-QA%20system/backend/requirements.txt)

```
fastapi[standard]
uvicorn[standard]
websockets
python-multipart
python-dotenv
langchain-core
langchain-ollama
langchain-chroma
sentence-transformers
torch
chromadb
exa-py
google-genai
huggingface_hub
aiofiles
pydantic
```

#### [NEW] [.env](file:///e:/Python/PDF-QA%20system/backend/.env)

```
GEMINI_API_KEY=<from jupyter/.env>
EXA_API_KEY=<from jupyter/.env>
HF_TOKEN=<from jupyter/.env>
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e2b
EMBEDDING_MODEL=google/embeddinggemma-300M
CHROMA_REFERENCE_DIR=E:/Python/PDF-QA system/jupyter/chroma_langchain_db
CHROMA_COLLECTION=spm_knowledge
BACKEND_PORT=8000
```

> [!NOTE]
> `CHROMA_REFERENCE_DIR` is kept as reference but is **not connected to** by the backend. Per-session vector stores are created at `backend/data/vector_stores/{session_id}/`.

---

#### [NEW] [core/\_\_init\_\_.py](file:///e:/Python/PDF-QA%20system/backend/core/__init__.py)
Empty init file for the package.

#### [NEW] [core/embeddings.py](file:///e:/Python/PDF-QA%20system/backend/core/embeddings.py)
- Direct port of `EmbeddingGemmaLangChain` class from notebook
- `embed_documents(texts)` — batched encoding with `prompt_name="Retrieval-document"`
- `embed_query(text)` — single query encoding with `prompt_name="Retrieval-query"`
- `build_embedding_text(obj)` — constructs embedding-ready string from knowledge object
- `load_embedding_model()` — loads `SentenceTransformer("google/embeddinggemma-300M")`, logs to HuggingFace first via `huggingface_hub.login(token=HF_TOKEN)`

#### [NEW] [core/vectorstore.py](file:///e:/Python/PDF-QA%20system/backend/core/vectorstore.py)
**Per-session vector store management:**
- `create_session_vectorstore(session_id, documents, embedding_fn)`:
  - Creates `backend/data/vector_stores/{session_id}/` directory
  - Calls `Chroma.from_documents(documents, embedding, collection_name=session_id, persist_directory=path)`
  - Returns the Chroma instance
- `load_session_vectorstore(session_id, embedding_fn)`:
  - Reconnects to existing store at `backend/data/vector_stores/{session_id}/`
  - Returns `None` if path doesn't exist (session has no notes)
- `delete_session_vectorstore(session_id)`:
  - Recursively deletes `backend/data/vector_stores/{session_id}/`
- `add_documents_to_session(session_id, documents, embedding_fn)`:
  - Loads existing store, adds new documents

#### [NEW] [core/llm.py](file:///e:/Python/PDF-QA%20system/backend/core/llm.py)
- `get_llm()` → `ChatOllama(model="gemma4:e2b", temperature=1.0, top_p=0.95, top_k=64)`
- `get_llm_with_tools(llm, tools)` → `llm.bind_tools(tools)` with dynamic tool list based on toggles
- `check_ollama_status()` → async GET `http://localhost:11434/api/tags`, raises clear error if down

#### [NEW] [core/tools.py](file:///e:/Python/PDF-QA%20system/backend/core/tools.py)
All 7 tool functions. Each returns a JSON **string**.

1. **`retrieve_chunks(query, top_k=4, filter_type=None, filter_unit=None)`**
   - Receives `vector_store` from agent context (not global)
   - If `vector_store is None` → returns `{"status": "no_notes", "message": "No PDF notes uploaded for this session. Use web_search instead."}`
   - Otherwise: builds `$and`/`$or` Chroma filter, runs `similarity_search_with_score`
   - Returns `{status, query, num_results, chunks: [{similarity_score, topic, section, type, unit, content}]}`

2. **`list_topics()`**
   - Receives `vector_store` from agent context
   - If `vector_store is None` → returns `{"status": "no_notes"}`
   - Otherwise: extracts unique metadata values from collection
   - Returns `{status, total_chunks, units, topics, sections, types}`

3. **`web_search(query, num_results=3)`**
   - Uses `exa_client.search_and_contents()` with `type="auto"`, `highlights.max_characters=3000`
   - Returns `{status, query, num_results, results: [{title, url, highlights, published}]}`

4. **`generate_diagram(topic, diagram_type="flowchart")`**
   - **No nested LLM call**
   - Calls `retrieve_chunks(topic)` internally to get relevant chunks
   - Returns `{status, topic, diagram_type, chunks: [...]}` — raw chunk data
   - The agentic loop's Gemma response generates the Mermaid syntax from these chunks as its final answer with a `diagram` marker

5. **`save_memory(key, value)`** → delegates to `memory.py`
6. **`load_memory()`** → delegates to `memory.py`
7. **`summarize_session(session_id)`** → delegates to `memory.py`

> [!NOTE]
> Tools 1–4 need `vector_store` and `exa_client` injected at runtime. We use closures/partials when binding tools to pass the session's vector store instance per-request.

#### [NEW] [core/agent.py](file:///e:/Python/PDF-QA%20system/backend/core/agent.py)

- **`build_system_prompt(topics_data, memory_data, has_notes)`**:
  - If `has_notes=True`: includes Knowledge Base Overview (units, topics, types) + tool priority rules from notebook
  - If `has_notes=False`: *"No notes uploaded for this session. You can answer questions using web search. The user can upload PDF notes at any time."*
  - Appends memory data: *"User preferences and context: {memory_dict}"*
  - Prepends `<|think|>` token when `enable_thinking=True`

- **`execute_tool_call(tool_call, tool_map)`** → looks up function, calls with args, returns `ToolMessage`. Handles unknown tool names and TypeError gracefully (direct port from notebook).

- **`async run_agent_streaming(messages, system_prompt, llm_with_tools, tool_map, websocket, options)`**:
  - Async agentic loop, `MAX_ITERATIONS=6`
  - Uses `llm_with_tools.astream(messages)` for token-level streaming
  - Sends WebSocket JSON events:
    - `{"type": "thinking", "content": "..."}` — if thinking enabled, parsed from `<|channel>thought...<channel|>` delimiters
    - `{"type": "tool_call", "tool": "...", "args": {...}}` — if verbose enabled
    - `{"type": "tool_result", "tool": "...", "result": "..."}` — if verbose enabled
    - `{"type": "content", "content": "..."}` — streamed answer tokens
    - `{"type": "diagram", "mermaid_code": "..."}` — when detected in final answer (Gemma wraps mermaid in code fences)
    - `{"type": "done", "session_id": "..."}`
    - `{"type": "error", "message": "..."}`
  - Strips thinking content before appending AIMessage to history
  - Tool execution uses `asyncio.to_thread()` for sync Chroma/Exa calls
  - Multimodal content: image base64 prepended before text in HumanMessage

#### [NEW] [core/memory.py](file:///e:/Python/PDF-QA%20system/backend/core/memory.py)
- `save_memory(key, value, session_id)` — thread-safe JSON file I/O with asyncio lock
- `load_memory()` — reads all memories from `backend/data/memory.json`
- `delete_memory(key)` — removes a key
- `summarize_session(session_id, llm)` — reads session file, prompts Gemma for 3–5 sentence summary, saves to `backend/data/sessions/{session_id}_summary.json`

#### [NEW] [core/pdf_pipeline.py](file:///e:/Python/PDF-QA%20system/backend/core/pdf_pipeline.py)
- `async extract_knowledge_objects(pdf_bytes, filename)`:
  - Calls Gemini 2.5 Flash API with the PDF extraction prompt from notebook
  - Returns `{markdown, knowledge_objects}` 
- `build_langchain_documents(knowledge_objects)`:
  - Converts knowledge objects to LangChain `Document` objects with metadata
  - Uses `build_embedding_text()` for page_content
- `async process_pdf(pdf_bytes, filename, session_id, embedding_fn, progress_callback)`:
  - Stage 1: Extract with Gemini (progress 0–40%)
  - Stage 2: Build documents (progress 40–60%)
  - Stage 3: Create/update session vector store via `create_session_vectorstore()` (progress 60–100%)
  - Returns metadata: topic count, chunk count, note_id

---

### Phase 2: Backend API (`backend/routers/` + `backend/main.py`)

---

#### [NEW] [main.py](file:///e:/Python/PDF-QA%20system/backend/main.py)
- FastAPI app with **lifespan** event handler:
  - **Startup**: 
    1. Load env vars
    2. Login to HuggingFace (`huggingface_hub.login(token=HF_TOKEN)`)
    3. Load EmbeddingGemma model (~30s) → store in `app.state.embedding_model`
    4. Create `EmbeddingGemmaLangChain` wrapper → `app.state.embedding_fn`
    5. Check Ollama is running → fail fast with clear error if not
    6. Create `ChatOllama` LLM → `app.state.llm`
    7. Init Exa client → `app.state.exa_client`
    8. Load memories → `app.state.memories`
  - **No global vector store** — each session loads its own on demand
- CORS middleware: allow `http://localhost:5173`
- Mount routers: chat, sessions, upload, notes, memory
- Health check: `GET /health` → `{status, ollama, embedding_model, sessions_count}`

#### [NEW] [routers/\_\_init\_\_.py](file:///e:/Python/PDF-QA%20system/backend/routers/__init__.py)
Empty init file.

#### [NEW] [routers/chat.py](file:///e:/Python/PDF-QA%20system/backend/routers/chat.py)
- **`WebSocket /ws/chat/{session_id}`**:
  - On connect: load session from file, load session's vector store (if `has_notes=True`)
  - Receive JSON: `{message, image_base64, enable_thinking, enable_verbose, stream, enable_web_search}`
  - Construct `HumanMessage`:
    - If `image_base64`: content = `[{type: "image_url", image_url: {url: "data:image/jpeg;base64,..."}}, {type: "text", text: message}]`
    - Otherwise: content = message string
  - Build tool list based on toggles:
    - Always: `retrieve_chunks`, `list_topics`, `generate_diagram`, `save_memory`
    - If `enable_web_search`: add `web_search`
  - Bind session's vector store into tool closures
  - Call `run_agent_streaming()` with WebSocket
  - Save updated history to session file
  - Auto-title: on first message, take first 40 chars → prompt Gemma: "Summarize in 5 words: {text}"

#### [NEW] [routers/sessions.py](file:///e:/Python/PDF-QA%20system/backend/routers/sessions.py)
- `GET /sessions` — list all sessions sorted by `updated_at` desc
- `POST /sessions` — create new session file, returns `{session_id, title, created_at}`
  - Session JSON format:
    ```json
    {
      "session_id": "uuid",
      "title": "New Chat",
      "created_at": "ISO",
      "updated_at": "ISO",
      "model": "gemma4:e2b",
      "has_notes": false,
      "vector_store_path": null,
      "messages": [],
      "summary": null,
      "memory_keys": [],
      "note_metadata": null
    }
    ```
- `GET /sessions/{session_id}` — full chat history
- `DELETE /sessions/{session_id}` — delete session file **AND** `backend/data/vector_stores/{session_id}/` recursively
- `PUT /sessions/{session_id}/title` — rename session
- `POST /sessions/{session_id}/summarize` — trigger `summarize_session`

#### [NEW] [routers/upload.py](file:///e:/Python/PDF-QA%20system/backend/routers/upload.py)
- `POST /upload/image` — accepts jpg/png/webp, saves to `uploads/images/{uuid}.{ext}`, returns `{file_id, base64}`

#### [NEW] [routers/notes.py](file:///e:/Python/PDF-QA%20system/backend/routers/notes.py)
- `POST /notes/upload` — **requires `session_id` parameter**
  - Upload PDF → save to `uploads/pdfs/{uuid}.pdf`
  - Stream progress via SSE:
    - `{stage: "extracting", progress: 10, message: "Extracting with Gemini..."}`
    - `{stage: "embedding", progress: 50, message: "Building embeddings..."}`
    - `{stage: "indexing", progress: 80, message: "Indexing to ChromaDB..."}`
    - `{stage: "done", progress: 100, message: "Done!"}`
  - After indexing: update session JSON → `has_notes=true`, `vector_store_path=backend/data/vector_stores/{session_id}/`, `note_metadata={filename, topic_count, chunk_count, created_at}`
- `GET /notes/topics?session_id=...` — calls `list_topics()` for that session's vector store
- `DELETE /notes/{session_id}` — remove note's vectors, reset session's `has_notes=false`

#### [NEW] [routers/memory.py](file:///e:/Python/PDF-QA%20system/backend/routers/memory.py)
- `GET /memory` — returns all saved memories
- `POST /memory` — save a memory `{key, value}`
- `DELETE /memory/{key}` — delete a memory

---

### Phase 3: Frontend Foundation

Scaffold with Vite + React + TypeScript + **Tailwind CSS v3** (custom components, no shadcn/ui).

---

#### Frontend scaffolding
```bash
npx -y create-vite@latest ./ --template react-ts
npm install tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
npm install framer-motion zustand @tanstack/react-query
npm install react-markdown remark-gfm rehype-highlight
npm install mermaid lucide-react
```

#### [NEW] [tailwind.config.js](file:///e:/Python/PDF-QA%20system/frontend/tailwind.config.js)
- Content paths: `./src/**/*.{ts,tsx}`
- Dark mode: `class`
- Extended theme: custom color palette (slate/zinc/purple/blue), fonts (Inter, JetBrains Mono)
- Custom animations: `fadeIn`, `slideUp`, `pulse-slow`

#### [NEW] [index.css](file:///e:/Python/PDF-QA%20system/frontend/src/index.css)
- `@tailwind base/components/utilities`
- CSS variables for design tokens (colors, radii, shadows)
- Import Google Fonts: Inter (UI), JetBrains Mono (code)
- Custom scrollbar styling
- Glassmorphism utility classes
- Dark mode defaults

#### [NEW] [.env](file:///e:/Python/PDF-QA%20system/frontend/.env)
```
VITE_BACKEND_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

#### [NEW] [types/index.ts](file:///e:/Python/PDF-QA%20system/frontend/src/types/index.ts)
```typescript
// Core types — NO audio references anywhere
interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: string;
  attachments?: Attachment[];   // images only
  tool_calls?: ToolCall[];
  thinking?: string;
  diagrams?: DiagramData[];
}

interface Attachment {
  type: 'image';    // no audio
  file_id: string;
  base64: string;
  filename: string;
  thumbnail?: string;
}

interface Session {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  has_notes: boolean;
  vector_store_path: string | null;
  messages: Message[];
  summary: string | null;
  note_metadata: NoteMetadata | null;
}

interface ChatSettings {
  enable_thinking: boolean;   // default false
  enable_verbose: boolean;    // default false
  stream: boolean;            // always true
  enable_web_search: boolean; // default true
}

interface WSEvent {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'content' | 'diagram' | 'done' | 'error';
  content?: string;
  tool?: string;
  args?: Record<string, unknown>;
  result?: string;
  mermaid_code?: string;
  session_id?: string;
  message?: string;
}

// ... Memory, NoteMetadata, TopicsData, DiagramData, ToolCall
```

#### [NEW] [store/chatStore.ts](file:///e:/Python/PDF-QA%20system/frontend/src/store/chatStore.ts)
Zustand store:
- `sessions`, `activeSessionId` — on first load, if `activeSessionId` is null → auto-call `POST /sessions` → set as active
- `messages` (current session), `isStreaming`
- `currentThinking`, `currentContent` (live streaming accumulators)
- `settings: ChatSettings`
- `memories`, `darkMode`
- Actions: `createSession`, `deleteSession`, `setActiveSession`, `addMessage`, `appendStreamContent`, `updateSettings`, `toggleDarkMode`

#### [NEW] [lib/api.ts](file:///e:/Python/PDF-QA%20system/frontend/src/lib/api.ts)
REST client functions using `VITE_BACKEND_URL`:
- Sessions: `fetchSessions()`, `createSession()`, `deleteSession(id)`, `renameSession(id, title)`
- Memory: `fetchMemories()`, `saveMemory(key, value)`, `deleteMemory(key)`
- Notes: `uploadNote(sessionId, file)`, `fetchTopics(sessionId)`, `deleteNote(sessionId)`
- Upload: `uploadImage(file)` — returns `{file_id, base64}`

#### [NEW] [hooks/useWebSocket.ts](file:///e:/Python/PDF-QA%20system/frontend/src/hooks/useWebSocket.ts)
- Manages WebSocket to `ws://localhost:8000/ws/chat/{session_id}`
- Parses incoming JSON events by `type` field
- Updates Zustand store: `appendStreamContent`, `setThinking`, `addToolCall`, `addDiagram`
- `sendMessage(message, imageBase64, settings)` — sends JSON payload
- Auto-reconnect on disconnect
- Cleans up on session change

---

### Phase 4: Frontend UI Components

All custom Tailwind — premium Claude-like aesthetic with dark/light mode.

---

#### [NEW] [components/layout/Sidebar.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/layout/Sidebar.tsx)
- 260px fixed sidebar, `bg-gray-950/90 backdrop-blur-xl` in dark mode
- **Top**: App logo "PDF-QA" + dark mode toggle (sun/moon)
- **"+ New Chat"** button: gradient purple/blue pill, creates session via API
- **Session list** grouped by date:
  - Click → set active session, load history
  - Hover → show rename ✏️ / delete 🗑️ icons (lucide-react)
  - Active session highlighted with accent border
  - Badge icon 📚 if `has_notes=true`
- **Memory panel**: brain icon + memory count badge + "View All" expand
- **Notes panel**: shows note metadata if active session `has_notes=true`, "Upload Notes" button opens modal
- Responsive: hamburger toggle on `md:` breakpoint

#### [NEW] [components/layout/Header.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/layout/Header.tsx)
- Session title (click-to-edit with inline input)
- Notes status badge: "📚 Notes loaded" or "No notes" 
- Right side — **toggle pills** with `TogglePanel`:
  - 🧠 Thinking: OFF/ON — purple accent
  - 📋 Verbose: OFF/ON — blue accent
  - ⚡ Stream: ON — always on, muted
  - 🌐 Web Search: ON/OFF — green accent

#### [NEW] [components/chat/ChatWindow.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/chat/ChatWindow.tsx)
- Scrollable `overflow-y-auto` with smooth scroll to bottom on new content
- **Empty state**: centered welcome message with app icon, "Upload a PDF or ask a question" subtitle, 3–4 suggested prompt pills
- Maps messages → `MessageBubble` with Framer Motion `animate` transitions
- Shows typing indicator (3 pulsing dots) during streaming
- `useRef` for scroll container, auto-scroll with `scrollIntoView`

#### [NEW] [components/chat/MessageBubble.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/chat/MessageBubble.tsx)
- **User messages**: right-aligned, `bg-purple-600 text-white rounded-2xl rounded-br-md`, max-width 70%
  - Shows image thumbnail if attached
- **Assistant messages**: left-aligned, `bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-bl-md`
  - `react-markdown` with `remark-gfm` for tables, lists, bold, etc.
  - `rehype-highlight` for code blocks with copy button
  - Renders `ThinkingBubble` above content if `message.thinking` exists
  - Renders `ToolCallCard` list if `message.tool_calls` exists and verbose was on
  - Renders `DiagramRenderer` inline if `message.diagrams` exists

#### [NEW] [components/chat/MessageInput.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/chat/MessageInput.tsx)
- Auto-resizing `<textarea>` (1–6 lines), `bg-gray-100 dark:bg-gray-800 rounded-2xl`
- **Left**: image attach button 🖼️ → file input (jpg/png/webp)
- **Right**: send button (arrow-up icon), gradient accent, disabled when empty or streaming
- Attached image shown as removable chip with thumbnail + ✕ above textarea
- Enter to send, Shift+Enter for newline
- During streaming: send button becomes "Stop ■" button
- No audio attachment button

#### [NEW] [components/chat/ThinkingBubble.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/chat/ThinkingBubble.tsx)
- Collapsible card: `bg-purple-50 dark:bg-purple-900/20 border-purple-200`
- Header: brain icon + "Thinking..." + chevron toggle
- Body: italic `text-gray-500` content, monospace feel
- Framer Motion `AnimatePresence` for expand/collapse
- Streams live during thinking phase → auto-collapses when content starts

#### [NEW] [components/chat/ToolCallCard.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/chat/ToolCallCard.tsx)
- Compact inline card: tool icon + name + collapsible args/result
- Color coding:
  - 🔍 `retrieve_chunks` → blue
  - 📋 `list_topics` → purple  
  - 🌐 `web_search` → green
  - 📊 `generate_diagram` → orange
  - 🧠 `save_memory` / `load_memory` → pink
- `font-mono text-xs` for JSON args and results
- Collapse by default, click to expand

#### [NEW] [components/chat/DiagramRenderer.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/chat/DiagramRenderer.tsx)
- Receives `mermaid_code` string
- Uses `mermaid.render()` (initialized with `startOnLoad: false`)
- Card wrapper: title bar + SVG output + "Copy Mermaid Code" button
- Dark/light theme auto-synced
- If render fails: fallback shows raw code in a code block
- Supports: flowchart, sequence, mindmap, graph

#### [NEW] [components/upload/FileUploadZone.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/upload/FileUploadZone.tsx)
- Drag-and-drop zone with dashed border
- Visual feedback: border color change on drag hover
- Image-only file type validation (no audio)
- Returns base64 + metadata

#### [NEW] [components/upload/NotesUpload.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/upload/NotesUpload.tsx)
- **Modal** overlay with glassmorphism backdrop
- Drag-and-drop PDF zone (accepts `.pdf` only)
- Progress bar with animated stages:
  1. "Extracting with Gemini..." (0–40%)
  2. "Building embeddings..." (40–60%)
  3. "Indexing to ChromaDB..." (60–100%)
  4. "Done! ✓" — green checkmark
- After success: shows topic count, chunk count
- Sends `session_id` with the upload
- Close button returns to chat

#### [NEW] [components/settings/TogglePanel.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/components/settings/TogglePanel.tsx)
- Reusable toggle pill: `{icon, label, enabled, onChange, accentColor}`
- Animated switch track with color transition
- Compact size for header row layout

#### [NEW] [lib/mermaid.ts](file:///e:/Python/PDF-QA%20system/frontend/src/lib/mermaid.ts)
- `initMermaid()` — call once with `startOnLoad: false`, theme from dark mode
- `renderDiagram(id, code)` → returns SVG string
- Theme sync function for dark/light switch

#### [NEW] [pages/ChatPage.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/pages/ChatPage.tsx)
- Layout: `Sidebar | (Header + ChatWindow + MessageInput)`
- `flex h-screen` with sidebar and main area
- On mount:
  1. Fetch sessions list
  2. If no `activeSessionId` → `POST /sessions` → set active
  3. Open WebSocket to active session
  4. Fetch memories
- Responsive: sidebar hidden below `md:` breakpoint with hamburger

#### [NEW] [App.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/App.tsx)
- `QueryClientProvider` (React Query)
- Dark mode: reads `darkMode` from Zustand, sets `class="dark"` on `<html>`
- Renders `ChatPage`

#### [NEW] [main.tsx](file:///e:/Python/PDF-QA%20system/frontend/src/main.tsx)
- `ReactDOM.createRoot` → `<App />`

---

### Phase 5: Integration & Polish

#### Data directories to create

```
backend/data/
backend/data/memory.json          ← initialized as {}
backend/data/chats/                ← session JSON files
backend/data/sessions/             ← session summaries
backend/data/vector_stores/        ← per-session ChromaDB stores
backend/uploads/
backend/uploads/pdfs/
backend/uploads/images/
```

#### End-to-end flow

1. User opens app → frontend creates session → WebSocket connects
2. User sends question (no notes) → Gemma uses web_search → streams response
3. User uploads PDF in sidebar → Gemini extracts → embeddings built → ChromaDB indexed → session gets `has_notes=true`
4. User sends question → Gemma uses `retrieve_chunks` with session's vector store → streams response
5. User asks for diagram → Gemma calls `generate_diagram` → retrieves chunks → generates Mermaid in final answer → frontend renders SVG
6. User toggles thinking → system prompt gets `<|think|>` → thinking block streams → then final answer
7. User saves memory → persists across sessions
8. User closes/refreshes → sessions persist → chat resumes

---

## Verification Plan

### Automated Tests
1. **Backend startup**: Verify EmbeddingGemma loads, Ollama responds, Exa client initialized
2. **Session CRUD**: `curl` each REST endpoint — create, list, get, delete, rename
3. **WebSocket smoke test**: Connect with `wscat`, send message, verify event stream
4. **Notes upload**: Upload PDF, verify per-session vector store created at correct path
5. **Frontend build**: `npm run build` produces no errors

### Manual Verification (Browser)
1. Open `http://localhost:5173` → verify auto-session creation, Claude-like UI
2. Send question without notes → verify web_search fallback + streaming
3. Upload PDF → verify progress bar stages → verify `has_notes` badge appears
4. Send question with notes → verify `retrieve_chunks` + streaming response
5. Toggle thinking → verify collapsible thinking block
6. Toggle verbose → verify tool call cards
7. Ask for diagram → verify Mermaid renders inline
8. Dark/light mode toggle → verify all components
9. Create multiple sessions → verify sidebar list + switching
10. Refresh page → verify session persistence
11. Delete session → verify vector store cleanup
