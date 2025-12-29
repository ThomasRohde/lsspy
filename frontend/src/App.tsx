import { useState, useCallback } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/layout'
import { Dashboard, Tasks, Agents, Messages, Events } from './pages'
import { KeyboardShortcutsModal } from './components/KeyboardShortcutsModal'
import { useKeyboardShortcuts } from './hooks'
import { useWebSocket } from './hooks'

function AppContent() {
  const [showShortcuts, setShowShortcuts] = useState(false)
  const { requestSync } = useWebSocket()

  const handleShowHelp = useCallback(() => {
    setShowShortcuts(true)
  }, [])

  const handleRefresh = useCallback(() => {
    requestSync()
  }, [requestSync])

  const handleEscape = useCallback(() => {
    setShowShortcuts(false)
  }, [])

  useKeyboardShortcuts({
    onShowHelp: handleShowHelp,
    onRefresh: handleRefresh,
    onEscape: handleEscape,
  })

  return (
    <>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="tasks" element={<Tasks />} />
          <Route path="agents" element={<Agents />} />
          <Route path="messages" element={<Messages />} />
          <Route path="events" element={<Events />} />
        </Route>
      </Routes>
      <KeyboardShortcutsModal
        isOpen={showShortcuts}
        onClose={() => setShowShortcuts(false)}
      />
    </>
  )
}

function App() {
  return <AppContent />
}

export default App
