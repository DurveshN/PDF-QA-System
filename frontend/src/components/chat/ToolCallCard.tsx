import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { ToolCall } from '../../types'

interface ToolCallCardProps {
  toolCall: ToolCall
}

const toolConfig: Record<string, { icon: string; color: string; bg: string }> = {
  retrieve_chunks: {
    icon: '🔍',
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800/50',
  },
  list_topics: {
    icon: '📋',
    color: 'text-purple-600 dark:text-purple-400',
    bg: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800/50',
  },
  web_search: {
    icon: '🌐',
    color: 'text-green-600 dark:text-green-400',
    bg: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800/50',
  },
  generate_diagram: {
    icon: '📊',
    color: 'text-orange-600 dark:text-orange-400',
    bg: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800/50',
  },
  save_memory: {
    icon: '🧠',
    color: 'text-pink-600 dark:text-pink-400',
    bg: 'bg-pink-50 dark:bg-pink-900/20 border-pink-200 dark:border-pink-800/50',
  },
  load_memory: {
    icon: '🧠',
    color: 'text-pink-600 dark:text-pink-400',
    bg: 'bg-pink-50 dark:bg-pink-900/20 border-pink-200 dark:border-pink-800/50',
  },
}

const defaultConfig = {
  icon: '⚙️',
  color: 'text-gray-600 dark:text-gray-400',
  bg: 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700',
}

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false)
  const config = toolConfig[toolCall.name] ?? defaultConfig

  return (
    <div className={`rounded-lg border text-xs mb-1.5 ${config.bg}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className={`flex items-center gap-2 w-full px-3 py-1.5 ${config.color} font-medium`}
      >
        <span>{config.icon}</span>
        <span className="font-mono">{toolCall.name}</span>
        {toolCall.result ? (
          <span className="text-green-500 ml-auto text-[10px]">✓ done</span>
        ) : (
          <span className="ml-auto animate-pulse-slow text-[10px]">running...</span>
        )}
        <ChevronDown
          size={12}
          className={`transition-transform ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      {expanded && (
        <div className="px-3 pb-2 space-y-1.5">
          <div>
            <span className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-500">
              Args
            </span>
            <pre className="mt-0.5 p-2 rounded bg-white/50 dark:bg-black/20 font-mono text-[11px] overflow-x-auto max-h-32 overflow-y-auto">
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </div>
          {toolCall.result && (
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-500">
                Result
              </span>
              <pre className="mt-0.5 p-2 rounded bg-white/50 dark:bg-black/20 font-mono text-[11px] overflow-x-auto max-h-40 overflow-y-auto">
                {(() => {
                  try {
                    return JSON.stringify(JSON.parse(toolCall.result), null, 2)
                  } catch {
                    return toolCall.result
                  }
                })()}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
