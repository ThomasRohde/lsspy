import { create } from 'zustand'
import type { Agent, Task, Lease, Message, LodestarEvent, RepoStatus } from '../types'

interface DataState {
  // Data collections
  agents: Map<string, Agent>
  tasks: Map<string, Task>
  leases: Map<string, Lease>
  messages: Message[]
  events: LodestarEvent[]
  repoStatus: RepoStatus | null

  // Connection state
  isConnected: boolean
  lastSyncAt: string | null
  connectionError: string | null
  reconnectAttempts: number

  // Agent actions
  setAgents: (agents: Agent[]) => void
  updateAgent: (agent: Agent) => void
  removeAgent: (agentId: string) => void

  // Task actions
  setTasks: (tasks: Task[]) => void
  updateTask: (task: Task) => void
  removeTask: (taskId: string) => void

  // Lease actions
  setLeases: (leases: Lease[]) => void
  updateLease: (lease: Lease) => void
  removeLease: (leaseId: string) => void
  removeLeaseByTask: (taskId: string) => void

  // Message actions
  setMessages: (messages: Message[]) => void
  addMessage: (message: Message) => void
  markMessageRead: (messageId: string) => void

  // Event actions
  setEvents: (events: LodestarEvent[]) => void
  addEvent: (event: LodestarEvent) => void
  clearEvents: () => void

  // Status actions
  setRepoStatus: (status: RepoStatus) => void

  // Connection actions
  setConnected: (connected: boolean) => void
  updateLastSync: () => void
  setConnectionError: (error: string | null) => void
  setReconnectAttempts: (attempts: number) => void

  // Bulk operations
  reset: () => void
}

const initialState = {
  agents: new Map<string, Agent>(),
  tasks: new Map<string, Task>(),
  leases: new Map<string, Lease>(),
  messages: [] as Message[],
  events: [] as LodestarEvent[],
  repoStatus: null as RepoStatus | null,
  isConnected: false,
  lastSyncAt: null as string | null,
  connectionError: null as string | null,
  reconnectAttempts: 0,
}

export const useDataStore = create<DataState>((set) => ({
  ...initialState,

  // Agent actions
  setAgents: (agents) =>
    set({
      agents: new Map(agents.map((a) => [a.id, a])),
    }),

  updateAgent: (agent) =>
    set((state) => {
      const newAgents = new Map(state.agents)
      newAgents.set(agent.id, agent)
      return { agents: newAgents }
    }),

  removeAgent: (agentId) =>
    set((state) => {
      const newAgents = new Map(state.agents)
      newAgents.delete(agentId)
      return { agents: newAgents }
    }),

  // Task actions
  setTasks: (tasks) =>
    set({
      tasks: new Map(tasks.map((t) => [t.id, t])),
    }),

  updateTask: (task) =>
    set((state) => {
      const newTasks = new Map(state.tasks)
      newTasks.set(task.id, task)
      return { tasks: newTasks }
    }),

  removeTask: (taskId) =>
    set((state) => {
      const newTasks = new Map(state.tasks)
      newTasks.delete(taskId)
      return { tasks: newTasks }
    }),

  // Lease actions
  setLeases: (leases) =>
    set({
      leases: new Map(leases.map((l) => [l.leaseId, l])),
    }),

  updateLease: (lease) =>
    set((state) => {
      const newLeases = new Map(state.leases)
      newLeases.set(lease.leaseId, lease)
      return { leases: newLeases }
    }),

  removeLease: (leaseId) =>
    set((state) => {
      const newLeases = new Map(state.leases)
      newLeases.delete(leaseId)
      return { leases: newLeases }
    }),

  removeLeaseByTask: (taskId) =>
    set((state) => {
      const newLeases = new Map(state.leases)
      for (const [leaseId, lease] of newLeases) {
        if (lease.taskId === taskId) {
          newLeases.delete(leaseId)
        }
      }
      return { leases: newLeases }
    }),

  // Message actions
  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  markMessageRead: (messageId) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, readAt: new Date().toISOString() } : m
      ),
    })),

  // Event actions
  setEvents: (events) => set({ events }),

  addEvent: (event) =>
    set((state) => ({
      events: [...state.events, event].slice(-1000), // Keep last 1000 events
    })),

  clearEvents: () => set({ events: [] }),

  // Status actions
  setRepoStatus: (status) => set({ repoStatus: status }),

  // Connection actions
  setConnected: (connected) => set({ isConnected: connected }),

  updateLastSync: () => set({ lastSyncAt: new Date().toISOString() }),

  setConnectionError: (error) => set({ connectionError: error }),

  setReconnectAttempts: (attempts) => set({ reconnectAttempts: attempts }),

  // Bulk operations
  reset: () => set(initialState),
}))

// Selector hooks for common queries
export const useAgentsList = () =>
  useDataStore((state) => Array.from(state.agents.values()))

export const useTasksList = () =>
  useDataStore((state) => Array.from(state.tasks.values()))

export const useLeasesList = () =>
  useDataStore((state) => Array.from(state.leases.values()))

export const useTaskById = (taskId: string) =>
  useDataStore((state) => state.tasks.get(taskId))

export const useAgentById = (agentId: string) =>
  useDataStore((state) => state.agents.get(agentId))

export const useLeaseByTask = (taskId: string) =>
  useDataStore((state) => {
    for (const lease of state.leases.values()) {
      if (lease.taskId === taskId) return lease
    }
    return undefined
  })

export const useUnreadMessages = () =>
  useDataStore((state) => state.messages.filter((m) => !m.readAt))

export const useRecentEvents = (limit = 50) =>
  useDataStore((state) => state.events.slice(-limit))
