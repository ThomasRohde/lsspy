import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { StatusBar } from '../StatusBar'

export function Layout() {
  return (
    <div className="h-screen bg-dark-bg text-text-primary flex flex-col">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
      <StatusBar />
    </div>
  )
}
