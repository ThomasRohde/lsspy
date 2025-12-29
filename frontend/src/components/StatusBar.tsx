import { useDataStore, useAgentsList, useTasksList, useLeasesList } from '../stores'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

export function StatusBar() {
  const isConnected = useDataStore((state) => state.isConnected)
  const lastSyncAt = useDataStore((state) => state.lastSyncAt)
  const repoStatus = useDataStore((state) => state.repoStatus)
  const connectionError = useDataStore((state) => state.connectionError)
  const reconnectAttempts = useDataStore((state) => state.reconnectAttempts)

  const agents = useAgentsList()
  const tasks = useTasksList()
  const leases = useLeasesList()

  // Calculate stats
  const activeAgents = agents.filter((a) => a.status === 'online').length
  const openTasks = tasks.filter((t) => t.status === 'ready').length
  const inProgressTasks = leases.length

  // Find expiring leases (within 5 minutes)
  const now = new Date()
  const expiringLeases = leases.filter((l) => {
    const expiresAt = new Date(l.expiresAt)
    const minutesUntilExpiry = (expiresAt.getTime() - now.getTime()) / 1000 / 60
    return minutesUntilExpiry > 0 && minutesUntilExpiry <= 5
  })

  return (
    <div className="h-8 bg-dark-surface border-t border-dark-border flex items-center px-4 text-xs">
      {/* Project info */}
      <div className="flex items-center gap-2">
        <span className="text-gray-400">Lodestar</span>
        <span className="text-gray-600">|</span>
        <span className="text-gray-500 font-mono">lsspy</span>
      </div>

      {/* Connection status */}
      <div className="ml-4 flex items-center gap-2">
        <div
          className={clsx(
            'w-2 h-2 rounded-full',
            isConnected ? 'bg-green-500' : reconnectAttempts > 0 ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'
          )}
        />
        <span className={clsx(
          isConnected ? 'text-green-400' : reconnectAttempts > 0 ? 'text-yellow-400' : 'text-red-400'
        )}>
          {isConnected ? 'Connected' : reconnectAttempts > 0 ? `Reconnecting (${reconnectAttempts}/10)` : 'Disconnected'}
        </span>
      </div>

      {/* Connection error */}
      {connectionError && !isConnected && (
        <div className="ml-4 text-orange-400 text-xs max-w-64 truncate" title={connectionError}>
          {connectionError}
        </div>
      )}

      {/* Last sync */}
      {lastSyncAt && (
        <div className="ml-4 text-gray-500">
          Last sync: {formatDistanceToNow(new Date(lastSyncAt), { addSuffix: true })}
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Quick stats */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">Agents:</span>
          <span className={activeAgents > 0 ? 'text-blue-400' : 'text-gray-400'}>
            {activeAgents}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">Ready:</span>
          <span className={openTasks > 0 ? 'text-yellow-400' : 'text-gray-400'}>
            {openTasks}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">In Progress:</span>
          <span className={inProgressTasks > 0 ? 'text-green-400' : 'text-gray-400'}>
            {inProgressTasks}
          </span>
        </div>

        {expiringLeases.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-orange-500">Expiring:</span>
            <span className="text-orange-400">{expiringLeases.length}</span>
          </div>
        )}

        {repoStatus && (
          <div className="flex items-center gap-1.5">
            <span className="text-gray-500">Total:</span>
            <span className="text-gray-300">{repoStatus.totalTasks}</span>
          </div>
        )}
      </div>
    </div>
  )
}
