import { useEffect, useState, useId } from 'react'
import { Copy, Check, RefreshCw } from 'lucide-react'
import { renderDiagram } from '../../lib/mermaid'

interface DiagramRendererProps {
  mermaidCode: string
  id: string
}

export default function DiagramRenderer({ mermaidCode, id }: DiagramRendererProps) {
  const [svg, setSvg] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [copied, setCopied] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const reactId = useId()

  useEffect(() => {
    let cancelled = false

    async function render() {
      try {
        const renderedSvg = await renderDiagram(
          `${id}-${reactId.replace(/:/g, '')}`,
          mermaidCode
        )
        if (!cancelled) {
          setSvg(renderedSvg)
          setError('')
        }
      } catch (err) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : String(err)
          setError(msg)
          setSvg('')
        }
      }
    }

    render()
    return () => {
      cancelled = true
    }
  }, [mermaidCode, id, reactId, retryCount])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(mermaidCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRetry = () => {
    setError('')
    setSvg('')
    setRetryCount((c) => c + 1)
  }

  return (
    <div className="my-3 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
        <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
          📊 Diagram
        </span>
        <div className="flex items-center gap-2">
          {error && (
            <button
              onClick={handleRetry}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              aria-label="Retry render"
            >
              <RefreshCw size={12} />
              Retry
            </button>
          )}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
            aria-label="Copy mermaid code"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            {copied ? 'Copied' : 'Copy Code'}
          </button>
        </div>
      </div>

      {svg ? (
        <div
          className="p-4 bg-white dark:bg-gray-900 overflow-x-auto flex justify-center [&>svg]:max-w-full"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : error ? (
        <div className="p-4">
          <p className="text-xs text-amber-600 dark:text-amber-400 mb-2">
            ⚠️ Could not render diagram — showing raw code
          </p>
          <pre className="p-3 rounded-lg bg-gray-100 dark:bg-gray-800 text-xs font-mono overflow-x-auto whitespace-pre-wrap text-gray-700 dark:text-gray-300">
            {mermaidCode}
          </pre>
        </div>
      ) : (
        <div className="p-8 flex justify-center">
          <div className="animate-pulse text-sm text-gray-400">
            Rendering diagram...
          </div>
        </div>
      )}
    </div>
  )
}
