import { useState } from 'react'
import { useAgentsList, useLeasesList } from '../stores'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'
import type { Agent } from '../types'

interface AgentRowProps {
  agent: Agent
  currentTaskId: string | null
  isExpanded: boolean
  onToggle: () => void
}

function AgentAvatar({ agent, size = 'md' }: { agent: Agent; size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-sm',
    lg: 'w-10 h-10 text-base',
  }

  const statusColors = {
    online: 'bg-green-500',
    idle: 'bg-yellow-500',
    offline: 'bg-gray-500',
  }

  const initials = agent.displayName
    ? agent.displayName
      .split(' ')
      .map((n) => n[0])
      .join('')
      .slice(0, 2)
      .toUpperCase()
    : agent.id.slice(0, 2).toUpperCase()

  return (
    <div className="relative">
      <div
        className={clsx(
          'rounded-full bg-dark-border flex items-center justify-center text-text-secondary font-medium',
          sizeClasses[size]
        )}
      >
        {initials}
      </div>
      <div
        className={clsx(
          'absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-dark-surface',
          statusColors[agent.status]
        )}
        title={agent.status}
      />
    </div>
  )
}

function AgentRow({ agent, currentTaskId, isExpanded, onToggle }: AgentRowProps) {
  const statusColors = {
    online: 'text-green-500',
    idle: 'text-yellow-500',
    offline: 'text-text-muted',
  }

  return (
    <>
      <tr
        className="border-b border-dark-border hover:bg-dark-bg-secondary cursor-pointer"
        onClick={onToggle}
      >
        <td className="py-3 px-4">
          <div className="flex items-center gap-3">
            <AgentAvatar agent={agent} />
            <div>
              <div className="font-medium text-text-primary">
                {agent.displayName || 'Anonymous Agent'}
              </div>
              <div className="text-xs text-text-muted font-mono">{agent.id}</div>
            </div>
          </div>
        </td>
        <td className="py-3 px-4">
          <span className={clsx('capitalize', statusColors[agent.status])}>
            {agent.status}
          </span>
        </td>
        <td className="py-3 px-4 text-text-secondary">
          {currentTaskId ? (
            <span className="font-mono text-blue-500">{currentTaskId}</span>
          ) : (
            <span className="text-text-muted">--</span>
          )}
        </td>
        <td className="py-3 px-4 text-text-secondary text-sm">
          {agent.lastSeenAt ? formatDistanceToNow(new Date(agent.lastSeenAt), { addSuffix: true }) : '--'}
        </td>
        <td className="py-3 px-4 text-right">
          <button className="text-text-secondary hover:text-text-primary">
            {isExpanded ? '▼' : '▶'}
          </button>
        </td>
      </tr>
      {isExpanded && (
        <tr className="bg-dark-bg/50">
          <td colSpan={5} className="px-4 py-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <h4 className="text-text-secondary mb-2">Capabilities</h4>
                <div className="flex flex-wrap gap-1">
                  {agent.capabilities.length > 0 ? (
                    agent.capabilities.map((cap) => (
                      <span
                        key={cap}
                        className="px-2 py-0.5 bg-dark-border rounded text-text-secondary text-xs"
                      >
                        {cap}
                      </span>
                    ))
                  ) : (
                    <span className="text-text-muted">No capabilities listed</span>
                  )}
                </div>
              </div>
              <div>
                <h4 className="text-text-secondary mb-2">Session Info</h4>
                <div className="space-y-1 text-text-secondary">
                  {agent.sessionMeta?.model && (
                    <div>Model: <span className="text-text-primary">{agent.sessionMeta.model}</span></div>
                  )}
                  {agent.sessionMeta?.client && (
                    <div>Client: <span className="text-text-primary">{agent.sessionMeta.client}</span></div>
                  )}
                  <div>
                    Registered: {agent.registeredAt ? formatDistanceToNow(new Date(agent.registeredAt), { addSuffix: true }) : '--'}
                  </div>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export function AgentPanel() {
  const agents = useAgentsList()
  const leases = useLeasesList()
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  // Map of agentId -> taskId from leases
  const agentTaskMap = new Map<string, string>()
  leases.forEach((lease) => {
    agentTaskMap.set(lease.agentId, lease.taskId)
  })

  const toggleExpanded = (agentId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(agentId)) {
        next.delete(agentId)
      } else {
        next.add(agentId)
      }
      return next
    })
  }

  // Sort: online first, then idle, then offline; within same status, by last seen
  const sortedAgents = [...agents].sort((a, b) => {
    const statusOrder = { online: 0, idle: 1, offline: 2 }
    if (statusOrder[a.status] !== statusOrder[b.status]) {
      return statusOrder[a.status] - statusOrder[b.status]
    }
    const aTime = a.lastSeenAt ? new Date(a.lastSeenAt).getTime() : 0
    const bTime = b.lastSeenAt ? new Date(b.lastSeenAt).getTime() : 0
    return bTime - aTime
  })

  if (agents.length === 0) {
    return (
      <div className="bg-dark-surface border border-dark-border rounded-lg p-8 text-center">
        <div className="text-text-secondary">No agents registered</div>
        <div className="text-text-muted text-sm mt-1">
          Agents will appear here when they connect to Lodestar
        </div>
      </div>
    )
  }

  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg overflow-hidden">
      <table className="w-full">
        <thead className="bg-dark-bg/50">
          <tr className="text-left text-sm text-text-secondary">
            <th className="py-3 px-4 font-medium">Agent</th>
            <th className="py-3 px-4 font-medium">Status</th>
            <th className="py-3 px-4 font-medium">Current Task</th>
            <th className="py-3 px-4 font-medium">Last Seen</th>
            <th className="py-3 px-4 w-12"></th>
          </tr>
        </thead>
        <tbody>
          {sortedAgents.map((agent) => (
            <AgentRow
              key={agent.id}
              agent={agent}
              currentTaskId={agentTaskMap.get(agent.id) || null}
              isExpanded={expandedIds.has(agent.id)}
              onToggle={() => toggleExpanded(agent.id)}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}
