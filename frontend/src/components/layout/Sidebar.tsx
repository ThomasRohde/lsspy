import { Link, useLocation } from 'react-router-dom'
import clsx from 'clsx'

interface NavItem {
  label: string
  path: string
  icon: string
}

const navItems: NavItem[] = [
  { label: 'Overview', path: '/', icon: 'grid' },
  { label: 'Tasks', path: '/tasks', icon: 'check-square' },
  { label: 'Agents', path: '/agents', icon: 'users' },
  { label: 'Messages', path: '/messages', icon: 'message-square' },
  { label: 'Events', path: '/events', icon: 'activity' },
]

function NavIcon({ icon }: { icon: string }) {
  // Simple icon representations using CSS shapes
  const iconMap: Record<string, React.ReactNode> = {
    'grid': (
      <div className="grid grid-cols-2 gap-0.5 w-4 h-4">
        <div className="bg-current rounded-sm" />
        <div className="bg-current rounded-sm" />
        <div className="bg-current rounded-sm" />
        <div className="bg-current rounded-sm" />
      </div>
    ),
    'check-square': (
      <div className="w-4 h-4 border-2 border-current rounded flex items-center justify-center">
        <div className="w-2 h-1 border-b-2 border-l-2 border-current transform -rotate-45" />
      </div>
    ),
    'users': (
      <div className="w-4 h-4 flex items-center justify-center">
        <div className="flex -space-x-1">
          <div className="w-2 h-2 bg-current rounded-full" />
          <div className="w-2 h-2 bg-current rounded-full" />
        </div>
      </div>
    ),
    'message-square': (
      <div className="w-4 h-4 border-2 border-current rounded relative">
        <div className="absolute -bottom-1 left-1 w-2 h-2 bg-dark-surface border-l-2 border-b-2 border-current transform rotate-45" />
      </div>
    ),
    'activity': (
      <div className="w-4 h-4 flex items-center gap-0.5">
        <div className="w-1 h-2 bg-current" />
        <div className="w-1 h-4 bg-current" />
        <div className="w-1 h-1 bg-current" />
        <div className="w-1 h-3 bg-current" />
      </div>
    ),
  }

  return <>{iconMap[icon] || null}</>
}

export function Sidebar() {
  const location = useLocation()

  return (
    <aside className="w-56 bg-dark-surface border-r border-dark-border flex flex-col">
      <nav className="flex-1 py-4">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                    isActive
                      ? 'bg-blue-500/20 text-blue-400'
                      : 'text-text-secondary hover:bg-dark-bg-secondary hover:text-text-primary'
                  )}
                >
                  <NavIcon icon={item.icon} />
                  {item.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
      <div className="p-4 border-t border-dark-border">
        <div className="text-xs text-text-muted">
          Lodestar Dashboard v0.1.0
        </div>
      </div>
    </aside>
  )
}
