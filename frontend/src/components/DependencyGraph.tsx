import { useCallback, useMemo, useState } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  NodeProps,
  Handle,
  Position,
  ReactFlowProvider,
  useReactFlow,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useTasksList, useLeasesList } from '../stores'
import type { Task } from '../types'
import clsx from 'clsx'

// Node status colors per PRD
const statusStyles: Record<string, { bg: string; border: string; text: string; pulse?: boolean; doubleBorder?: boolean }> = {
  todo: { bg: 'bg-gray-600', border: 'border-gray-500', text: 'text-gray-200' },
  ready: { bg: 'bg-blue-600', border: 'border-blue-400', text: 'text-blue-100' },
  in_progress: { bg: 'bg-yellow-600', border: 'border-yellow-400', text: 'text-yellow-100', pulse: true },
  done: { bg: 'bg-green-600', border: 'border-green-400', text: 'text-green-100' },
  verified: { bg: 'bg-green-600', border: 'border-green-300', text: 'text-green-100', doubleBorder: true },
  blocked: { bg: 'bg-red-600', border: 'border-red-400', text: 'text-red-100' },
}

interface TaskNodeData {
  task: Task
  isInProgress: boolean
  isBlocked: boolean
  onClick: (taskId: string) => void
}

function TaskNode({ data }: NodeProps<TaskNodeData>) {
  const { task, isInProgress, isBlocked } = data

  let displayStatus: string
  if (task.status === 'blocked') displayStatus = 'blocked'  // Explicit blocked status from schema
  else if (isBlocked) displayStatus = 'blocked'  // Computed blocked (unverified deps)
  else if (isInProgress) displayStatus = 'in_progress'
  else if (task.status === 'todo') displayStatus = 'todo'
  else if (task.status === 'ready') displayStatus = 'ready'
  else if (task.status === 'done') displayStatus = 'done'
  else if (task.status === 'verified') displayStatus = 'verified'
  else displayStatus = 'todo'

  const style = statusStyles[displayStatus] || statusStyles.todo

  return (
    <div
      className={clsx(
        'px-3 py-2 rounded-lg border-2 min-w-[140px] max-w-[180px] cursor-pointer transition-transform hover:scale-105',
        style.bg,
        style.border,
        style.pulse && 'animate-pulse',
        style.doubleBorder && 'ring-2 ring-green-400 ring-offset-2 ring-offset-dark-bg'
      )}
      onClick={() => data.onClick(task.id)}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />
      <div className="text-xs font-mono text-gray-300 mb-1">{task.id}</div>
      <div className={clsx('text-sm font-medium line-clamp-2', style.text)}>
        {task.title}
      </div>
      <div className="flex items-center justify-between mt-1">
        <span className="text-xs text-gray-300">P{task.priority}</span>
        <span className="text-xs capitalize text-gray-300">{displayStatus.replace('_', ' ')}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  )
}

const nodeTypes = {
  task: TaskNode,
}

// Simple DAG layout algorithm
function layoutNodes(tasks: Task[], leaseTaskIds: Set<string>): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = []
  const edges: Edge[] = []

  // Build adjacency list and compute levels
  const taskMap = new Map<string, Task>()
  tasks.forEach((t) => taskMap.set(t.id, t))

  // Compute levels using topological ordering
  const levels = new Map<string, number>()
  const visited = new Set<string>()

  function computeLevel(taskId: string): number {
    if (levels.has(taskId)) return levels.get(taskId)!
    if (visited.has(taskId)) return 0 // Handle cycles

    visited.add(taskId)
    const task = taskMap.get(taskId)
    if (!task || task.dependencies.length === 0) {
      levels.set(taskId, 0)
      return 0
    }

    let maxDepLevel = 0
    for (const depId of task.dependencies) {
      if (taskMap.has(depId)) {
        maxDepLevel = Math.max(maxDepLevel, computeLevel(depId) + 1)
      }
    }

    levels.set(taskId, maxDepLevel)
    return maxDepLevel
  }

  tasks.forEach((t) => computeLevel(t.id))

  // Group tasks by level
  const levelGroups = new Map<number, Task[]>()
  tasks.forEach((task) => {
    const level = levels.get(task.id) || 0
    if (!levelGroups.has(level)) levelGroups.set(level, [])
    levelGroups.get(level)!.push(task)
  })

  // Position nodes
  const nodeSpacingX = 220
  const nodeSpacingY = 120
  const sortedLevels = Array.from(levelGroups.keys()).sort((a, b) => a - b)

  sortedLevels.forEach((level) => {
    const levelTasks = levelGroups.get(level)!
    levelTasks.sort((a, b) => a.priority - b.priority) // Sort by priority within level

    const startX = -(levelTasks.length - 1) * nodeSpacingX / 2

    levelTasks.forEach((task, index) => {
      const isInProgress = leaseTaskIds.has(task.id)

      // Check if blocked (has unverified dependencies)
      const isBlocked = task.status === 'ready' && task.dependencies.some((depId) => {
        const depTask = taskMap.get(depId)
        return depTask && depTask.status !== 'verified'
      })

      nodes.push({
        id: task.id,
        type: 'task',
        position: { x: startX + index * nodeSpacingX, y: level * nodeSpacingY },
        data: {
          task,
          isInProgress,
          isBlocked,
          onClick: () => { },
        },
      })

      // Create edges from dependencies
      task.dependencies.forEach((depId) => {
        if (taskMap.has(depId)) {
          edges.push({
            id: `${depId}-${task.id}`,
            source: depId,
            target: task.id,
            animated: leaseTaskIds.has(task.id),
            style: { stroke: '#6b7280' },
          })
        }
      })
    })
  })

  return { nodes, edges }
}

