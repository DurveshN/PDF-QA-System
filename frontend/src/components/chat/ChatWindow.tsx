import { useEffect, useRef } from 'react'
import { FileText, Search, BookOpen, Lightbulb } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'
import MessageBubble from './MessageBubble'
import ThinkingBubble from './ThinkingBubble'
import ToolCallCard from './ToolCallCard'

interface ChatWindowProps {
  onSuggestedPrompt: (prompt: string) => void
}

const suggestedPrompts = [
  { icon: <Search size={14} />, text: 'Search the web for recent AI news' },
  { icon: <BookOpen size={14} />, text: 'What topics are in my notes?' },
  { icon: <FileText size={14} />, text: 'Summarize the key concepts' },
  { icon: <Lightbulb size={14} />, text: 'Generate a diagram of the main ideas' },
]

export default function ChatWindow({ onSuggestedPrompt }: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const messages = useChatStore((s) => s.getActiveMessages())
  const isStreaming = useChatStore((s) => s.isStreaming)
  const currentThinking = useChatStore((s) => s.currentThinking)
  const currentContent = useChatStore((s) => s.currentContent)
  const currentToolCalls = useChatStore((s) => s.currentToolCalls)
  const currentDiagrams = useChatStore((s) => s.currentDiagrams)

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentContent, currentThinking, currentToolCalls])

  const isEmpty = messages.length === 0 && !isStreaming

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto px-4 py-6 scroll-smooth"
    >
      {isEmpty ? (
        /* Empty state */
        <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
          <div className="w-16 h-16 rounded-2xl bg-accent-500/10 flex items-center justify-center mb-4">
            <FileText size={28} className="text-accent-500" />
          </div>
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
            PDF-QA System
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-8 max-w-md">
            Upload a PDF to ask questions about your notes, or start a conversation with web search.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg w-full">
            {suggestedPrompts.map((prompt) => (
              <button
                key={prompt.text}
                onClick={() => onSuggestedPrompt(prompt.text)}
                className="flex items-center gap-2 px-4 py-3 rounded-xl text-left text-sm
                           bg-gray-50 dark:bg-gray-800/50 
                           border border-gray-200 dark:border-gray-700
                           hover:border-accent-400 dark:hover:border-accent-500
                           hover:bg-accent-50 dark:hover:bg-accent-900/10
                           text-gray-600 dark:text-gray-400
                           transition-all duration-200"
              >
                <span className="text-accent-500">{prompt.icon}</span>
                {prompt.text}
              </button>
            ))}
          </div>
        </div>
      ) : (
        /* Messages */
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {/* Live streaming state */}
          {isStreaming && (
            <div className="flex gap-3 justify-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-500/10 flex items-center justify-center mt-1">
                <div className="w-4 h-4 rounded-full bg-accent-500 animate-pulse-slow" />
              </div>
              <div className="max-w-[75%]">
                {/* Live thinking */}
                {currentThinking && (
                  <ThinkingBubble content={currentThinking} isLive />
                )}

                {/* Live tool calls */}
                {currentToolCalls.length > 0 && (
                  <div className="mb-2 space-y-1">
                    {currentToolCalls.map((tc) => (
                      <ToolCallCard key={tc.id} toolCall={tc} />
                    ))}
                  </div>
                )}

                {/* Live content */}
                {currentContent ? (
                  <div className="rounded-2xl rounded-bl-md px-4 py-2.5 text-sm leading-relaxed bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200">
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdownLive content={currentContent} />
                    </div>
                    <span className="inline-block w-1.5 h-4 bg-accent-500 ml-0.5 animate-pulse rounded-sm" />
                  </div>
                ) : !currentThinking && currentToolCalls.length === 0 ? (
                  /* Typing indicator */
                  <div className="rounded-2xl rounded-bl-md px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}

// Lightweight live markdown renderer (avoids re-parsing on every token)
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function ReactMarkdownLive({ content }: { content: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {content}
    </ReactMarkdown>
  )
}
