import { useState, useMemo } from 'react'
import { useDataStore, useAgentById, useAgentsList } from '../stores'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'
import type { Message, MessageSeverity } from '../types'

interface MessageItemProps {
  message: Message
  isExpanded: boolean
  onToggle: () => void
}

const severityStyles: Record<MessageSeverity, { bg: string; border: string; icon: string }> = {
  info: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', icon: 'ℹ️' },
  warning: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', icon: '⚠️' },
  handoff: { bg: 'bg-purple-500/10', border: 'border-purple-500/30', icon: '🤝' },
  blocker: { bg: 'bg-red-500/10', border: 'border-red-500/30', icon: '🚫' },
}

function MessageItem({ message, isExpanded, onToggle }: MessageItemProps) {
  const fromAgent = useAgentById(message.from)
  const agents = useAgentsList()

  const isLongMessage = message.body.length > 200
  const displayBody = isExpanded || !isLongMessage
    ? message.body
    : message.body.slice(0, 200) + '...'

  const severity = message.severity || 'info'
  const style = severityStyles[severity]
  
  const isUnread = message.readBy.length === 0
  const readByAgents = agents.filter(a => message.readBy.includes(a.id))

  return (
    <div
      className={clsx(
        'p-4 rounded-lg border transition-colors',
        style.bg,
        style.border,
        isUnread && 'ring-2 ring-blue-400/50'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          {/* Unread indicator */}
          {isUnread && (
            <div className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0" />
          )}
          <span className="text-sm font-medium text-text-primary">
            {fromAgent?.displayName || message.from.slice(0, 8)}
          </span>
          <span className="text-text-muted">→</span>
          <span className="text-sm text-text-secondary">
            <span className="font-mono text-blue-500">{message.taskId}</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-lg" title={severity}>
            {style.icon}
          </span>
          <span className="text-xs text-text-muted">
            {formatDistanceToNow(new Date(message.createdAt), { addSuffix: true })}
          </span>
        </div>
      </div>

      {/* Subject */}
      {message.subject && (
        <div className="text-sm font-medium text-text-primary mb-2">
          {message.subject}
        </div>
      )}

      {/* Body */}
      <div className="text-sm text-text-secondary whitespace-pre-wrap">
        {displayBody}
      </div>

      {/* Expand/Collapse */}
      {isLongMessage && (
        <button
          onClick={onToggle}
          className="mt-2 text-xs text-blue-400 hover:text-blue-300"
        >
          {isExpanded ? 'Show less' : 'Show more'}
        </button>
      )}

      {/* Read status */}
      <div className="mt-2 pt-2 border-t border-dark-border flex items-center justify-between">
        <span className="text-xs text-text-muted">
          Thread: <span className="font-mono text-text-secondary">{message.taskId}</span>
        </span>
        {message.readBy.length > 0 && (
          <span className="text-xs text-text-muted">
            Read by: {readByAgents.map(a => a.displayName || a.id.slice(0, 8)).join(', ')}
          </span>
        )}
      </div>
    </div>
  )
}

type FilterMode = 'all' | 'task' | 'unread' | 'severity'
type GroupMode = 'none' | 'thread'

export function MessageFeed() {
  const messages = useDataStore((state) => state.messages)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [filterMode, setFilterMode] = useState<FilterMode>('all')
  const [filterValue, setFilterValue] = useState('')
  const [groupMode, setGroupMode] = useState<GroupMode>('thread')

  const toggleExpanded = (id: string) => {
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

  // Filter messages
  const filteredMessages = useMemo(() => {
    let result = [...messages]

    if (filterMode === 'unread') {
      result = result.filter((m) => m.readBy.length === 0)
    } else if (filterMode === 'task' && filterValue) {
      result = result.filter(
        (m) => m.taskId.toLowerCase().includes(filterValue.toLowerCase())
      )
    } else if (filterMode === 'severity' && filterValue) {
      result = result.filter(
        (m) => m.severity === filterValue
      )
    }

    // Sort by date, newest first
    result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())

    return result
  }, [messages, filterMode, filterValue])

  // Group messages by thread if enabled
  const groupedMessages = useMemo(() => {
    if (groupMode === 'none') {
      return { ungrouped: filteredMessages }
    }

    const groups: Record<string, Message[]> = {}
    filteredMessages.forEach((msg) => {
      const key = msg.taskId
      if (!groups[key]) groups[key] = []
      groups[key].push(msg)
    })

    return groups
  }, [filteredMessages, groupMode])

  const unreadCount = messages.filter((m) => m.readBy.length === 0).length

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <select
          value={filterMode}
          onChange={(e) => {
            setFilterMode(e.target.value as FilterMode)
            setFilterValue('')
          }}
          className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="all">All Messages</option>
          <option value="unread">Unread ({unreadCount})</option>
          <option value="task">By Task</option>
          <option value="severity">By Severity</option>
        </select>

        {filterMode === 'task' && (
          <input
            type="text"
            placeholder="Task ID..."
            value={filterValue}
            onChange={(e) => setFilterValue(e.target.value)}
            className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-sm w-40"
          />
        )}

        {filterMode === 'severity' && (
          <select
            value={filterValue}
            onChange={(e) => setFilterValue(e.target.value)}
            className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Severities</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="handoff">Handoff</option>
            <option value="blocker">Blocker</option>
          </select>
        )}

        <div className="flex items-center gap-2 ml-auto">
          <span className="text-sm text-text-muted">Group by:</span>
          <select
            value={groupMode}
            onChange={(e) => setGroupMode(e.target.value as GroupMode)}
            className="bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-sm"
          >
            <option value="none">None</option>
            <option value="thread">Task Thread</option>
          </select>
        </div>
      </div>

      {/* Messages */}
      {filteredMessages.length === 0 ? (
        <div className="bg-dark-surface border border-dark-border rounded-lg p-8 text-center">
          <div className="text-text-secondary">No messages to display</div>
          <div className="text-text-muted text-sm mt-1">
            {filterMode !== 'all'
              ? 'Try adjusting your filters'
              : 'Messages will appear here when agents communicate'}
          </div>
        </div>
      ) : groupMode === 'thread' ? (
        <div className="space-y-6">
          {Object.entries(groupedMessages).map(([threadId, threadMessages]) => (
            <div key={threadId} className="space-y-2">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium text-text-secondary">
                  Task Thread: {threadId}
                </h3>
                <span className="text-xs text-text-muted">
                  ({threadMessages.length} {threadMessages.length === 1 ? 'message' : 'messages'})
                </span>
              </div>
              <div className="space-y-2 pl-4 border-l-2 border-dark-border">
                {threadMessages.map((msg) => (
                  <MessageItem
                    key={msg.id}
                    message={msg}
                    isExpanded={expandedIds.has(msg.id)}
                    onToggle={() => toggleExpanded(msg.id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {filteredMessages.map((msg) => (
            <MessageItem
              key={msg.id}
              message={msg}
              isExpanded={expandedIds.has(msg.id)}
              onToggle={() => toggleExpanded(msg.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
