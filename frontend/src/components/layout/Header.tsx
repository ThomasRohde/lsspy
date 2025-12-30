import { Link } from 'react-router-dom'
import { ModeToggle } from '../ModeToggle'

export function Header() {
  return (
    <header className="h-14 bg-dark-surface border-b border-dark-border flex items-center px-4">
      <Link to="/" className="flex items-center gap-2">
        <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">LS</span>
        </div>
        <h1 className="text-lg font-semibold text-text-primary">lsspy</h1>
      </Link>
      <nav className="ml-8 flex gap-4">
        <Link
          to="/"
          className="text-text-secondary hover:text-text-primary transition-colors text-sm"
        >
          Dashboard
        </Link>
        <Link
          to="/tasks"
          className="text-text-secondary hover:text-text-primary transition-colors text-sm"
        >
          Tasks
        </Link>
        <Link
          to="/agents"
          className="text-text-secondary hover:text-text-primary transition-colors text-sm"
        >
          Agents
        </Link>
      </nav>
      <div className="ml-auto flex items-center gap-3">
        <ModeToggle />
      </div>
    </header>
  )
}
