import { useState, useMemo } from 'react'
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
} from 'recharts'
import { useTasksList, useAgentsList, useLeasesList, useRecentEvents } from '../stores'

interface CollapsibleSectionProps {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
}

function CollapsibleSection({ title, defaultOpen = true, children }: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg overflow-hidden">
      <button
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-dark-bg-secondary transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="font-medium text-text-primary">{title}</span>
        <span className="text-text-secondary">{isOpen ? '▼' : '▶'}</span>
      </button>
      {isOpen && (
        <div className="p-4 border-t border-dark-border">
          {children}
        </div>
      )}
    </div>
  )
}

const STATUS_COLORS: Record<string, string> = {
  ready: '#eab308',
  done: '#22c55e',
  verified: '#a855f7',
  deleted: '#6b7280',
}

function TaskStatusDistribution() {
  const tasks = useTasksList()

  const data = useMemo(() => {
    const counts: Record<string, number> = {}
    tasks.forEach((t) => {
      counts[t.status] = (counts[t.status] || 0) + 1
    })
    return Object.entries(counts).map(([status, count]) => ({
      name: status.charAt(0).toUpperCase() + status.slice(1),
      value: count,
      color: STATUS_COLORS[status] || '#6b7280',
    }))
  }, [tasks])

  if (data.length === 0) {
    return <div className="text-center text-gray-500 py-8">No task data</div>
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          dataKey="value"
          label={({ name, value }) => `${name}: ${value}`}
          labelLine={false}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

function TasksOverTime() {
  const events = useRecentEvents(1000)

  const data = useMemo(() => {
    // Group verified events by hour
    const hourlyData: Record<string, { done: number; verified: number }> = {}

    events.forEach((event) => {
      if (event.type === 'task.done' || event.type === 'task.verified') {
        const hour = new Date(event.createdAt).toISOString().slice(0, 13)
        if (!hourlyData[hour]) hourlyData[hour] = { done: 0, verified: 0 }
        if (event.type === 'task.done') hourlyData[hour].done++
        else hourlyData[hour].verified++
      }
    })

    return Object.entries(hourlyData)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-24)
      .map(([hour, counts]) => ({
        time: hour.slice(11, 13) + ':00',
        done: counts.done,
        verified: counts.verified,
      }))
  }, [events])

  if (data.length === 0) {
    return <div className="text-center text-gray-500 py-8">No completion data yet</div>
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} />
        <YAxis stroke="var(--text-muted)" fontSize={12} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
          }}
        />
        <Legend />
        <Line type="monotone" dataKey="done" stroke="#22c55e" name="Done" />
        <Line type="monotone" dataKey="verified" stroke="#a855f7" name="Verified" />
      </LineChart>
    </ResponsiveContainer>
  )
}

function AgentActivityOverview() {
  const agents = useAgentsList()
  const leases = useLeasesList()

  const data = useMemo(() => {
    return agents.map((agent) => {
      const agentLeases = leases.filter((l) => l.agentId === agent.id)
      return {
        name: agent.displayName || agent.id.slice(0, 8),
        active: agentLeases.length,
        status: agent.status,
      }
    }).filter((a) => a.status !== 'offline' || a.active > 0)
  }, [agents, leases])

  if (data.length === 0) {
    return <div className="text-center text-text-muted py-8">No agent data</div>
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} layout="vertical">
        <XAxis type="number" stroke="var(--text-muted)" fontSize={12} />
        <YAxis type="category" dataKey="name" stroke="var(--text-muted)" fontSize={12} width={80} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
          }}
        />
        <Bar dataKey="active" fill="#3b82f6" name="Active Tasks" />
      </BarChart>
    </ResponsiveContainer>
  )
}

function PriorityDistribution() {
  const tasks = useTasksList()

  const data = useMemo(() => {
    const counts: Record<number, number> = {}
    tasks.forEach((t) => {
      counts[t.priority] = (counts[t.priority] || 0) + 1
    })
    return Object.entries(counts)
      .map(([priority, count]) => ({
        priority: `P${priority}`,
        count,
      }))
      .sort((a, b) => parseInt(a.priority.slice(1)) - parseInt(b.priority.slice(1)))
  }, [tasks])

  if (data.length === 0) {
    return <div className="text-center text-gray-500 py-8">No task data</div>
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data}>
        <XAxis dataKey="priority" stroke="#6b7280" fontSize={12} />
        <YAxis stroke="#6b7280" fontSize={12} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
          }}
        />
        <Bar dataKey="count" fill="#eab308" name="Tasks" />
      </BarChart>
    </ResponsiveContainer>
  )
}

function QuickStats() {
  const tasks = useTasksList()
  const agents = useAgentsList()
  const leases = useLeasesList()
  const events = useRecentEvents(100)

  const stats = useMemo(() => ({
    totalTasks: tasks.length,
    readyTasks: tasks.filter((t) => t.status === 'ready').length,
    completedTasks: tasks.filter((t) => t.status === 'verified').length,
    activeAgents: agents.filter((a) => a.status === 'online').length,
    totalAgents: agents.length,
    activeLeases: leases.length,
    recentEvents: events.length,
  }), [tasks, agents, leases, events])

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="text-center">
        <div className="text-2xl font-bold text-yellow-500">{stats.readyTasks}</div>
        <div className="text-sm text-text-secondary">Ready</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-purple-500">{stats.completedTasks}</div>
        <div className="text-sm text-text-secondary">Verified</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-green-500">{stats.activeAgents}</div>
        <div className="text-sm text-text-secondary">Active Agents</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-blue-500">{stats.activeLeases}</div>
        <div className="text-sm text-text-secondary">Active Leases</div>
      </div>
    </div>
  )
}

export function StatisticsPanel() {
  return (
    <div className="space-y-4">
      <CollapsibleSection title="Quick Statistics" defaultOpen={true}>
        <QuickStats />
      </CollapsibleSection>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CollapsibleSection title="Task Status Distribution" defaultOpen={true}>
          <TaskStatusDistribution />
        </CollapsibleSection>

        <CollapsibleSection title="Priority Distribution" defaultOpen={true}>
          <PriorityDistribution />
        </CollapsibleSection>
      </div>

      <CollapsibleSection title="Tasks Completed Over Time" defaultOpen={true}>
        <TasksOverTime />
      </CollapsibleSection>

      <CollapsibleSection title="Agent Activity" defaultOpen={true}>
        <AgentActivityOverview />
      </CollapsibleSection>
    </div>
  )
}
