// Agent types
export interface Agent {
  id: string
  displayName: string | null
  role: string | null
  capabilities: string[]
  registeredAt: string
  lastSeenAt: string
  status: 'online' | 'idle' | 'offline'
  sessionMeta?: {
    model?: string
    client?: string
  }
}

// Task types - aligned with schema.md TaskStatus enum
export type TaskStatus = 'todo' | 'ready' | 'blocked' | 'done' | 'verified' | 'deleted'

export interface Task {
  id: string
  title: string
  description: string
  acceptanceCriteria: string[]
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
  taskId: string // Required in Lodestar 0.9.0+
  body: string
  readBy: string[] // Array of agent IDs who have read this message
  subject?: string | null
  severity?: MessageSeverity | null
}

// Event types - aligned with schema.md event_type values
export type EventType =
  | 'agent.join'
  | 'agent.heartbeat'
  | 'agent.leave'
  | 'task.claim'
  | 'task.renew'
  | 'task.release'
  | 'task.done'
  | 'task.verified'
  | 'lease.expired'
  | 'message.sent'
  | 'message.read'

export interface LodestarEvent {
  id: number
  createdAt: string
  type: EventType | string  // Allow string for forward compatibility
  actorAgentId?: string | null
  taskId?: string | null
  targetAgentId?: string | null
  correlationId?: string | null
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

