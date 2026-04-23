import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, ChevronDown } from 'lucide-react'

interface ThinkingBubbleProps {
  content: string
  isLive?: boolean
}

export default function ThinkingBubble({
  content,
  isLive = false,
}: ThinkingBubbleProps) {
  const [expanded, setExpanded] = useState(isLive)

  // Auto-expand when live thinking starts, auto-collapse when done
  useEffect(() => {
    if (isLive) setExpanded(true)
  }, [isLive])

  if (!content) return null

  return (
    <div className="mb-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs font-medium text-purple-600 dark:text-purple-400 
                   hover:text-purple-700 dark:hover:text-purple-300 transition-colors"
      >
        <Brain size={14} className={isLive ? 'animate-pulse-slow' : ''} />
        <span>{isLive ? 'Thinking...' : 'Thought process'}</span>
        <ChevronDown
          size={14}
          className={`transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div
              className="mt-2 p-3 rounded-lg text-xs leading-relaxed
                         bg-purple-50 dark:bg-purple-900/20 
                         border border-purple-200 dark:border-purple-800/50
                         text-gray-600 dark:text-gray-400 italic
                         font-mono max-h-60 overflow-y-auto"
            >
              {content}
              {isLive && (
                <span className="inline-block w-1.5 h-3.5 bg-purple-500 ml-0.5 animate-pulse" />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
