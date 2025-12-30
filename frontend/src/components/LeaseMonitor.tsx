import { useState, useEffect, useCallback } from 'react'
import { useLeasesList, useAgentById, useTaskById } from '../stores'
import { formatDistanceToNow, differenceInSeconds } from 'date-fns'
import clsx from 'clsx'
import type { Lease } from '../types'

type LeaseStatus = 'healthy' | 'warning' | 'critical' | 'expired'

interface LeaseRowProps {
  lease: Lease
  onExpiringSoon?: (lease: Lease) => void
}

function getLeaseStatus(lease: Lease): { status: LeaseStatus; percentRemaining: number; secondsRemaining: number } {
  const now = new Date()
  const expiresAt = new Date(lease.expiresAt)
  const createdAt = new Date(lease.createdAt)

  const totalSeconds = differenceInSeconds(expiresAt, createdAt)
  const secondsRemaining = differenceInSeconds(expiresAt, now)
  const percentRemaining = Math.max(0, Math.min(100, (secondsRemaining / totalSeconds) * 100))

  let status: LeaseStatus
  if (secondsRemaining <= 0) {
    status = 'expired'
  } else if (percentRemaining <= 15) {
    status = 'critical'
  } else if (percentRemaining <= 40) {
    status = 'warning'
  } else {
    status = 'healthy'
  }

  return { status, percentRemaining, secondsRemaining }
}

function formatTimeRemaining(seconds: number): string {
  if (seconds <= 0) return 'Expired'

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  } else {
    return `${secs}s`
  }
}

const statusColors = {
  healthy: {
    text: 'text-green-400',
    bg: 'bg-green-500',
    border: 'border-green-500',
  },
  warning: {
    text: 'text-yellow-400',
    bg: 'bg-yellow-500',
    border: 'border-yellow-500',
  },
  critical: {
    text: 'text-orange-400',
    bg: 'bg-orange-500',
    border: 'border-orange-500',
  },
  expired: {
    text: 'text-red-400',
    bg: 'bg-red-500',
    border: 'border-red-500',
  },
}

function LeaseRow({ lease, onExpiringSoon }: LeaseRowProps) {
  const agent = useAgentById(lease.agentId)
  const task = useTaskById(lease.taskId)
  const [leaseInfo, setLeaseInfo] = useState(() => getLeaseStatus(lease))
  const [hasNotified, setHasNotified] = useState(false)

  // Update countdown every second
  useEffect(() => {
    const interval = setInterval(() => {
      const info = getLeaseStatus(lease)
      setLeaseInfo(info)

      // Notify when entering critical status
      if (info.status === 'critical' && !hasNotified && onExpiringSoon) {
        onExpiringSoon(lease)
        setHasNotified(true)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [lease, hasNotified, onExpiringSoon])

  const colors = statusColors[leaseInfo.status]

  return (
    <tr className="border-b border-dark-border hover:bg-dark-bg-secondary">
      <td className="py-3 px-4">
        <span className="font-mono text-blue-400">{lease.taskId}</span>
        {task && (
          <div className="text-xs text-text-muted truncate max-w-[200px]">
            {task.title}
          </div>
        )}
      </td>
      <td className="py-3 px-4">
        <span className="text-text-secondary">
          {agent?.displayName || lease.agentId.slice(0, 8)}
        </span>
      </td>
      <td className="py-3 px-4 text-text-secondary text-sm">
        {formatDistanceToNow(new Date(lease.createdAt), { addSuffix: true })}
      </td>
      <td className="py-3 px-4 text-text-secondary text-sm">
        {formatDistanceToNow(new Date(lease.expiresAt), { addSuffix: true })}
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <span className={clsx('font-mono text-sm', colors.text)}>
            {formatTimeRemaining(leaseInfo.secondsRemaining)}
          </span>
        </div>
      </td>
      <td className="py-3 px-4">
        <div className="w-24">
          <div className="h-2 bg-dark-border rounded-full overflow-hidden">
            <div
              className={clsx('h-full transition-all duration-1000', colors.bg)}
              style={{ width: `${leaseInfo.percentRemaining}%` }}
            />
          </div>
        </div>
      </td>
      <td className="py-3 px-4">
        <span
          className={clsx(
            'px-2 py-0.5 rounded text-xs font-medium capitalize',
            colors.text,
            'bg-opacity-20',
            leaseInfo.status === 'healthy' && 'bg-green-500/20',
            leaseInfo.status === 'warning' && 'bg-yellow-500/20',
            leaseInfo.status === 'critical' && 'bg-orange-500/20',
            leaseInfo.status === 'expired' && 'bg-red-500/20'
          )}
        >
          {leaseInfo.status}
        </span>
      </td>
    </tr>
  )
}

// Simple toast notification component
function Toast({
  message,
  type,
  onClose,
}: {
  message: string
  type: 'warning' | 'error'
  onClose: () => void
}) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div
      className={clsx(
        'flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg',
        type === 'warning' && 'bg-orange-500/90 text-orange-100',
        type === 'error' && 'bg-red-500/90 text-red-100'
      )}
    >
      <span className="text-lg">{type === 'warning' ? '⚠️' : '❌'}</span>
      <span className="text-sm font-medium">{message}</span>
      <button
        onClick={onClose}
        className="ml-2 text-white/70 hover:text-white"
      >
        ×
      </button>
    </div>
  )
}

interface ToastData {
  id: string
  message: string
  type: 'warning' | 'error'
}

export function LeaseMonitor() {
  const leases = useLeasesList()
  const [toasts, setToasts] = useState<ToastData[]>([])

  const handleExpiringSoon = useCallback((lease: Lease) => {
    const id = `${lease.leaseId}-${Date.now()}`
    setToasts((prev) => [
      ...prev,
      {
        id,
        message: `Lease for ${lease.taskId} is expiring soon!`,
        type: 'warning',
      },
    ])
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  // Sort leases by time remaining (most urgent first)
  const sortedLeases = [...leases].sort((a, b) => {
    const aInfo = getLeaseStatus(a)
    const bInfo = getLeaseStatus(b)
    return aInfo.secondsRemaining - bInfo.secondsRemaining
  })

  if (leases.length === 0) {
    return (
      <div className="bg-dark-surface border border-dark-border rounded-lg p-8 text-center">
        <div className="text-text-secondary">No active leases</div>
        <div className="text-text-muted text-sm mt-1">
          Leases will appear here when agents claim tasks
        </div>
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Toast Container */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>

      {/* Lease Table */}
      <div className="bg-dark-surface border border-dark-border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-dark-border flex items-center justify-between">
          <h3 className="font-semibold text-text-primary">Active Leases</h3>
          <span className="text-sm text-text-muted">{leases.length} active</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-dark-bg/50">
              <tr className="text-left text-sm text-text-secondary">
                <th className="py-3 px-4 font-medium">Task</th>
                <th className="py-3 px-4 font-medium">Agent</th>
                <th className="py-3 px-4 font-medium">Created</th>
                <th className="py-3 px-4 font-medium">Expires</th>
                <th className="py-3 px-4 font-medium">Time Left</th>
                <th className="py-3 px-4 font-medium">Progress</th>
                <th className="py-3 px-4 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {sortedLeases.map((lease) => (
                <LeaseRow
                  key={lease.leaseId}
                  lease={lease}
                  onExpiringSoon={handleExpiringSoon}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center gap-6 text-xs text-text-muted">
        <span>Status:</span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          Healthy (60%+)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-yellow-500" />
          Warning (40-60%)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-orange-500" />
          Critical (&lt;15%)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-500" />
          Expired
        </span>
      </div>
    </div>
  )
}
