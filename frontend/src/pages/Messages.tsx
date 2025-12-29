import { MessageFeed } from '../components/MessageFeed'
import { useDataStore } from '../stores'

export function Messages() {
  const messages = useDataStore((state) => state.messages)
  const unreadCount = messages.filter((m) => !m.readAt).length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Messages</h1>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-gray-400">{messages.length} total</span>
          {unreadCount > 0 && (
            <span className="text-blue-400">{unreadCount} unread</span>
          )}
        </div>
      </div>
      <MessageFeed />
    </div>
  )
}
