import { useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react'
import { uploadNote, fetchUploadStatus } from '../../lib/api'
import { useChatStore } from '../../store/chatStore'

interface NotesUploadProps {
  sessionId: string
  onClose: () => void
}

export default function NotesUpload({ sessionId, onClose }: NotesUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [stage, setStage] = useState('')
  const [stageMessage, setStageMessage] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [resultInfo, setResultInfo] = useState<{ topics: number; chunks: number } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval>>()

  const updateSessionNotes = useChatStore((s) => s.updateSessionNotes)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile?.type === 'application/pdf') {
      setFile(droppedFile)
      setError('')
    } else {
      setError('Please drop a PDF file.')
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected?.type === 'application/pdf') {
      setFile(selected)
      setError('')
    } else {
      setError('Please select a PDF file.')
    }
  }

  const startPolling = (taskId: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const status = await fetchUploadStatus(taskId)
        setProgress(status.progress)
        setStage(status.stage)
        setStageMessage(status.message)

        if (status.status === 'done') {
          if (pollRef.current) clearInterval(pollRef.current)
          setDone(true)
          setUploading(false)
          if (status.result) {
            setResultInfo({
              topics: status.result.topic_count,
              chunks: status.result.chunk_count,
            })
            // Update store
            updateSessionNotes(sessionId, true, {
              filename: status.result.filename,
              topic_count: status.result.topic_count,
              chunk_count: status.result.chunk_count,
              created_at: new Date().toISOString(),
            })
          }
        } else if (status.status === 'error') {
          if (pollRef.current) clearInterval(pollRef.current)
          setError(status.message)
          setUploading(false)
        }
      } catch {
        // Polling error is non-critical
      }
    }, 1000)
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError('')
    setProgress(5)
    setStage('extracting')
    setStageMessage('Starting upload...')

    try {
      const { task_id } = await uploadNote(sessionId, file)
      startPolling(task_id)
    } catch (err) {
      if (pollRef.current) clearInterval(pollRef.current)
      setError(err instanceof Error ? err.message : 'Upload failed')
      setUploading(false)
    }
  }

  const stageColors: Record<string, string> = {
    extracting: 'bg-blue-500',
    embedding: 'bg-purple-500',
    indexing: 'bg-orange-500',
    done: 'bg-green-500',
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        onClick={(e) => {
          if (e.target === e.currentTarget && !uploading) onClose()
        }}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden border border-gray-200 dark:border-gray-700"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-semibold text-gray-800 dark:text-gray-200">
              Upload PDF Notes
            </h3>
            {!uploading && (
              <button
                onClick={onClose}
                className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                aria-label="Close"
              >
                <X size={18} className="text-gray-500" />
              </button>
            )}
          </div>

          <div className="p-5">
            {!uploading && !done ? (
              <>
                {/* Drop zone */}
                <div
                  onDragOver={(e) => {
                    e.preventDefault()
                    setDragOver(true)
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`
                    border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
                    ${
                      dragOver
                        ? 'border-accent-500 bg-accent-50 dark:bg-accent-900/10'
                        : file
                          ? 'border-green-400 bg-green-50 dark:bg-green-900/10'
                          : 'border-gray-300 dark:border-gray-600 hover:border-accent-400'
                    }
                  `}
                >
                  {file ? (
                    <div className="flex flex-col items-center gap-2">
                      <FileText size={32} className="text-green-500" />
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024 / 1024).toFixed(1)} MB
                      </p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <Upload size={32} className="text-gray-400" />
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Drop a PDF here or click to browse
                      </p>
                      <p className="text-xs text-gray-400">.pdf files only</p>
                    </div>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                />

                {error && (
                  <div className="mt-3 flex items-center gap-2 text-sm text-red-500">
                    <AlertCircle size={14} />
                    {error}
                  </div>
                )}

                <button
                  onClick={handleUpload}
                  disabled={!file}
                  className="mt-4 w-full py-2.5 rounded-xl bg-accent-600 hover:bg-accent-700 text-white text-sm font-medium
                             transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Upload & Process
                </button>
              </>
            ) : done ? (
              /* Success state */
              <div className="text-center py-4">
                <CheckCircle size={48} className="text-green-500 mx-auto mb-3" />
                <h4 className="text-base font-semibold text-gray-800 dark:text-gray-200 mb-1">
                  Notes Processed!
                </h4>
                {resultInfo && (
                  <p className="text-sm text-gray-500 mb-4">
                    {resultInfo.topics} topics · {resultInfo.chunks} chunks indexed
                  </p>
                )}
                <button
                  onClick={onClose}
                  className="px-6 py-2 rounded-xl bg-accent-600 hover:bg-accent-700 text-white text-sm font-medium transition-colors"
                >
                  Start Chatting
                </button>
              </div>
            ) : (
              /* Progress state */
              <div className="py-4">
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {stageMessage}
                    </span>
                    <span className="text-xs text-gray-500">{Math.round(progress)}%</span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <motion.div
                      className={`h-full rounded-full ${stageColors[stage] ?? 'bg-accent-500'}`}
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                </div>

                {/* Stage indicators */}
                <div className="space-y-2 text-xs">
                  {[
                    { key: 'extracting', label: 'Extracting with Gemini...' },
                    { key: 'embedding', label: 'Building embeddings...' },
                    { key: 'indexing', label: 'Indexing to ChromaDB...' },
                  ].map((s) => {
                    const isActive = stage === s.key
                    const isPast =
                      ['extracting', 'embedding', 'indexing', 'done'].indexOf(stage) >
                      ['extracting', 'embedding', 'indexing', 'done'].indexOf(s.key)
                    return (
                      <div
                        key={s.key}
                        className={`flex items-center gap-2 ${
                          isPast
                            ? 'text-green-500'
                            : isActive
                              ? 'text-accent-500 font-medium'
                              : 'text-gray-400'
                        }`}
                      >
                        {isPast ? (
                          <CheckCircle size={12} />
                        ) : isActive ? (
                          <div className="w-3 h-3 rounded-full border-2 border-accent-500 border-t-transparent animate-spin" />
                        ) : (
                          <div className="w-3 h-3 rounded-full border border-gray-300 dark:border-gray-600" />
                        )}
                        {s.label}
                      </div>
                    )
                  })}
                </div>

                {error && (
                  <div className="mt-3 flex items-center gap-2 text-sm text-red-500">
                    <AlertCircle size={14} />
                    {error}
                  </div>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
