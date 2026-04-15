import { useState, useRef, useEffect } from 'react'
import { Menu, BookOpen, Pencil, Check } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'
import { renameSession } from '../../lib/api'
import TogglePanel from '../settings/TogglePanel'

interface HeaderProps {
  onToggleSidebar: () => void
}

export default function Header({ onToggleSidebar }: HeaderProps) {
  const activeSession = useChatStore((s) => s.getActiveSession())
  const settings = useChatStore((s) => s.settings)
  const updateSettings = useChatStore((s) => s.updateSettings)
  const updateSessionTitle = useChatStore((s) => s.updateSessionTitle)

  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [editing])

  const startEditing = () => {
    if (!activeSession) return
    setEditTitle(activeSession.title)
    setEditing(true)
  }

  const saveTitle = async () => {
    if (!activeSession || !editTitle.trim()) {
      setEditing(false)
      return
    }
    const newTitle = editTitle.trim()
    updateSessionTitle(activeSession.session_id, newTitle)
    setEditing(false)
    try {
      await renameSession(activeSession.session_id, newTitle)
    } catch {
      // Revert on error
    }
  }

  return (
    <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <div className="flex items-center gap-3">
        {/* Mobile hamburger */}
        <button
          onClick={onToggleSidebar}
          className="md:hidden p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          aria-label="Toggle sidebar"
        >
          <Menu size={20} className="text-gray-600 dark:text-gray-400" />
        </button>

        {/* Session title */}
        {editing ? (
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') saveTitle()
                if (e.key === 'Escape') setEditing(false)
              }}
              onBlur={saveTitle}
              className="text-sm font-medium bg-transparent border-b-2 border-accent-500 
                         outline-none text-gray-800 dark:text-gray-200 px-1 py-0.5"
              maxLength={60}
            />
            <button onClick={saveTitle} className="text-accent-500">
              <Check size={16} />
            </button>
          </div>
        ) : (
          <button
            onClick={startEditing}
            className="flex items-center gap-1.5 text-sm font-medium text-gray-800 dark:text-gray-200 
                       hover:text-accent-600 dark:hover:text-accent-400 transition-colors group"
          >
            {activeSession?.title ?? 'New Chat'}
            <Pencil
              size={12}
              className="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity"
            />
          </button>
        )}

        {/* Notes badge */}
        {activeSession?.has_notes && (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
            <BookOpen size={10} />
            Notes loaded
          </span>
        )}
      </div>

      {/* Toggle pills */}
      <div className="flex items-center gap-1.5">
        <TogglePanel
          icon="🧠"
          label="Think"
          enabled={settings.enable_thinking}
          onChange={(v) => updateSettings({ enable_thinking: v })}
          accentColor="purple"
        />
        <TogglePanel
          icon="📋"
          label="Verbose"
          enabled={settings.enable_verbose}
          onChange={(v) => updateSettings({ enable_verbose: v })}
          accentColor="blue"
        />
        <TogglePanel
          icon="🌐"
          label="Web"
          enabled={settings.enable_web_search}
          onChange={(v) => updateSettings({ enable_web_search: v })}
          accentColor="green"
        />
      </div>
    </header>
  )
}
