import { memo, useState } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { Copy, Check, User, Bot } from 'lucide-react'
import type { Message } from '../../types'
import ThinkingBubble from './ThinkingBubble'
import ToolCallCard from './ToolCallCard'
import DiagramRenderer from './DiagramRenderer'

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
}

function CodeBlock({ children, className }: { children: string; className?: string }) {
  const [copied, setCopied] = useState(false)
  const language = className?.replace('language-', '') || ''

  const handleCopy = async () => {
    await navigator.clipboard.writeText(children)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group my-2 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
      {language && (
        <div className="flex items-center justify-between px-3 py-1 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <span className="text-[10px] font-mono text-gray-500 uppercase">{language}</span>
          <button
            onClick={handleCopy}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label="Copy code"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
          </button>
        </div>
      )}
      <pre className="p-3 overflow-x-auto bg-gray-50 dark:bg-gray-900 text-sm">
        <code className={className}>{children}</code>
      </pre>
      {!language && (
        <button
          onClick={handleCopy}
          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity
                     p-1 rounded bg-gray-200 dark:bg-gray-700 text-gray-500"
          aria-label="Copy code"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
        </button>
      )}
    </div>
  )
}

export default memo(function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {/* Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-500/10 flex items-center justify-center mt-1">
          <Bot size={16} className="text-accent-500" />
        </div>
      )}

      <div className={`max-w-[75%] ${isUser ? 'order-first' : ''}`}>
        {/* Thinking bubble */}
        {message.thinking && (
          <ThinkingBubble content={message.thinking} />
        )}

        {/* Tool calls */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mb-2 space-y-1">
            {message.tool_calls.map((tc) => (
              <ToolCallCard key={tc.id} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Message bubble */}
        <div
          className={`
            rounded-2xl px-4 py-2.5 text-sm leading-relaxed
            ${
              isUser
                ? 'bg-accent-600 text-white rounded-br-md'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-bl-md text-gray-800 dark:text-gray-200'
            }
          `}
        >
          {/* Image attachments */}
          {message.attachments?.map((att) => (
            <div key={att.file_id} className="mb-2">
              <img
                src={`data:image/jpeg;base64,${att.base64}`}
                alt={att.filename}
                className="max-w-full max-h-60 rounded-lg"
              />
            </div>
          ))}

          {/* Content */}
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none prose-pre:p-0 prose-pre:bg-transparent prose-pre:border-0">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  code({ className, children, ...props }) {
                    const isInline = !className
                    if (isInline) {
                      return (
                        <code
                          className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-xs font-mono"
                          {...props}
                        >
                          {children}
                        </code>
                      )
                    }
                    return (
                      <CodeBlock className={className}>
                        {String(children).replace(/\n$/, '')}
                      </CodeBlock>
                    )
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {/* Streaming cursor */}
          {isStreaming && !isUser && (
            <span className="inline-block w-1.5 h-4 bg-accent-500 ml-0.5 animate-pulse rounded-sm" />
          )}
        </div>

        {/* Diagrams */}
        {message.diagrams?.map((d) => (
          <DiagramRenderer key={d.id} id={d.id} mermaidCode={d.mermaid_code} />
        ))}

        {/* Timestamp */}
        <div
          className={`text-[10px] text-gray-400 mt-1 ${isUser ? 'text-right' : 'text-left'}`}
        >
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-600 flex items-center justify-center mt-1">
          <User size={16} className="text-white" />
        </div>
      )}
    </motion.div>
  )
})
