import { useState, useMemo } from 'react'
import { useRecentEvents, useAgentById, useTaskById } from '../stores'
import { formatDistanceToNow, format } from 'date-fns'
import clsx from 'clsx'
import type { LodestarEvent, EventType } from '../types'

interface EventItemProps {
  event: LodestarEvent
  isExpanded: boolean
  onToggle: () => void
}

const eventConfig: Record<EventType, { icon: string; color: string; label: string }> = {
  'agent.joined': { icon: '👋', color: 'bg-green-500', label: 'Agent Joined' },
  'agent.left': { icon: '👋', color: 'bg-red-500', label: 'Agent Left' },
  'agent.heartbeat': { icon: '💓', color: 'bg-gray-500', label: 'Heartbeat' },
  'task.claimed': { icon: '🎯', color: 'bg-blue-500', label: 'Task Claimed' },
  'task.released': { icon: '📤', color: 'bg-yellow-500', label: 'Task Released' },
  'task.done': { icon: '✅', color: 'bg-green-500', label: 'Task Done' },
  'task.verified': { icon: '✨', color: 'bg-purple-500', label: 'Task Verified' },
  'message.sent': { icon: '💬', color: 'bg-cyan-500', label: 'Message Sent' },
}

function EventItem({ event, isExpanded, onToggle }: EventItemProps) {
  const config = eventConfig[event.type] || { icon: '📌', color: 'bg-gray-500', label: event.type }
  const agent = useAgentById(event.actorAgentId || '')
  const targetAgent = useAgentById(event.targetAgentId || '')
  const task = useTaskById(event.taskId || '')

  return (
    <div className="relative pl-8 pb-6 group">
      {/* Timeline line */}
      <div className="absolute left-3 top-6 bottom-0 w-px bg-dark-border group-last:hidden" />

      {/* Event dot */}
      <div
        className={clsx(
          'absolute left-0 top-1 w-6 h-6 rounded-full flex items-center justify-center text-sm',
          config.color
        )}
      >
        {config.icon}
      </div>

      {/* Event content */}
      <div
        className={clsx(
          'bg-dark-surface border border-dark-border rounded-lg p-3 cursor-pointer hover:border-gray-600 transition-colors',
          isExpanded && 'border-gray-600'
        )}
        onClick={onToggle}
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            <span className="text-sm font-medium text-gray-200">
              {config.label}
            </span>
            {event.taskId && (
              <span className="ml-2 text-xs font-mono text-blue-400">
                {event.taskId}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">
              {formatDistanceToNow(new Date(event.createdAt), { addSuffix: true })}
            </span>
            <span className="text-gray-400 text-xs">
              {isExpanded ? '▼' : '▶'}
            </span>
          </div>
        </div>

        {/* Actor info */}
        {event.actorAgentId && (
          <div className="text-xs text-gray-400 mt-1">
            by {agent?.displayName || event.actorAgentId.slice(0, 8)}
          </div>
        )}

        {/* Expanded details */}
        {isExpanded && (
          <div className="mt-3 pt-3 border-t border-dark-border space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-gray-500">Event ID:</span>
                <span className="ml-2 text-gray-300 font-mono">{event.id}</span>
              </div>
              <div>
                <span className="text-gray-500">Time:</span>
                <span className="ml-2 text-gray-300">
                  {format(new Date(event.createdAt), 'HH:mm:ss')}
                </span>
              </div>
              {event.actorAgentId && (
                <div>
                  <span className="text-gray-500">Actor:</span>
                  <span className="ml-2 text-gray-300">
                    {agent?.displayName || event.actorAgentId}
                  </span>
                </div>
              )}
              {event.targetAgentId && (
                <div>
                  <span className="text-gray-500">Target:</span>
                  <span className="ml-2 text-gray-300">
                    {targetAgent?.displayName || event.targetAgentId}
                  </span>
                </div>
              )}
              {event.taskId && task && (
                <div className="col-span-2">
                  <span className="text-gray-500">Task:</span>
                  <span className="ml-2 text-gray-300">{task.title}</span>
                </div>
              )}
            </div>
            {event.payload && Object.keys(event.payload).length > 0 && (
              <div>
                <span className="text-gray-500">Payload:</span>
                <pre className="mt-1 p-2 bg-dark-bg rounded text-xs text-gray-400 overflow-x-auto">
                  {JSON.stringify(event.payload, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

type FilterType = 'all' | EventType

export function EventTimeline({ limit = 100 }: { limit?: number }) {
  const events = useRecentEvents(limit)
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())
  const [filter, setFilter] = useState<FilterType>('all')
  const [hideHeartbeats, setHideHeartbeats] = useState(true)

  const toggleExpanded = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  // Filter events
  const filteredEvents = useMemo(() => {
    let result = [...events]

    if (hideHeartbeats) {
      result = result.filter((e) => e.type !== 'agent.heartbeat')
    }

    if (filter !== 'all') {
      result = result.filter((e) => e.type === filter)
    }

    // Sort by time, newest first
    result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())

    return result
  }, [events, filter, hideHeartbeats])

  const eventTypes = Object.keys(eventConfig) as EventType[]

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as FilterType)}
          className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="all">All Events</option>
          {eventTypes.map((type) => (
            <option key={type} value={type}>
              {eventConfig[type].icon} {eventConfig[type].label}
            </option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-sm text-gray-400">
          <input
            type="checkbox"
            checked={hideHeartbeats}
            onChange={(e) => setHideHeartbeats(e.target.checked)}
            className="rounded border-dark-border bg-dark-surface"
          />
          Hide heartbeats
        </label>

        <span className="text-sm text-gray-500 ml-auto">
          {filteredEvents.length} events
        </span>
      </div>

      {/* Timeline */}
      {filteredEvents.length === 0 ? (
        <div className="bg-dark-surface border border-dark-border rounded-lg p-8 text-center">
          <div className="text-gray-400">No events to display</div>
          <div className="text-gray-500 text-sm mt-1">
            Events will appear here as agents interact with tasks
          </div>
        </div>
      ) : (
        <div className="bg-dark-surface border border-dark-border rounded-lg p-4">
          <div className="max-h-[600px] overflow-y-auto">
            {filteredEvents.map((event) => (
              <EventItem
                key={event.id}
                event={event}
                isExpanded={expandedIds.has(event.id)}
                onToggle={() => toggleExpanded(event.id)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
