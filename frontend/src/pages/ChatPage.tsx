import { useEffect, useState, useCallback } from 'react'
import { useChatStore } from '../store/chatStore'
import type { Message } from '../types'
import { useWebSocket } from '../hooks/useWebSocket'
import * as api from '../lib/api'
import { initMermaid } from '../lib/mermaid'

import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import ChatWindow from '../components/chat/ChatWindow'
import MessageInput from '../components/chat/MessageInput'
import NotesUpload from '../components/upload/NotesUpload'

export default function ChatPage() {
  const [showNotesUpload, setShowNotesUpload] = useState(false)

  const activeSessionId = useChatStore((s) => s.activeSessionId)
  const sessionsLoaded = useChatStore((s) => s.sessionsLoaded)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const settings = useChatStore((s) => s.settings)
  const darkMode = useChatStore((s) => s.darkMode)
  const sidebarOpen = useChatStore((s) => s.sidebarOpen)

  const setSessions = useChatStore((s) => s.setSessions)
  const setActiveSessionId = useChatStore((s) => s.setActiveSessionId)
  const setSessionsLoaded = useChatStore((s) => s.setSessionsLoaded)
  const addSession = useChatStore((s) => s.addSession)
  const addMessage = useChatStore((s) => s.addMessage)
  const setIsStreaming = useChatStore((s) => s.setIsStreaming)
  const resetStreamState = useChatStore((s) => s.resetStreamState)
  const setMemories = useChatStore((s) => s.setMemories)
  const toggleSidebar = useChatStore((s) => s.toggleSidebar)
  const setSidebarOpen = useChatStore((s) => s.setSidebarOpen)

  const { sendMessage, disconnect } = useWebSocket(activeSessionId)

  // Initialize mermaid with current theme
  useEffect(() => {
    initMermaid(darkMode)
  }, [darkMode])

  // Load full session data when active session changes
  useEffect(() => {
    if (!activeSessionId || !sessionsLoaded) return

    async function loadSession() {
      try {
        const fullSession = await api.getSession(activeSessionId!)
        // Update the session in the store with full data (including messages)
        const store = useChatStore.getState()
        const updated = store.sessions.map((s) =>
          s.session_id === activeSessionId
            ? {
                ...s,
                messages: (fullSession.messages ?? []).map((m: any, i: number) => ({
                  id: m.id || `msg_loaded_${i}`,
                  role: m.role as 'user' | 'assistant' | 'tool',
                  content: m.content || '',
                  timestamp: m.timestamp || fullSession.created_at,
                  thinking: m.thinking,
                  tool_calls: m.tool_calls,
                  diagrams: m.diagrams,
                  attachments: m.attachments,
                })),
                has_notes: fullSession.has_notes ?? false,
                note_metadata: fullSession.note_metadata ?? null,
                summary: fullSession.summary ?? null,
              }
            : s
        )
        store.setSessions(updated)
      } catch {
        // Session may not exist yet
      }
    }

    loadSession()
  }, [activeSessionId, sessionsLoaded])

  // Load sessions on mount
  useEffect(() => {
    async function init() {
      try {
        // Fetch sessions
        const sessions = await api.fetchSessions()
        setSessions(sessions)

        // If no active session or active session doesn't exist, create one
        const currentActiveId = useChatStore.getState().activeSessionId
        const sessionExists = sessions.some((s) => s.session_id === currentActiveId)

        if (!currentActiveId || !sessionExists) {
          if (sessions.length > 0) {
            setActiveSessionId(sessions[0].session_id)
          } else {
            const newSession = await api.createSession()
            addSession(newSession)
            setActiveSessionId(newSession.session_id)
          }
        }

        // Fetch memories
        try {
          const memories = await api.fetchMemories()
          setMemories(memories)
        } catch {
          // Non-critical
        }

        setSessionsLoaded(true)
      } catch (err) {
        console.error('Failed to initialize:', err)
        setSessionsLoaded(true)
      }
    }

    init()
  }, [])

  // Handle sending a message
  const handleSend = useCallback(
    (message: string, imageBase64: string | null) => {
      if (!activeSessionId) return

      // Add user message to store
      const userMsg = {
        id: `msg_${Date.now()}`,
        role: 'user' as const,
        content: message,
        timestamp: new Date().toISOString(),
        attachments: imageBase64
          ? [
              {
                type: 'image' as const,
                file_id: `img_${Date.now()}`,
                base64: imageBase64,
                filename: 'image.jpg',
              },
            ]
          : undefined,
      }
      addMessage(activeSessionId, userMsg)

      // Start streaming
      setIsStreaming(true)
      resetStreamState()

      // Send via WebSocket
      const sent = sendMessage(message, imageBase64, settings)
      if (!sent) {
        setIsStreaming(false)
        addMessage(activeSessionId, {
          id: `msg_err_${Date.now()}`,
          role: 'assistant',
          content: '⚠️ Connection lost. Please try again.',
          timestamp: new Date().toISOString(),
        })
      }
    },
    [activeSessionId, settings, sendMessage]
  )

  const handleSuggestedPrompt = useCallback(
    (prompt: string) => {
      handleSend(prompt, null)
    },
    [handleSend]
  )

  const handleStop = useCallback(() => {
    disconnect()
    setIsStreaming(false)
  }, [disconnect])

  if (!sessionsLoaded) {
    return (
      <div className="flex items-center justify-center h-screen bg-white dark:bg-gray-900">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-full border-2 border-accent-500 border-t-transparent animate-spin" />
          <p className="text-sm text-gray-500">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 overflow-hidden">
      {/* Sidebar - desktop */}
      <div className="hidden md:block flex-shrink-0">
        <Sidebar
          onUploadNotes={() => setShowNotesUpload(true)}
        />
      </div>

      {/* Sidebar - mobile overlay */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="relative z-10 h-full">
            <Sidebar
              onUploadNotes={() => {
                setShowNotesUpload(true)
                setSidebarOpen(false)
              }}
              onClose={() => setSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header onToggleSidebar={toggleSidebar} />
        <ChatWindow onSuggestedPrompt={handleSuggestedPrompt} />
        <MessageInput
          onSend={handleSend}
          isStreaming={isStreaming}
          onStop={handleStop}
        />
      </div>

      {/* Notes upload modal */}
      {showNotesUpload && activeSessionId && (
        <NotesUpload
          sessionId={activeSessionId}
          onClose={() => setShowNotesUpload(false)}
        />
      )}
    </div>
  )
}
