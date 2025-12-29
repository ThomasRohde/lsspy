import { AgentPanel } from '../components/AgentPanel'
import { useAgentsList } from '../stores'

export function Agents() {
  const agents = useAgentsList()
  const onlineCount = agents.filter((a) => a.status === 'online').length
  const idleCount = agents.filter((a) => a.status === 'idle').length
  const offlineCount = agents.filter((a) => a.status === 'offline').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Agents</h1>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-green-400">{onlineCount} online</span>
          <span className="text-yellow-400">{idleCount} idle</span>
          <span className="text-gray-400">{offlineCount} offline</span>
        </div>
      </div>
      <AgentPanel />
    </div>
  )
}
