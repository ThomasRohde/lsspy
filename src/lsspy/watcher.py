"""File system watcher for Lodestar files."""

import time
from collections.abc import Callable
from pathlib import Path
from threading import Lock, Thread
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver


class DebouncedEventHandler(FileSystemEventHandler):
    """File system event handler with debouncing."""

    def __init__(
        self, lodestar_dir: Path, on_change: Callable[[], None], debounce_ms: int = 100
    ) -> None:
        """Initialize the handler.

        Args:
            lodestar_dir: Path to .lodestar directory
            on_change: Callback to invoke when files change
            debounce_ms: Debounce period in milliseconds
        """
        self.lodestar_dir = lodestar_dir
        self.on_change = on_change
        self.debounce_seconds = debounce_ms / 1000.0
        self.runtime_db = lodestar_dir / "runtime.sqlite"
        self.runtime_db_wal = lodestar_dir / "runtime.sqlite-wal"
        self.runtime_db_shm = lodestar_dir / "runtime.sqlite-shm"
        self.spec_file = lodestar_dir / "spec.yaml"

        self._last_trigger = 0.0
        self._pending = False
        self._lock = Lock()
        self._debounce_thread: Thread | None = None

    def _should_trigger(self, path: Path) -> bool:
        """Check if the path should trigger a callback.

        Args:
            path: File path that changed

        Returns:
            True if callback should be triggered
        """
        return path in (
            self.runtime_db,
            self.runtime_db_wal,
            self.runtime_db_shm,
            self.spec_file,
        )

    def _trigger_debounced(self) -> None:
        """Trigger callback after debounce period."""
        time.sleep(self.debounce_seconds)

        with self._lock:
            if self._pending:
                current_time = time.time()
                if current_time - self._last_trigger >= self.debounce_seconds:
                    self._last_trigger = current_time
                    self._pending = False
                    try:
                        self.on_change()
                    except Exception:
                        pass

    def _schedule_trigger(self) -> None:
        """Schedule a debounced trigger."""
        with self._lock:
            self._pending = True

            # Cancel existing debounce thread if running
            if self._debounce_thread and self._debounce_thread.is_alive():
                return

            # Start new debounce thread
            self._debounce_thread = Thread(target=self._trigger_debounced, daemon=True)
            self._debounce_thread.start()

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        path = Path(str(event.src_path))
        if self._should_trigger(path):
            self._schedule_trigger()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        path = Path(str(event.src_path))
        if self._should_trigger(path):
            self._schedule_trigger()


class LodestarWatcher:
    """Watch .lodestar directory for changes."""

    def __init__(
        self,
        lodestar_dir: Path,
        on_change: Callable[[], None],
        debounce_ms: int = 100,
        use_polling: bool = False,
    ) -> None:
        """Initialize the watcher.

        Args:
            lodestar_dir: Path to .lodestar directory
            on_change: Callback to invoke when files change
            debounce_ms: Debounce period in milliseconds
            use_polling: Force polling observer (fallback mode)
        """
        self.lodestar_dir = lodestar_dir
        self.on_change = on_change
        self.debounce_ms = debounce_ms
        self.use_polling = use_polling
        self._observer: Any = None
        self._event_handler: DebouncedEventHandler | None = None

    def start(self) -> None:
        """Start watching the directory."""
        if self._observer is not None:
            return  # Already started

        self._event_handler = DebouncedEventHandler(
            self.lodestar_dir, self.on_change, self.debounce_ms
        )

        # Try native observer first, fall back to polling
        try:
            if self.use_polling:
                raise Exception("Polling mode forced")

            self._observer = Observer()
            self._observer.schedule(self._event_handler, str(self.lodestar_dir), recursive=False)
            self._observer.start()
        except Exception:
            # Fall back to polling observer
            self._observer = PollingObserver()
            self._observer.schedule(self._event_handler, str(self.lodestar_dir), recursive=False)
            self._observer.start()

    def stop(self) -> None:
        """Stop watching the directory."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None
            self._event_handler = None

    def is_alive(self) -> bool:
        """Check if watcher is running.

        Returns:
            True if watcher is active
        """
        return self._observer is not None and self._observer.is_alive()


def start_watcher(
    lodestar_dir: Path,
    on_change: Callable[[], None],
    debounce_ms: int = 100,
    use_polling: bool = False,
) -> LodestarWatcher:
    """Start watching the .lodestar directory.

    Args:
        lodestar_dir: Path to .lodestar directory
        on_change: Callback to invoke when files change
        debounce_ms: Debounce period in milliseconds
        use_polling: Force polling observer (fallback mode)

    Returns:
        LodestarWatcher instance (must be stopped by caller)
    """
    watcher = LodestarWatcher(lodestar_dir, on_change, debounce_ms, use_polling)
    watcher.start()
    return watcher
