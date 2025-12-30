"""Tests for file system watcher."""

import time
from pathlib import Path
from unittest.mock import Mock

from lsspy.watcher import DebouncedEventHandler, LodestarWatcher


class TestDebouncedEventHandler:
    """Tests for DebouncedEventHandler class."""

    def test_init(self, lodestar_dir: Path) -> None:
        """Test DebouncedEventHandler initialization."""
        callback = Mock()
        handler = DebouncedEventHandler(lodestar_dir, callback, debounce_ms=100)

        assert handler.lodestar_dir == lodestar_dir
        assert handler.on_change == callback
        assert handler.debounce_seconds == 0.1

    def test_should_trigger_runtime_db(self, lodestar_dir: Path) -> None:
        """Test that runtime.sqlite changes trigger callback."""
        callback = Mock()
        handler = DebouncedEventHandler(lodestar_dir, callback)

        runtime_db = lodestar_dir / "runtime.sqlite"
        assert handler._should_trigger(runtime_db) is True

    def test_should_trigger_runtime_wal(self, lodestar_dir: Path) -> None:
        """Test that runtime.sqlite-wal changes trigger callback."""
        callback = Mock()
        handler = DebouncedEventHandler(lodestar_dir, callback)

        wal_file = lodestar_dir / "runtime.sqlite-wal"
        assert handler._should_trigger(wal_file) is True

    def test_should_trigger_spec_file(self, lodestar_dir: Path) -> None:
        """Test that spec.yaml changes trigger callback."""
        callback = Mock()
        handler = DebouncedEventHandler(lodestar_dir, callback)

        spec_file = lodestar_dir / "spec.yaml"
        assert handler._should_trigger(spec_file) is True

    def test_should_not_trigger_other_files(self, lodestar_dir: Path) -> None:
        """Test that other files don't trigger callback."""
        callback = Mock()
        handler = DebouncedEventHandler(lodestar_dir, callback)

        other_file = lodestar_dir / "other.txt"
        assert handler._should_trigger(other_file) is False

    def test_debouncing(self, lodestar_dir: Path) -> None:
        """Test that callback is debounced."""
        callback = Mock()
        handler = DebouncedEventHandler(lodestar_dir, callback, debounce_ms=50)

        # Create mock events
        from watchdog.events import FileModifiedEvent

        # Trigger multiple events rapidly
        event1 = FileModifiedEvent(str(lodestar_dir / "spec.yaml"))
        event2 = FileModifiedEvent(str(lodestar_dir / "spec.yaml"))
        event3 = FileModifiedEvent(str(lodestar_dir / "spec.yaml"))

        handler.on_modified(event1)
        handler.on_modified(event2)
        handler.on_modified(event3)

        # Wait for debounce
        time.sleep(0.15)

        # Callback should be called once despite multiple events
        assert callback.call_count == 1

    def test_on_modified_directory_ignored(self, lodestar_dir: Path) -> None:
        """Test that directory modification events are ignored."""
        callback = Mock()
        handler = DebouncedEventHandler(lodestar_dir, callback)

        from watchdog.events import FileModifiedEvent

        event = FileModifiedEvent(str(lodestar_dir))
        event.is_directory = True

        handler.on_modified(event)
        time.sleep(0.1)

        callback.assert_not_called()

    def test_on_created(self, lodestar_dir: Path) -> None:
        """Test file creation events."""
        callback = Mock()
        handler = DebouncedEventHandler(lodestar_dir, callback, debounce_ms=50)

        from watchdog.events import FileCreatedEvent

        event = FileCreatedEvent(str(lodestar_dir / "spec.yaml"))
        handler.on_created(event)

        time.sleep(0.1)
        callback.assert_called_once()

    def test_callback_exception_handled(self, lodestar_dir: Path) -> None:
        """Test that exceptions in callback are handled."""
        callback = Mock(side_effect=Exception("Test error"))
        handler = DebouncedEventHandler(lodestar_dir, callback, debounce_ms=50)

        from watchdog.events import FileModifiedEvent

        event = FileModifiedEvent(str(lodestar_dir / "spec.yaml"))

        # Should not raise exception
        handler.on_modified(event)
        time.sleep(0.1)


class TestLodestarWatcher:
    """Tests for LodestarWatcher class."""

    def test_init(self, lodestar_dir: Path) -> None:
        """Test LodestarWatcher initialization."""
        callback = Mock()
        watcher = LodestarWatcher(lodestar_dir, callback)

        assert watcher.lodestar_dir == lodestar_dir
        assert watcher.on_change == callback
        assert watcher._observer is None

    def test_start_stop(self, lodestar_dir: Path) -> None:
        """Test starting and stopping the watcher."""
        callback = Mock()
        watcher = LodestarWatcher(lodestar_dir, callback)

        watcher.start()
        assert watcher._observer is not None
        assert watcher.is_alive() is True

        watcher.stop()
        assert watcher._observer is None

    def test_context_manager(self, lodestar_dir: Path) -> None:
        """Test using watcher with start/stop."""
        callback = Mock()
        watcher = LodestarWatcher(lodestar_dir, callback)

        watcher.start()
        assert watcher.is_alive() is True

        watcher.stop()
        assert watcher._observer is None

    def test_file_change_triggers_callback(self, lodestar_dir: Path, spec_file: Path) -> None:
        """Test that file changes trigger callback."""
        callback = Mock()
        watcher = LodestarWatcher(lodestar_dir, callback, debounce_ms=50)

        watcher.start()

        # Modify the spec file
        with open(spec_file, "a") as f:
            f.write("\n# Modified")

        # Wait for event processing and debounce
        time.sleep(0.2)

        watcher.stop()

        # Callback should have been called
        assert callback.call_count >= 1

    def test_use_polling_observer(self, lodestar_dir: Path) -> None:
        """Test using polling observer."""
        callback = Mock()
        watcher = LodestarWatcher(lodestar_dir, callback, use_polling=True)

        watcher.start()
        assert watcher._observer is not None

        watcher.stop()

    def test_start_twice_idempotent(self, lodestar_dir: Path) -> None:
        """Test that calling start twice is safe."""
        callback = Mock()
        watcher = LodestarWatcher(lodestar_dir, callback)

        watcher.start()
        first_observer = watcher._observer

        watcher.start()
        second_observer = watcher._observer

        # Should not create a new observer
        assert first_observer == second_observer

        watcher.stop()

    def test_stop_without_start(self, lodestar_dir: Path) -> None:
        """Test that stopping without starting is safe."""
        callback = Mock()
        watcher = LodestarWatcher(lodestar_dir, callback)

        # Should not raise exception
        watcher.stop()
        assert watcher._observer is None

    def test_multiple_file_changes_debounced(self, lodestar_dir: Path, spec_file: Path) -> None:
        """Test that multiple rapid changes are debounced."""
        callback = Mock()
        watcher = LodestarWatcher(lodestar_dir, callback, debounce_ms=100)

        watcher.start()

        # Make multiple rapid changes
        for i in range(5):
            with open(spec_file, "a") as f:
                f.write(f"\n# Change {i}")
            time.sleep(0.01)

        # Wait for debounce
        time.sleep(0.2)

        watcher.stop()

        # Should be called fewer times than changes made
        assert callback.call_count < 5
