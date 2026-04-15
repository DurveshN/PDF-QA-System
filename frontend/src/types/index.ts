// ── Core Message Types ──────────────────────────────────────────────────────

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  timestamp: string
  attachments?: Attachment[]
  tool_calls?: ToolCall[]
  thinking?: string
  diagrams?: DiagramData[]
}

export interface Attachment {
  type: 'image'
  file_id: string
  base64: string
  filename: string
  thumbnail?: string
}

export interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  result?: string
}

export interface DiagramData {
  id: string
  mermaid_code: string
  svg?: string
}

// ── Session Types ───────────────────────────────────────────────────────────

export interface Session {
  session_id: string
  title: string
  created_at: string
  updated_at: string
  model: string
  has_notes: boolean
  vector_store_path: string | null
  messages: Message[]
  summary: string | null
  memory_keys: string[]
  note_metadata: NoteMetadata | null
}

export interface NoteMetadata {
  filename: string
  topic_count: number
  chunk_count: number
  created_at: string
  note_id?: string
}

// ── Chat Settings ───────────────────────────────────────────────────────────

export interface ChatSettings {
  enable_thinking: boolean
  enable_verbose: boolean
  stream: boolean
  enable_web_search: boolean
}

// ── WebSocket Event Types ───────────────────────────────────────────────────

export interface WSEvent {
  type:
    | 'thinking'
    | 'tool_call'
    | 'tool_result'
    | 'content'
    | 'diagram'
    | 'done'
    | 'error'
    | 'ready'
  content?: string
  tool?: string
  args?: Record<string, unknown>
  result?: string
  mermaid_code?: string
  session_id?: string
  message?: string
  title?: string
}

// ── Memory Types ────────────────────────────────────────────────────────────

export interface Memory {
  key: string
  value: string
}

// ── Topics Data ─────────────────────────────────────────────────────────────

export interface TopicsData {
  status: string
  total_chunks: number
  units: string[]
  topics: string[]
  sections: string[]
  types: string[]
}

// ── Upload Progress ─────────────────────────────────────────────────────────

export interface UploadProgress {
  stage: string
  progress: number
  message: string
}
