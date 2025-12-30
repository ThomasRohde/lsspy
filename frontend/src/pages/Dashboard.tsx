import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAgentsList, useTasksList, useLeasesList, useRecentEvents } from '../stores'
import { AgentPanel } from '../components/AgentPanel'
import { TaskBoard } from '../components/TaskBoard'
import { DependencyGraph } from '../components/DependencyGraph'
import { LeaseMonitor } from '../components/LeaseMonitor'
import { MessageFeed } from '../components/MessageFeed'
import { EventTimeline } from '../components/EventTimeline'
import { StatisticsPanel } from '../components/StatisticsPanel'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

type PanelView = 'overview' | 'tasks' | 'agents' | 'graph' | 'leases' | 'messages' | 'events' | 'stats'

function StatCard({
  label,
  value,
  color = 'text-white',
  subValue
}: {
  label: string
  value: number | string
  color?: string
  subValue?: string
}) {
  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg p-4">
      <h3 className="text-sm text-gray-400 mb-1">{label}</h3>
      <p className={clsx('text-2xl font-bold', color)}>{value}</p>
      {subValue && <p className="text-xs text-gray-500 mt-1">{subValue}</p>}
    </div>
  )
}

function RecentActivityFeed() {
  const events = useRecentEvents(10)

  if (events.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        No recent activity
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {events.map((event) => (
        <div
          key={event.id}
          className="flex items-center gap-3 py-2 px-3 rounded bg-dark-bg/50"
        >
          <div className={clsx(
            'w-2 h-2 rounded-full flex-shrink-0',
            event.type.includes('joined') && 'bg-green-500',
            event.type.includes('left') && 'bg-red-500',
            event.type.includes('claimed') && 'bg-blue-500',
            event.type.includes('done') && 'bg-yellow-500',
            event.type.includes('verified') && 'bg-purple-500',
            event.type.includes('message') && 'bg-cyan-500',
            !['joined', 'left', 'claimed', 'done', 'verified', 'message'].some(t => event.type.includes(t)) && 'bg-gray-500'
          )} />
          <div className="flex-1 min-w-0">
            <span className="text-sm text-text-primary font-medium">{event.type}</span>
            {event.taskId && (
              <span className="ml-2 text-xs font-mono text-blue-400">{event.taskId}</span>
            )}
            {event.actorAgentId && (
              <span className="ml-2 text-xs text-gray-500">by {event.actorAgentId.slice(0, 8)}</span>
            )}
          </div>
          <span className="text-xs text-gray-500 flex-shrink-0">
            {formatDistanceToNow(new Date(event.createdAt), { addSuffix: true })}
          </span>
        </div>
      ))}
    </div>
  )
}

export function Dashboard() {
  const [activePanel, setActivePanel] = useState<PanelView>('overview')
  const agents = useAgentsList()
  const tasks = useTasksList()
  const leases = useLeasesList()

  const activeAgents = agents.filter((a) => a.status === 'online').length
  const readyTasks = tasks.filter((t) => t.status === 'ready' && !leases.find(l => l.taskId === t.id)).length
  const inProgressTasks = leases.length
  const completedTasks = tasks.filter((t) => t.status === 'verified').length
  const doneTasks = tasks.filter((t) => t.status === 'done').length

  const panelTabs = [
    { key: 'overview' as PanelView, label: 'Overview' },
    { key: 'tasks' as PanelView, label: 'Tasks' },
    { key: 'agents' as PanelView, label: 'Agents' },
    { key: 'graph' as PanelView, label: 'Graph' },
    { key: 'leases' as PanelView, label: 'Leases' },
    { key: 'messages' as PanelView, label: 'Messages' },
    { key: 'events' as PanelView, label: 'Events' },
    { key: 'stats' as PanelView, label: 'Stats' },
  ]

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex bg-dark-surface rounded-lg border border-dark-border">
          {panelTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActivePanel(tab.key)}
              className={clsx(
                'px-4 py-2 text-sm transition-colors',
                activePanel === tab.key
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-gray-400 hover:text-white'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {activePanel === 'overview' && (
        <div className="space-y-6 flex-1 overflow-auto">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            <StatCard
              label="Active Agents"
              value={activeAgents}
              color="text-green-400"
              subValue={`${agents.length} total`}
            />
            <StatCard
              label="Ready Tasks"
              value={readyTasks}
              color="text-yellow-400"
            />
            <StatCard
              label="In Progress"
              value={inProgressTasks}
              color="text-blue-400"
            />
            <StatCard
              label="Pending Review"
              value={doneTasks}
              color="text-orange-400"
            />
            <StatCard
              label="Completed"
              value={completedTasks}
              color="text-purple-400"
              subValue={`${tasks.length} total`}
            />
          </div>

          {/* Two-column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Activity */}
            <div className="bg-dark-surface border border-dark-border rounded-lg overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border">
                <h2 className="font-semibold">Recent Activity</h2>
                <Link to="/events" className="text-sm text-blue-400 hover:text-blue-300">
                  View all
                </Link>
              </div>
              <div className="p-4 max-h-[300px] overflow-y-auto">
                <RecentActivityFeed />
              </div>
            </div>

            {/* Quick Agents View */}
            <div className="bg-dark-surface border border-dark-border rounded-lg overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border">
                <h2 className="font-semibold">Active Agents</h2>
                <Link to="/agents" className="text-sm text-blue-400 hover:text-blue-300">
                  View all
                </Link>
              </div>
              <div className="p-4 max-h-[300px] overflow-y-auto">
                {agents.filter(a => a.status === 'online').length > 0 ? (
                  <div className="space-y-2">
                    {agents.filter(a => a.status === 'online').slice(0, 5).map((agent) => {
                      const agentLease = leases.find(l => l.agentId === agent.id)
                      return (
                        <div
                          key={agent.id}
                          className="flex items-center justify-between py-2 px-3 rounded bg-dark-bg/50"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-green-500" />
                            <span className="text-sm text-gray-200">
                              {agent.displayName || agent.id.slice(0, 8)}
                            </span>
                          </div>
                          {agentLease && (
                            <span className="text-xs font-mono text-blue-400">
                              {agentLease.taskId}
                            </span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    No active agents
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {activePanel === 'tasks' && (
        <div className="flex-1 min-h-0">
          <TaskBoard />
        </div>
      )}

      {activePanel === 'agents' && (
        <div className="flex-1 overflow-auto">
          <AgentPanel />
        </div>
      )}

      {activePanel === 'graph' && (
        <div className="flex-1 min-h-0">
          <DependencyGraph />
        </div>
      )}

      {activePanel === 'leases' && (
        <div className="flex-1 overflow-auto">
          <LeaseMonitor />
        </div>
      )}

      {activePanel === 'messages' && (
        <div className="flex-1 overflow-auto">
          <MessageFeed />
        </div>
      )}

      {activePanel === 'events' && (
        <div className="flex-1 overflow-auto">
          <EventTimeline limit={200} />
        </div>
      )}

      {activePanel === 'stats' && (
        <div className="flex-1 overflow-auto">
          <StatisticsPanel />
        </div>
      )}
    </div>
  )
}
