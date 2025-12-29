import { SHORTCUTS, formatShortcut } from '../hooks/useKeyboardShortcuts'

interface KeyboardShortcutsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-dark-surface border border-dark-border rounded-xl shadow-2xl max-w-md w-full max-h-[80vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-dark-border">
            <h2 className="text-lg font-semibold text-gray-100">Keyboard Shortcuts</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white text-xl leading-none"
            >
              ×
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[60vh]">
            <div className="space-y-3">
              {SHORTCUTS.map((shortcut) => (
                <div
                  key={shortcut.key}
                  className="flex items-center justify-between py-2"
                >
                  <span className="text-gray-300">{shortcut.description}</span>
                  <kbd className="px-2 py-1 bg-dark-bg border border-dark-border rounded text-sm font-mono text-gray-400">
                    {formatShortcut(shortcut)}
                  </kbd>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-dark-border bg-dark-bg/50">
            <p className="text-sm text-gray-500 text-center">
              Press <kbd className="px-1.5 py-0.5 bg-dark-border rounded text-xs">?</kbd> anytime to show this help
            </p>
          </div>
        </div>
      </div>
    </>
  )
}
