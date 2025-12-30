import { useState, useMemo } from 'react'
import { useTasksList, useLeasesList, useAgentById, useAgentsList } from '../stores'
import { formatDistanceToNow, differenceInSeconds } from 'date-fns'
import clsx from 'clsx'
import type { Task, Lease } from '../types'

type ColumnStatus = 'todo' | 'ready' | 'in_progress' | 'blocked' | 'done' | 'verified'

interface TaskCardProps {
  task: Task
  lease: Lease | undefined
  onClick: () => void
}

interface TaskDetailsSidebarProps {
  task: Task
  lease: Lease | undefined
  onClose: () => void
}

interface FilterState {
  label: string
  priority: string
  agent: string
}

const COLUMNS: { key: ColumnStatus; label: string; color: string }[] = [
  { key: 'todo', label: 'Todo', color: 'border-gray-500' },
  { key: 'ready', label: 'Ready', color: 'border-yellow-500' },
  { key: 'in_progress', label: 'In Progress', color: 'border-blue-500' },
  { key: 'blocked', label: 'Blocked', color: 'border-red-500' },
  { key: 'done', label: 'Done', color: 'border-green-500' },
  { key: 'verified', label: 'Verified', color: 'border-purple-500' },
]

function LeaseCountdown({ lease }: { lease: Lease }) {
  const expiresAt = new Date(lease.expiresAt)
  const now = new Date()
  const secondsLeft = differenceInSeconds(expiresAt, now)

  if (secondsLeft <= 0) {
    return <span className="text-red-400">Expired</span>
  }

  const minutes = Math.floor(secondsLeft / 60)
  const seconds = secondsLeft % 60

  const colorClass = secondsLeft <= 300
    ? 'text-orange-400'
    : secondsLeft <= 600
      ? 'text-yellow-400'
      : 'text-text-muted'

  return (
    <span className={clsx('font-mono text-xs', colorClass)}>
      {minutes}:{seconds.toString().padStart(2, '0')}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: number }) {
  const colorClass =
    priority <= 3 ? 'bg-red-500/20 text-red-400 border-red-500/50' :
      priority <= 5 ? 'bg-orange-500/20 text-orange-400 border-orange-500/50' :
        priority <= 7 ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50' :
          'bg-gray-500/20 text-text-muted border-gray-500/50'

  return (
    <span className={clsx(
      'px-1.5 py-0.5 text-xs font-medium rounded border',
      colorClass
    )}>
      P{priority}
    </span>
  )
}

function TaskCard({ task, lease, onClick }: TaskCardProps) {
  const claimingAgent = useAgentById(lease?.agentId || '')

  return (
    <div
      className="bg-dark-bg border border-dark-border rounded-lg p-3 cursor-pointer hover:border-text-muted transition-colors"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-mono text-xs text-text-muted">{task.id}</span>
        <PriorityBadge priority={task.priority} />
      </div>
      <h3 className="text-sm font-medium text-text-primary mb-2 line-clamp-2">
        {task.title}
      </h3>
      {task.labels.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {task.labels.slice(0, 3).map((label) => (
            <span
              key={label}
              className="px-1.5 py-0.5 text-xs bg-dark-border rounded text-text-secondary"
            >
              {label}
            </span>
          ))}
          {task.labels.length > 3 && (
            <span className="text-xs text-text-muted">+{task.labels.length - 3}</span>
          )}
        </div>
      )}
      {lease && (
        <div className="flex items-center justify-between text-xs border-t border-dark-border pt-2 mt-2">
          <span className="text-blue-400 truncate max-w-[120px]">
            {claimingAgent?.displayName || lease.agentId.slice(0, 8)}
          </span>
          <LeaseCountdown lease={lease} />
        </div>
      )}
    </div>
  )
}

