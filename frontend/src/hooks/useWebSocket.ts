import { useCallback, useEffect, useRef } from 'react'
import { useChatStore } from '../store/chatStore'
import type { WSEvent, ChatSettings, DiagramData, ToolCall } from '../types'

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export function useWebSocket(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  const sessionIdRef = useRef(sessionId)

  // Keep sessionId ref in sync without causing reconnects
  sessionIdRef.current = sessionId

  const handleEvent = useCallback((event: WSEvent) => {
    const sid = sessionIdRef.current
    if (!sid) return

    const store = useChatStore.getState()

    switch (event.type) {
      case 'ready':
        break

      case 'thinking':
        if (event.content) {
          store.appendThinking(event.content)
        }
        break

      case 'content':
        if (event.content) {
          store.appendContent(event.content)
        }
        break

      case 'tool_call':
        if (event.tool) {
          const tc: ToolCall = {
            id: `tc_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
            name: event.tool,
            args: event.args ?? {},
          }
          store.addToolCall(tc)
        }
        break

      case 'tool_result':
        if (event.tool) {
          const matching = store.currentToolCalls.filter(
            (tc) => tc.name === event.tool && !tc.result
          )
          if (matching.length > 0) {
            store.updateToolCallResult(
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
          store.addDiagram(diagram)
        }
        break

      case 'done': {
        // Build the final assistant message from accumulated state
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
        store.addMessage(sid, assistantMsg)
        store.setIsStreaming(false)
        store.resetStreamState()

        // Update title if returned
        if (event.title) {
          store.updateSessionTitle(sid, event.title)
        }
        break
      }

      case 'error':
        store.setIsStreaming(false)
        store.resetStreamState()
        store.addMessage(sid, {
          id: `msg_err_${Date.now()}`,
          role: 'assistant',
          content: `⚠️ Error: ${event.message ?? 'Unknown error'}`,
          timestamp: new Date().toISOString(),
        })
        break
    }
  }, [])

  // Connect/disconnect only when sessionId changes
  useEffect(() => {
    if (!sessionId) return

    // Clear any pending reconnect
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = undefined
    }

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null // prevent reconnect from old socket
      wsRef.current.close()
      wsRef.current = null
    }

    function doConnect() {
      if (sessionIdRef.current !== sessionId) return // stale

      const ws = new WebSocket(`${WS_BASE}/ws/chat/${sessionId}`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log(`[WS] Connected to session ${sessionId?.slice(0, 8)}`)
      }

      ws.onmessage = (event) => {
        try {
          const data: WSEvent = JSON.parse(event.data)
          handleEvent(data)
        } catch {
          // ignore non-JSON
        }
      }

      ws.onclose = () => {
        console.log(`[WS] Disconnected from session ${sessionId?.slice(0, 8)}`)
        // Only reconnect if this session is still active
        if (sessionIdRef.current === sessionId) {
          reconnectTimer.current = setTimeout(doConnect, 3000)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    doConnect()

    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
        reconnectTimer.current = undefined
      }
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [sessionId, handleEvent])

  const sendMessage = useCallback(
    (message: string, imageBase64: string | null, settings: ChatSettings) => {
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
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = undefined
    }
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  return { sendMessage, disconnect }
}
