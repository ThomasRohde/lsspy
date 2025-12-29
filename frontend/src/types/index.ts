// Agent types
export interface Agent {
  id: string
  displayName: string | null
  capabilities: string[]
  registeredAt: string
  lastSeenAt: string
  status: 'online' | 'idle' | 'offline'
  sessionMeta?: {
    model?: string
    client?: string
  }
}

// Task types
export type TaskStatus = 'ready' | 'done' | 'verified' | 'deleted'

export interface Task {
  id: string
  title: string
  description: string
  status: TaskStatus
  priority: number
  labels: string[]
  locks: string[]
  dependencies: string[]
  dependents: string[]
  createdAt: string
  updatedAt: string
  prdSource?: string | null
}

// Lease types
export interface Lease {
  leaseId: string
  taskId: string
  agentId: string
  expiresAt: string
  ttlSeconds: number
  createdAt: string
}

// Message types
export type MessageSeverity = 'info' | 'warning' | 'handoff' | 'blocker'

export interface Message {
  id: string
  createdAt: string
  from: string
  to: string
  body: string
  taskId?: string | null
  subject?: string | null
  severity?: MessageSeverity | null
  readAt?: string | null
}

// Event types
export type EventType =
  | 'agent.joined'
  | 'agent.left'
  | 'agent.heartbeat'
  | 'task.claimed'
  | 'task.released'
  | 'task.done'
  | 'task.verified'
  | 'message.sent'

export interface LodestarEvent {
  id: number
  createdAt: string
  type: EventType
  actorAgentId?: string | null
  taskId?: string | null
  targetAgentId?: string | null
  payload?: Record<string, unknown>
}

// Repository status
export interface RepoStatus {
  totalTasks: number
  tasksByStatus: Record<TaskStatus, number>
  activeAgents: number
  totalAgents: number
  suggestedActions: string[]
}
