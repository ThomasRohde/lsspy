import { useEffect, useRef, useCallback, useState } from 'react'
import { useDataStore } from '../stores'
import type { Agent, Task, Lease, Message, LodestarEvent } from '../types'

// WebSocket message types from backend
interface WsUpdateMessage {
  type: 'update'
  scope: 'agents' | 'tasks' | 'leases' | 'messages' | 'events'
  data: unknown
  timestamp: string
}

interface WsConnectedMessage {
  type: 'connected'
  client_id: string
  subscriptions: string[]
  timestamp: string
}

interface WsSubscribedMessage {
  type: 'subscribed' | 'unsubscribed'
  subscriptions: string[]
  timestamp: string
}

interface WsErrorMessage {
  type: 'error'
  error: string
  timestamp: string
}

interface WsPongMessage {
  type: 'pong'
  timestamp: string
}

type WsIncomingMessage = WsUpdateMessage | WsConnectedMessage | WsSubscribedMessage | WsErrorMessage | WsPongMessage

// Legacy message types (for backward compatibility)
interface WsMessage {
  type: string
  payload: unknown
}

interface AgentsPayload {
  agents: Agent[]
}

interface TasksPayload {
  tasks: Task[]
}

interface LeasesPayload {
  leases: Lease[]
}

interface MessagesPayload {
  messages: Message[]
}

interface EventsPayload {
  events: LodestarEvent[]
}

interface StatusPayload {
  totalTasks: number
  tasksByStatus: Record<string, number>
  activeAgents: number
  totalAgents: number
  suggestedActions: string[]
}

interface UseWebSocketOptions {
  url?: string
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<number | null>(null)

  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected')
  const [error, setError] = useState<string | null>(null)

  // Get store actions via getState() to avoid subscribing to store changes
  // This prevents React error #301 (setState during render)
  const getStoreActions = useCallback(() => useDataStore.getState(), [])

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data) as WsIncomingMessage | WsMessage

      // Validate message has required fields
      if (!message || typeof message.type !== 'string') {
        console.warn('Received malformed WebSocket message: missing type', message)
        return
      }

      const store = getStoreActions()

      switch (message.type) {
        // New backend message format: update messages
        case 'update': {
          const updateMsg = message as WsUpdateMessage
          store.updateLastSync()

          // Validate data is an array
          const data = updateMsg.data
          if (!Array.isArray(data)) {
            console.warn(`Received non-array data for scope ${updateMsg.scope}:`, data)
            break
          }

          switch (updateMsg.scope) {
            case 'agents':
              store.setAgents(data as Agent[])
              break
            case 'tasks':
              store.setTasks(data as Task[])
              break
            case 'leases':
              store.setLeases(data as Lease[])
              break
            case 'messages':
              store.setMessages(data as Message[])
              break
            case 'events':
              store.setEvents(data as LodestarEvent[])
              break
            default:
              console.warn(`Unknown update scope: ${updateMsg.scope}`)
          }
          break
        }

        // Connection acknowledgment
        case 'connected':
          console.log('WebSocket connected with client ID:', (message as WsConnectedMessage).client_id)
          break

        // Subscription acknowledgment
        case 'subscribed':
        case 'unsubscribed':
          console.log('Subscription updated:', (message as WsSubscribedMessage).subscriptions)
          break

        // Pong response (for keepalive)
        case 'pong':
          break

        // Error message
        case 'error':
          console.error('WebSocket error from server:', (message as WsErrorMessage).error)
          break

        // Legacy message format support (backward compatibility)
        case 'agents':
          store.setAgents((message as WsMessage).payload as Agent[] | AgentsPayload['agents'])
          break

        case 'tasks':
          store.setTasks((message as WsMessage).payload as Task[] | TasksPayload['tasks'])
          break

        case 'leases':
          store.setLeases((message as WsMessage).payload as Lease[] | LeasesPayload['leases'])
          break

        case 'messages':
          store.setMessages((message as WsMessage).payload as Message[] | MessagesPayload['messages'])
          break

        case 'events':
          store.setEvents((message as WsMessage).payload as LodestarEvent[] | EventsPayload['events'])
          break

        case 'status':
          store.setRepoStatus((message as WsMessage).payload as StatusPayload)
          break

        // Incremental update messages (legacy)
        case 'agent.joined':
        case 'agent.updated':
          store.updateAgent((message as WsMessage).payload as Agent)
          break

        case 'agent.left':
          store.removeAgent(((message as WsMessage).payload as { agentId: string }).agentId)
          break

        case 'task.updated':
          store.updateTask((message as WsMessage).payload as Task)
          break

        case 'lease.created':
        case 'lease.renewed':
          store.updateLease((message as WsMessage).payload as Lease)
          break

        case 'lease.expired':
        case 'lease.released':
          store.removeLease(((message as WsMessage).payload as { leaseId: string }).leaseId)
          break

        case 'message.sent':
          store.addMessage((message as WsMessage).payload as Message)
          break

        case 'event':
          store.addEvent((message as WsMessage).payload as LodestarEvent)
          break

        case 'sync':
          // Full sync response
          store.updateLastSync()
          break

        default:
          console.warn('Unknown WebSocket message type:', message.type)
      }
    } catch (err) {
      console.error('Failed to parse WebSocket message:', err)
    }
  }, [getStoreActions])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    setConnectionState('connecting')
    setError(null)

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        const store = getStoreActions()
        setConnectionState('connected')
        store.setConnected(true)
        reconnectAttemptsRef.current = 0
        setError(null)
        store.setConnectionError(null)
        store.setReconnectAttempts(0)

        // Subscribe to all data scopes for real-time updates
        ws.send(JSON.stringify({ type: 'subscribe', scopes: ['all'] }))
      }

      ws.onmessage = handleMessage

      ws.onclose = (event) => {
        const store = getStoreActions()
        setConnectionState('disconnected')
        store.setConnected(false)
        wsRef.current = null

        // Attempt to reconnect unless explicitly closed
        if (!event.wasClean && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++
          const errorMsg = `Connection lost. Reconnecting (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`
          setError(errorMsg)
          store.setConnectionError(errorMsg)
          store.setReconnectAttempts(reconnectAttemptsRef.current)

          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect()
          }, reconnectInterval)
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          const errorMsg = 'Unable to connect to server. Please check that the LSSPY server is running and refresh the page.'
          setError(errorMsg)
          store.setConnectionError(errorMsg)
        }
      }

      ws.onerror = () => {
        const store = getStoreActions()
        const errorMsg = 'WebSocket connection error. Server may be unavailable.'
        setError(errorMsg)
        store.setConnectionError(errorMsg)
      }
    } catch (err) {
      const store = getStoreActions()
      setConnectionState('disconnected')
      const errorMsg = 'Failed to create WebSocket connection. Check server configuration.'
      setError(errorMsg)
      store.setConnectionError(errorMsg)
      console.error('WebSocket connection error:', err)
    }
  }, [url, handleMessage, reconnectInterval, maxReconnectAttempts, getStoreActions])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }

    const store = getStoreActions()
    setConnectionState('disconnected')
    store.setConnected(false)
  }, [getStoreActions])

  const send = useCallback((message: WsMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  const requestSync = useCallback(() => {
    // Re-subscribe to trigger fresh data delivery
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', scopes: ['all'] }))
    }
  }, [])

  // Auto-connect on mount
  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    connectionState,
    error,
    connect,
    disconnect,
    send,
    requestSync,
  }
}
