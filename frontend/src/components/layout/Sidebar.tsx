import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  MessageSquare,
  Trash2,
  Pencil,
  Sun,
  Moon,
  BookOpen,
  Brain,
  Upload,
  X,
  Check,
} from 'lucide-react'
import { useChatStore } from '../../store/chatStore'
import * as api from '../../lib/api'

interface SidebarProps {
  onUploadNotes: () => void
  onClose?: () => void
}

export default function Sidebar({ onUploadNotes, onClose }: SidebarProps) {
  const sessions = useChatStore((s) => s.sessions)
  const activeSessionId = useChatStore((s) => s.activeSessionId)
  const darkMode = useChatStore((s) => s.darkMode)
  const memories = useChatStore((s) => s.memories)
  const activeSession = useChatStore((s) => s.getActiveSession())

  const setActiveSessionId = useChatStore((s) => s.setActiveSessionId)
  const addSession = useChatStore((s) => s.addSession)
  const removeSession = useChatStore((s) => s.removeSession)
  const updateSessionTitle = useChatStore((s) => s.updateSessionTitle)
  const toggleDarkMode = useChatStore((s) => s.toggleDarkMode)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [showMemories, setShowMemories] = useState(false)

  const handleNewChat = async () => {
    try {
      const session = await api.createSession()
      addSession(session)
      setActiveSessionId(session.session_id)
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    try {
      await api.deleteSession(sessionId)
      removeSession(sessionId)
    } catch (err) {
      console.error('Failed to delete session:', err)
    }
  }

  const startRename = (e: React.MouseEvent, sessionId: string, title: string) => {
    e.stopPropagation()
    setEditingId(sessionId)
    setEditTitle(title)
  }

  const saveRename = async (sessionId: string) => {
    if (!editTitle.trim()) {
      setEditingId(null)
      return
    }
    updateSessionTitle(sessionId, editTitle.trim())
    setEditingId(null)
    try {
      await api.renameSession(sessionId, editTitle.trim())
    } catch {
      // silent
    }
  }

  // Group sessions by date
  const grouped = groupSessionsByDate(sessions)
  const memoryCount = Object.keys(memories).length

  return (
    <div className="flex flex-col h-full bg-gray-950/95 backdrop-blur-xl text-gray-300 w-[260px]">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-accent-600 flex items-center justify-center">
            <BookOpen size={14} className="text-white" />
          </div>
          <span className="text-sm font-semibold text-white">PDF-QA</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={toggleDarkMode}
            className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
            aria-label="Toggle dark mode"
          >
            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          {/* Mobile close */}
          {onClose && (
            <button
              onClick={onClose}
              className="md:hidden p-1.5 rounded-lg hover:bg-white/10 transition-colors"
              aria-label="Close sidebar"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* New Chat button */}
      <div className="px-3 mb-3">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl
                     bg-gradient-to-r from-accent-600 to-blue-600 
                     hover:from-accent-500 hover:to-blue-500
                     text-white text-sm font-medium transition-all shadow-lg shadow-accent-600/20"
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 space-y-4 scrollbar-thin">
        {grouped.map((group) => (
          <div key={group.label}>
            <p className="px-2 mb-1 text-[10px] uppercase tracking-wider text-gray-500 font-medium">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.sessions.map((session) => {
                const isActive = session.session_id === activeSessionId
                const isEditing = editingId === session.session_id

                return (
                  <div
                    key={session.session_id}
                    onClick={() => setActiveSessionId(session.session_id)}
                    className={`
                      group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-all
                      ${
                        isActive
                          ? 'bg-white/10 border-l-2 border-accent-500'
                          : 'hover:bg-white/5 border-l-2 border-transparent'
                      }
                    `}
                  >
                    <MessageSquare size={14} className="flex-shrink-0 text-gray-500" />

                    {isEditing ? (
                      <div className="flex-1 flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        <input
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveRename(session.session_id)
                            if (e.key === 'Escape') setEditingId(null)
                          }}
                          onBlur={() => saveRename(session.session_id)}
                          autoFocus
                          className="flex-1 bg-transparent text-xs text-white border-b border-accent-500 outline-none px-0.5"
                          maxLength={60}
                        />
                        <button onClick={() => saveRename(session.session_id)}>
                          <Check size={12} className="text-accent-400" />
                        </button>
                      </div>
                    ) : (
                      <span className="flex-1 text-xs truncate">
                        {session.title}
                      </span>
                    )}

                    {session.has_notes && !isEditing && (
                      <BookOpen size={10} className="flex-shrink-0 text-green-400" />
                    )}

                    {!isEditing && (
                      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => startRename(e, session.session_id, session.title)}
                          className="p-1 rounded hover:bg-white/10"
                          aria-label="Rename session"
                        >
                          <Pencil size={10} />
                        </button>
                        <button
                          onClick={(e) => handleDelete(e, session.session_id)}
                          className="p-1 rounded hover:bg-red-500/20 text-red-400"
                          aria-label="Delete session"
                        >
                          <Trash2 size={10} />
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom panels */}
      <div className="border-t border-white/10 px-3 py-3 space-y-2">
        {/* Memory panel */}
        <button
          onClick={() => setShowMemories(!showMemories)}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-colors text-xs"
        >
          <Brain size={14} className="text-pink-400" />
          <span>Memories</span>
          {memoryCount > 0 && (
            <span className="ml-auto px-1.5 py-0.5 rounded-full bg-pink-500/20 text-pink-400 text-[10px]">
              {memoryCount}
            </span>
          )}
        </button>

        <AnimatePresence>
          {showMemories && memoryCount > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
                {Object.entries(memories).map(([key, value]) => (
                  <div key={key} className="text-[10px] text-gray-500">
                    <span className="text-gray-400 font-medium">{key}:</span> {String(value)}
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Notes upload */}
        {activeSession && (
          <button
            onClick={onUploadNotes}
            className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-colors text-xs"
          >
            <Upload size={14} className="text-blue-400" />
            <span>{activeSession.has_notes ? 'Re-upload Notes' : 'Upload Notes'}</span>
            {activeSession.note_metadata && (
              <span className="ml-auto text-[10px] text-gray-500">
                {activeSession.note_metadata.chunk_count} chunks
              </span>
            )}
          </button>
        )}
      </div>
    </div>
  )
}

// ── Helpers ──────────────────────────────────────────────────────────────────

import type { Session } from '../../types'

function groupSessionsByDate(sessions: Session[]): { label: string; sessions: Session[] }[] {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const weekAgo = new Date(today.getTime() - 7 * 86400000)

  const groups: Record<string, Session[]> = {
    Today: [],
    Yesterday: [],
    'This Week': [],
    Older: [],
  }

  for (const session of sessions) {
    const date = new Date(session.updated_at)
    if (date >= today) groups['Today'].push(session)
    else if (date >= yesterday) groups['Yesterday'].push(session)
    else if (date >= weekAgo) groups['This Week'].push(session)
    else groups['Older'].push(session)
  }

  return Object.entries(groups)
    .filter(([, s]) => s.length > 0)
    .map(([label, s]) => ({ label, sessions: s }))
}
