import { TaskBoard } from '../components/TaskBoard'
import { useTasksList } from '../stores'

export function Tasks() {
  const tasks = useTasksList()
  const readyCount = tasks.filter((t) => t.status === 'ready').length
  const doneCount = tasks.filter((t) => t.status === 'done').length
  const verifiedCount = tasks.filter((t) => t.status === 'verified').length

  return (
    <div className="h-full flex flex-col">
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold">Tasks</h1>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-yellow-400">{readyCount} ready</span>
          <span className="text-green-400">{doneCount} done</span>
          <span className="text-purple-400">{verifiedCount} verified</span>
          <span className="text-gray-400">{tasks.length} total</span>
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <TaskBoard />
      </div>
    </div>
  )
}
