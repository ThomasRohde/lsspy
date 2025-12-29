import { EventTimeline } from '../components/EventTimeline'
import { useRecentEvents } from '../stores'

export function Events() {
  const events = useRecentEvents(1000)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Events</h1>
        <span className="text-sm text-gray-400">
          {events.length} events in history
        </span>
      </div>
      <EventTimeline limit={500} />
    </div>
  )
}
