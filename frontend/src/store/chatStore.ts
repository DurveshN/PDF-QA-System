import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Session, Message, ChatSettings, ToolCall, DiagramData } from '../types'
import * as api from '../lib/api'

interface ChatState {
  // Sessions
  sessions: Session[]
  activeSessionId: string | null
  sessionsLoaded: boolean

  // Current streaming state
  isStreaming: boolean
  currentThinking: string
  currentContent: string
  currentToolCalls: ToolCall[]
  currentDiagrams: DiagramData[]

  // Settings
  settings: ChatSettings
  darkMode: boolean

  // Memories
  memories: Record<string, string>

  // Sidebar
  sidebarOpen: boolean

  // Actions
  setSessions: (sessions: Session[]) => void
  setActiveSessionId: (id: string | null) => void
  setSessionsLoaded: (loaded: boolean) => void
  addSession: (session: Session) => void
  removeSession: (id: string) => void
  updateSessionTitle: (id: string, title: string) => void
  updateSessionNotes: (id: string, hasNotes: boolean, metadata: Session['note_metadata']) => void

  // Message actions
  addMessage: (sessionId: string, message: Message) => void
  updateLastAssistantMessage: (sessionId: string, updates: Partial<Message>) => void

  // Streaming actions
  setIsStreaming: (streaming: boolean) => void
  appendThinking: (text: string) => void
  appendContent: (text: string) => void
  addToolCall: (toolCall: ToolCall) => void
  updateToolCallResult: (toolCallId: string, result: string) => void
  addDiagram: (diagram: DiagramData) => void
  resetStreamState: () => void

  // Settings
  updateSettings: (settings: Partial<ChatSettings>) => void
  toggleDarkMode: () => void

  // Memories
  setMemories: (memories: Record<string, string>) => void

  // Sidebar
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void

  // Helpers
  getActiveSession: () => Session | undefined
  getActiveMessages: () => Message[]
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // Initial state
      sessions: [],
      activeSessionId: null,
      sessionsLoaded: false,
      isStreaming: false,
      currentThinking: '',
      currentContent: '',
      currentToolCalls: [],
      currentDiagrams: [],
      settings: {
        enable_thinking: false,
        enable_verbose: false,
        stream: true,
        enable_web_search: true,
      },
      darkMode: true,
      memories: {},
      sidebarOpen: true,

      // Session actions
      setSessions: (sessions) => set({ sessions }),
      setActiveSessionId: (id) => set({ activeSessionId: id }),
      setSessionsLoaded: (loaded) => set({ sessionsLoaded: loaded }),

      addSession: (session) =>
        set((state) => ({
          sessions: [session, ...state.sessions],
        })),

      removeSession: (id) =>
        set((state) => ({
          sessions: state.sessions.filter((s) => s.session_id !== id),
          activeSessionId:
            state.activeSessionId === id
              ? state.sessions.find((s) => s.session_id !== id)?.session_id ?? null
              : state.activeSessionId,
        })),

      updateSessionTitle: (id, title) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.session_id === id ? { ...s, title } : s
          ),
        })),

      updateSessionNotes: (id, hasNotes, metadata) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.session_id === id
              ? { ...s, has_notes: hasNotes, note_metadata: metadata }
              : s
          ),
        })),

      // Message actions
      addMessage: (sessionId, message) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.session_id === sessionId
              ? { ...s, messages: [...s.messages, message], updated_at: new Date().toISOString() }
              : s
          ),
        })),

      updateLastAssistantMessage: (sessionId, updates) =>
        set((state) => ({
          sessions: state.sessions.map((s) => {
            if (s.session_id !== sessionId) return s
            const msgs = [...s.messages]
            const lastIdx = msgs.length - 1
            if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
              msgs[lastIdx] = { ...msgs[lastIdx], ...updates }
            }
            return { ...s, messages: msgs }
          }),
        })),

      // Streaming actions
      setIsStreaming: (streaming) => set({ isStreaming: streaming }),

      appendThinking: (text) =>
        set((state) => ({ currentThinking: state.currentThinking + text })),

      appendContent: (text) =>
        set((state) => ({ currentContent: state.currentContent + text })),

      addToolCall: (toolCall) =>
        set((state) => ({
          currentToolCalls: [...state.currentToolCalls, toolCall],
        })),

      updateToolCallResult: (toolCallId, result) =>
        set((state) => ({
          currentToolCalls: state.currentToolCalls.map((tc) =>
            tc.id === toolCallId ? { ...tc, result } : tc
          ),
        })),

      addDiagram: (diagram) =>
        set((state) => ({
          currentDiagrams: [...state.currentDiagrams, diagram],
        })),

      resetStreamState: () =>
        set({
          currentThinking: '',
          currentContent: '',
          currentToolCalls: [],
          currentDiagrams: [],
        }),

      // Settings
      updateSettings: (newSettings) =>
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        })),

      toggleDarkMode: () =>
        set((state) => ({ darkMode: !state.darkMode })),

      // Memories
      setMemories: (memories) => set({ memories }),

      // Sidebar
      toggleSidebar: () =>
        set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      // Helpers
      getActiveSession: () => {
        const { sessions, activeSessionId } = get()
        return sessions.find((s) => s.session_id === activeSessionId)
      },

      getActiveMessages: () => {
        const session = get().getActiveSession()
        return session?.messages ?? []
      },
    }),
    {
      name: 'pdf-qa-chat-store',
      partialize: (state) => ({
        activeSessionId: state.activeSessionId,
        settings: state.settings,
        darkMode: state.darkMode,
      }),
    }
  )
)
