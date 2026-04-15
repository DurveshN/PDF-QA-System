import { useEffect, useState, useRef } from 'react'
import { Copy, Check } from 'lucide-react'
import { renderDiagram } from '../../lib/mermaid'

interface DiagramRendererProps {
  mermaidCode: string
  id: string
}

export default function DiagramRenderer({ mermaidCode, id }: DiagramRendererProps) {
  const [svg, setSvg] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [copied, setCopied] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false

    async function render() {
      try {
        const renderedSvg = await renderDiagram(`mermaid-${id}`, mermaidCode)
        if (!cancelled) {
          setSvg(renderedSvg)
          setError('')
        }
      } catch (err) {
        if (!cancelled) {
          setError(String(err))
        }
      }
    }

    render()
    return () => {
      cancelled = true
    }
  }, [mermaidCode, id])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(mermaidCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-3 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
        <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
          📊 Diagram
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
          aria-label="Copy mermaid code"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy Code'}
        </button>
      </div>

      {svg ? (
        <div
          ref={containerRef}
          className="p-4 bg-white dark:bg-gray-900 overflow-x-auto flex justify-center"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : error ? (
        <div className="p-4">
          <p className="text-xs text-red-500 mb-2">Failed to render diagram</p>
          <pre className="p-3 rounded-lg bg-gray-100 dark:bg-gray-800 text-xs font-mono overflow-x-auto">
            {mermaidCode}
          </pre>
        </div>
      ) : (
        <div className="p-8 flex justify-center">
          <div className="animate-pulse text-sm text-gray-400">Rendering diagram...</div>
        </div>
      )}
    </div>
  )
}
