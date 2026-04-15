import { useState, useRef, useCallback, useEffect } from 'react'
import { ArrowUp, Image, Square, X } from 'lucide-react'
import { uploadImage } from '../../lib/api'

interface MessageInputProps {
  onSend: (message: string, imageBase64: string | null) => void
  isStreaming: boolean
  onStop?: () => void
}

export default function MessageInput({ onSend, isStreaming, onStop }: MessageInputProps) {
  const [text, setText] = useState('')
  const [imagePreview, setImagePreview] = useState<{
    base64: string
    filename: string
  } | null>(null)
  const [uploading, setUploading] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [text])

  const handleSend = useCallback(() => {
    const trimmed = text.trim()
    if (!trimmed && !imagePreview) return
    if (isStreaming) return

    onSend(trimmed, imagePreview?.base64 ?? null)
    setText('')
    setImagePreview(null)

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [text, imagePreview, isStreaming, onSend])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const validTypes = ['image/jpeg', 'image/png', 'image/webp']
    if (!validTypes.includes(file.type)) {
      alert('Please select a JPG, PNG, or WebP image.')
      return
    }

    setUploading(true)
    try {
      const result = await uploadImage(file)
      setImagePreview({ base64: result.base64, filename: file.name })
    } catch (err) {
      console.error('Image upload failed:', err)
      // Fallback: read locally
      const reader = new FileReader()
      reader.onload = () => {
        const base64 = (reader.result as string).split(',')[1]
        setImagePreview({ base64, filename: file.name })
      }
      reader.readAsDataURL(file)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      {/* Image preview */}
      {imagePreview && (
        <div className="mb-3 flex items-center gap-2">
          <div className="relative group">
            <img
              src={`data:image/jpeg;base64,${imagePreview.base64}`}
              alt={imagePreview.filename}
              className="h-16 w-16 object-cover rounded-lg border border-gray-200 dark:border-gray-700"
            />
            <button
              onClick={() => setImagePreview(null)}
              className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-500 text-white 
                         flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              aria-label="Remove image"
            >
              <X size={10} />
            </button>
          </div>
          <span className="text-xs text-gray-500 truncate max-w-[200px]">
            {imagePreview.filename}
          </span>
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* Image attach button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading || isStreaming}
          className="flex-shrink-0 p-2 rounded-xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
                     hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
          aria-label="Attach image"
        >
          <Image size={20} />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleImageSelect}
          className="hidden"
        />

        {/* Textarea */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question..."
            rows={1}
            disabled={isStreaming}
            className="w-full resize-none rounded-2xl px-4 py-2.5 text-sm
                       bg-gray-100 dark:bg-gray-800 
                       border border-gray-200 dark:border-gray-700
                       focus:outline-none focus:ring-2 focus:ring-accent-500/50 focus:border-accent-500
                       placeholder-gray-400 dark:placeholder-gray-500
                       text-gray-800 dark:text-gray-200
                       disabled:opacity-50 transition-colors"
          />
        </div>

        {/* Send / Stop button */}
        {isStreaming ? (
          <button
            onClick={onStop}
            className="flex-shrink-0 p-2.5 rounded-xl bg-red-500 hover:bg-red-600 text-white transition-colors"
            aria-label="Stop generation"
          >
            <Square size={16} />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={(!text.trim() && !imagePreview) || uploading}
            className="flex-shrink-0 p-2.5 rounded-xl bg-accent-600 hover:bg-accent-700 text-white 
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Send message"
          >
            <ArrowUp size={16} />
          </button>
        )}
      </div>
    </div>
  )
}