function TaskDetailsSidebar({ task, lease, onClose }: TaskDetailsSidebarProps) {
  const claimingAgent = useAgentById(lease?.agentId || '')

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-dark-surface border-l border-dark-border shadow-xl z-50 flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-dark-border">
        <div>
          <span className="text-text-muted font-mono text-sm">{task.id}</span>
          <PriorityBadge priority={task.priority} />
        </div>
        <button
          onClick={onClose}
          className="text-text-secondary hover:text-text-primary text-xl"
        >
          ×
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">{task.title}</h2>
        </div>
        <div>
          <h3 className="text-sm text-text-muted mb-1">Status</h3>
          <span className={clsx(
            'px-2 py-1 rounded text-sm capitalize',
            task.status === 'todo' && 'bg-gray-500/20 text-gray-400',
            task.status === 'ready' && 'bg-yellow-500/20 text-yellow-400',
            task.status === 'blocked' && 'bg-red-500/20 text-red-400',
            task.status === 'done' && 'bg-green-500/20 text-green-400',
            task.status === 'verified' && 'bg-purple-500/20 text-purple-400',
          )}>
            {task.status === 'ready' && lease ? 'in progress' : task.status}
          </span>
        </div>
        <div>
          <h3 className="text-sm text-text-muted mb-1">Description</h3>
          <p className="text-text-secondary text-sm whitespace-pre-wrap">
            {task.description || 'No description provided.'}
          </p>
        </div>
        {task.labels.length > 0 && (
          <div>
            <h3 className="text-sm text-text-muted mb-1">Labels</h3>
            <div className="flex flex-wrap gap-1">
              {task.labels.map((label) => (
                <span
                  key={label}
                  className="px-2 py-0.5 text-sm bg-dark-border rounded text-text-secondary"
                >
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}
        {task.dependencies.length > 0 && (
          <div>
            <h3 className="text-sm text-text-muted mb-1">Dependencies</h3>
            <div className="flex flex-wrap gap-1">
              {task.dependencies.map((dep) => (
                <span
                  key={dep}
                  className="px-2 py-0.5 text-sm font-mono bg-dark-border rounded text-text-muted"
                >
                  {dep}
                </span>
              ))}
            </div>
          </div>
        )}
        {lease && (
          <div>
            <h3 className="text-sm text-gray-500 mb-1">Current Lease</h3>
            <div className="bg-dark-bg rounded p-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Agent</span>
                <span className="text-blue-400">
                  {claimingAgent?.displayName || lease.agentId}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Time Remaining</span>
                <LeaseCountdown lease={lease} />
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Expires</span>
                <span className="text-gray-300">
                  {formatDistanceToNow(new Date(lease.expiresAt), { addSuffix: true })}
                </span>
              </div>
            </div>
          </div>
        )}
        <div className="text-xs text-text-muted pt-4 border-t border-dark-border">
          <div>Created: {formatDistanceToNow(new Date(task.createdAt), { addSuffix: true })}</div>
          <div>Updated: {formatDistanceToNow(new Date(task.updatedAt), { addSuffix: true })}</div>
        </div>
      </div>
    </div>
  )
}

export function TaskBoard() {
  const tasks = useTasksList()
  const leases = useLeasesList()
  const agents = useAgentsList()
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [filters, setFilters] = useState<FilterState>({
    label: '',
    priority: '',
    agent: '',
  })

  // Map of taskId -> lease
  const taskLeaseMap = useMemo(() => {
    const map = new Map<string, Lease>()
    leases.forEach((lease) => map.set(lease.taskId, lease))
    return map
  }, [leases])

  // Get unique labels for filter dropdown
  const allLabels = useMemo(() => {
    const labelSet = new Set<string>()
    tasks.forEach((t) => t.labels.forEach((l) => labelSet.add(l)))
    return Array.from(labelSet).sort()
  }, [tasks])

  // Filter tasks
  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      if (filters.label && !task.labels.includes(filters.label)) return false
      if (filters.priority && task.priority > parseInt(filters.priority)) return false
      if (filters.agent) {
        const lease = taskLeaseMap.get(task.id)
        if (!lease) return false
        const agent = agents.find((a) => a.id === lease.agentId)
        const agentName = agent?.displayName || lease.agentId
        if (!agentName.toLowerCase().includes(filters.agent.toLowerCase())) return false
      }
      return true
    })
  }, [tasks, filters, taskLeaseMap, agents])

  // Group tasks by column
  const tasksByColumn = useMemo(() => {
    const columns: Record<ColumnStatus, Task[]> = {
      todo: [],
      ready: [],
      in_progress: [],
      blocked: [],
      done: [],
      verified: [],
    }

    filteredTasks.forEach((task) => {
      if (task.status === 'deleted') return

      if (task.status === 'todo') {
        columns.todo.push(task)
      } else if (task.status === 'ready') {
        // Check if it has an active lease (in progress)
        if (taskLeaseMap.has(task.id)) {
          columns.in_progress.push(task)
        } else {
          columns.ready.push(task)
        }
      } else if (task.status === 'blocked') {
        columns.blocked.push(task)
      } else if (task.status === 'done') {
        columns.done.push(task)
      } else if (task.status === 'verified') {
        columns.verified.push(task)
      }
    })

    // Sort each column by priority
    Object.values(columns).forEach((col) => col.sort((a, b) => a.priority - b.priority))

    return columns
  }, [filteredTasks, taskLeaseMap])

  const selectedTask = selectedTaskId ? tasks.find((t) => t.id === selectedTaskId) : null

  return (
    <div className="h-full flex flex-col">
      {/* Filters */}
      <div className="flex items-center gap-4 mb-4 flex-shrink-0">
        <select
          value={filters.label}
          onChange={(e) => setFilters((f) => ({ ...f, label: e.target.value }))}
          className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Labels</option>
          {allLabels.map((label) => (
            <option key={label} value={label}>{label}</option>
          ))}
        </select>
        <select
          value={filters.priority}
          onChange={(e) => setFilters((f) => ({ ...f, priority: e.target.value }))}
          className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Priorities</option>
          <option value="3">P1-P3 (High)</option>
          <option value="5">P1-P5 (Medium+)</option>
          <option value="7">P1-P7 (Low+)</option>
        </select>
        <input
          type="text"
          placeholder="Filter by agent name..."
          value={filters.agent}
          onChange={(e) => setFilters((f) => ({ ...f, agent: e.target.value }))}
          className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-sm w-48"
        />
        {(filters.label || filters.priority || filters.agent) && (
          <button
            onClick={() => setFilters({ label: '', priority: '', agent: '' })}
            className="text-sm text-text-secondary hover:text-text-primary"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Kanban Board */}
      <div className="flex-1 flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((column) => (
          <div
            key={column.key}
            className={clsx(
              'flex-1 min-w-[280px] max-w-[320px] bg-dark-surface/50 rounded-lg border-t-2',
              column.color
            )}
          >
            <div className="p-3 border-b border-dark-border flex items-center justify-between">
              <h3 className="font-medium text-text-secondary">{column.label}</h3>
              <span className="text-sm text-text-muted">
                {tasksByColumn[column.key].length}
              </span>
            </div>
            <div className="p-2 space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto">
              {tasksByColumn[column.key].map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  lease={taskLeaseMap.get(task.id)}
                  onClick={() => setSelectedTaskId(task.id)}
                />
              ))}
              {tasksByColumn[column.key].length === 0 && (
                <div className="text-center text-text-muted text-sm py-4">
                  No tasks
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Details Sidebar */}
      {selectedTask && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setSelectedTaskId(null)}
          />
          <TaskDetailsSidebar
            task={selectedTask}
            lease={taskLeaseMap.get(selectedTask.id)}
            onClose={() => setSelectedTaskId(null)}
          />
        </>
      )}
    </div>
  )
}