function DependencyGraphInner({
  onNodeClick,
}: {
  onNodeClick?: (taskId: string) => void
}) {
  const tasks = useTasksList()
  const leases = useLeasesList()
  const { fitView } = useReactFlow()

  const leaseTaskIds = useMemo(
    () => new Set(leases.map((l) => l.taskId)),
    [leases]
  )

  const { nodes, edges } = useMemo(
    () => {
      const layout = layoutNodes(tasks, leaseTaskIds)
      // Add click handlers to nodes inline
      const nodesWithHandlers = layout.nodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          onClick: onNodeClick || (() => { }),
        },
      }))
      return { nodes: nodesWithHandlers, edges: layout.edges }
    },
    [tasks, leaseTaskIds, onNodeClick]
  )

  const handleFitView = useCallback(() => {
    fitView({ padding: 0.2 })
  }, [fitView])

  if (tasks.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        No tasks to display
      </div>
    )
  }

  return (
    <div className="h-full w-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2}
        className="bg-dark-bg"
      >
        <Background color="#334155" gap={20} />
        <Controls
          className="!bg-dark-surface !border-dark-border !shadow-lg"
          showInteractive={false}
        />
      </ReactFlow>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-dark-surface border border-dark-border rounded-lg p-3 text-xs">
        <div className="font-medium text-gray-300 mb-2">Status Legend</div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-gray-600 border border-gray-500" />
            <span className="text-gray-400">TODO</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-blue-600 border border-blue-400" />
            <span className="text-gray-400">Ready</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-yellow-600 border border-yellow-400" />
            <span className="text-gray-400">In Progress</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-green-600 border border-green-400" />
            <span className="text-gray-400">Done</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-green-600 border-2 border-green-300 ring-1 ring-green-400" />
            <span className="text-gray-400">Verified</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-red-600 border border-red-400" />
            <span className="text-gray-400">Blocked</span>
          </div>
        </div>
      </div>

      {/* Fit View Button */}
      <button
        onClick={handleFitView}
        className="absolute top-4 right-4 px-3 py-1.5 bg-dark-surface border border-dark-border rounded-lg text-sm text-gray-300 hover:text-white hover:border-gray-500 transition-colors"
      >
        Fit View
      </button>
    </div>
  )
}

export function DependencyGraph({
  onNodeClick,
  fullScreen = false,
}: {
  onNodeClick?: (taskId: string) => void
  fullScreen?: boolean
}) {
  const [isFullScreen, setIsFullScreen] = useState(fullScreen)

  if (isFullScreen) {
    return (
      <div className="fixed inset-0 z-50 bg-dark-bg">
        <button
          onClick={() => setIsFullScreen(false)}
          className="absolute top-4 left-4 z-10 px-3 py-1.5 bg-dark-surface border border-dark-border rounded-lg text-sm text-gray-300 hover:text-white"
        >
          Exit Full Screen
        </button>
        <ReactFlowProvider>
          <DependencyGraphInner onNodeClick={onNodeClick} />
        </ReactFlowProvider>
      </div>
    )
  }

  return (
    <div className="h-full relative">
      <button
        onClick={() => setIsFullScreen(true)}
        className="absolute top-4 left-4 z-10 px-3 py-1.5 bg-dark-surface border border-dark-border rounded-lg text-sm text-gray-300 hover:text-white"
      >
        Full Screen
      </button>
      <ReactFlowProvider>
        <DependencyGraphInner onNodeClick={onNodeClick} />
      </ReactFlowProvider>
    </div>
  )
}
