import { useCallback, useEffect, useRef } from 'react'
import { useChatStore } from '../store/chatStore'
import type { WSEvent, ChatSettings, DiagramData, ToolCall } from '../types'

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export function useWebSocket(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  const isConnectedRef = useRef(false)

  const {
    setIsStreaming,
    appendThinking,
    appendContent,
    addToolCall,
    updateToolCallResult,
    addDiagram,
    resetStreamState,
    addMessage,
    updateSessionTitle,
  } = useChatStore()

  const connect = useCallback(() => {
    if (!sessionId) return

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const ws = new WebSocket(`${WS_BASE}/ws/chat/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => {
      isConnectedRef.current = true
    }

    ws.onmessage = (event) => {
      try {
        const data: WSEvent = JSON.parse(event.data)
        handleEvent(data)
      } catch {
        // ignore non-JSON messages
      }
    }

    ws.onclose = () => {
      isConnectedRef.current = false
      // Auto-reconnect after 3s if session is still active
      const currentSessionId = useChatStore.getState().activeSessionId
      if (currentSessionId === sessionId) {
        reconnectTimer.current = setTimeout(() => {
          connect()
        }, 3000)
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [sessionId])

  const handleEvent = useCallback(
    (event: WSEvent) => {
      if (!sessionId) return

      switch (event.type) {
        case 'ready':
          break

        case 'thinking':
          if (event.content) {
            appendThinking(event.content)
          }
          break

        case 'content':
          if (event.content) {
            appendContent(event.content)
          }
          break

        case 'tool_call':
          if (event.tool) {
            const tc: ToolCall = {
              id: `tc_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
              name: event.tool,
              args: event.args ?? {},
            }
            addToolCall(tc)
          }
          break

        case 'tool_result':
          if (event.tool) {
            // Update the last tool call with this name
            const store = useChatStore.getState()
            const matching = store.currentToolCalls.filter(
              (tc) => tc.name === event.tool && !tc.result
            )
            if (matching.length > 0) {
              updateToolCallResult(
                matching[matching.length - 1].id,
                event.result ?? ''
              )
            }
          }
          break

        case 'diagram':
          if (event.mermaid_code) {
            const diagram: DiagramData = {
              id: `diag_${Date.now()}`,
              mermaid_code: event.mermaid_code,
            }
            addDiagram(diagram)
          }
          break

        case 'done': {
          const store = useChatStore.getState()
          // Build the final assistant message
          const assistantMsg = {
            id: `msg_${Date.now()}`,
            role: 'assistant' as const,
            content: store.currentContent,
            timestamp: new Date().toISOString(),
            thinking: store.currentThinking || undefined,
            tool_calls:
              store.currentToolCalls.length > 0
                ? store.currentToolCalls
                : undefined,
            diagrams:
              store.currentDiagrams.length > 0
                ? store.currentDiagrams
                : undefined,
          }
          addMessage(sessionId, assistantMsg)
          setIsStreaming(false)
          resetStreamState()

          // Update title if returned
          if (event.title) {
            updateSessionTitle(sessionId, event.title)
          }
          break
        }

        case 'error':
          setIsStreaming(false)
          resetStreamState()
          // Add error as assistant message
          addMessage(sessionId, {
            id: `msg_err_${Date.now()}`,
            role: 'assistant',
            content: `⚠️ Error: ${event.message ?? 'Unknown error'}`,
            timestamp: new Date().toISOString(),
          })
          break
      }
    },
    [sessionId]
  )

  // Connect when session changes
  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  const sendMessage = useCallback(
    (
      message: string,
      imageBase64: string | null,
      settings: ChatSettings
    ) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        return false
      }

      const payload: Record<string, unknown> = {
        message,
        enable_thinking: settings.enable_thinking,
        enable_verbose: settings.enable_verbose,
        stream: settings.stream,
        enable_web_search: settings.enable_web_search,
      }

      if (imageBase64) {
        payload.image_base64 = imageBase64
      }

      wsRef.current.send(JSON.stringify(payload))
      return true
    },
    []
  )

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  return { sendMessage, disconnect, isConnected: isConnectedRef }
}
