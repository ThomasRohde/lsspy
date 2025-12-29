import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

export interface Shortcut {
  key: string
  description: string
  modifiers?: ('ctrl' | 'alt' | 'shift' | 'meta')[]
}

export const SHORTCUTS: Shortcut[] = [
  { key: '?', description: 'Show keyboard shortcuts' },
  { key: '1', description: 'Go to Dashboard' },
  { key: '2', description: 'Go to Tasks' },
  { key: '3', description: 'Go to Agents' },
  { key: '4', description: 'Go to Messages' },
  { key: '5', description: 'Go to Events' },
  { key: 'g', description: 'Toggle dependency graph fullscreen' },
  { key: 'r', description: 'Refresh data', modifiers: ['ctrl'] },
  { key: 'Escape', description: 'Close modal / Clear selection' },
]

interface UseKeyboardShortcutsOptions {
  onShowHelp?: () => void
  onRefresh?: () => void
  onToggleGraph?: () => void
  onEscape?: () => void
}

export function useKeyboardShortcuts(options: UseKeyboardShortcutsOptions = {}) {
  const navigate = useNavigate()
  const { onShowHelp, onRefresh, onToggleGraph, onEscape } = options

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Ignore if typing in an input
      const target = event.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      ) {
        // Allow Escape in inputs
        if (event.key !== 'Escape') return
      }

      // Check for modifier combinations
      const isCtrl = event.ctrlKey || event.metaKey
      const isAlt = event.altKey
      // const isShift = event.shiftKey // Reserved for future use

      switch (event.key) {
        case '?':
          event.preventDefault()
          onShowHelp?.()
          break

        case '1':
          if (!isCtrl && !isAlt) {
            event.preventDefault()
            navigate('/')
          }
          break

        case '2':
          if (!isCtrl && !isAlt) {
            event.preventDefault()
            navigate('/tasks')
          }
          break

        case '3':
          if (!isCtrl && !isAlt) {
            event.preventDefault()
            navigate('/agents')
          }
          break

        case '4':
          if (!isCtrl && !isAlt) {
            event.preventDefault()
            navigate('/messages')
          }
          break

        case '5':
          if (!isCtrl && !isAlt) {
            event.preventDefault()
            navigate('/events')
          }
          break

        case 'g':
        case 'G':
          if (!isCtrl && !isAlt) {
            event.preventDefault()
            onToggleGraph?.()
          }
          break

        case 'r':
        case 'R':
          if (isCtrl) {
            event.preventDefault()
            onRefresh?.()
          }
          break

        case 'Escape':
          onEscape?.()
          break
      }
    },
    [navigate, onShowHelp, onRefresh, onToggleGraph, onEscape]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

export function formatShortcut(shortcut: Shortcut): string {
  const parts: string[] = []

  if (shortcut.modifiers?.includes('ctrl')) parts.push('Ctrl')
  if (shortcut.modifiers?.includes('alt')) parts.push('Alt')
  if (shortcut.modifiers?.includes('shift')) parts.push('Shift')
  if (shortcut.modifiers?.includes('meta')) parts.push('Cmd')

  parts.push(shortcut.key === 'Escape' ? 'Esc' : shortcut.key.toUpperCase())

  return parts.join(' + ')
}
