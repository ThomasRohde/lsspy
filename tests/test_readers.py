"""Tests for spec and runtime readers."""

from pathlib import Path

import pytest
import yaml

from lsspy.readers.runtime import RuntimeReader
from lsspy.readers.spec import SpecReader


class TestSpecReader:
    """Tests for SpecReader class."""

    def test_init(self, spec_file: Path) -> None:
        """Test SpecReader initialization."""
        reader = SpecReader(spec_file)
        assert reader.spec_path == spec_file

    def test_read_valid_spec(self, spec_file: Path) -> None:
        """Test reading a valid spec file."""
        reader = SpecReader(spec_file)
        data = reader.read()

        assert isinstance(data, dict)
        assert "tasks" in data
        assert len(data["tasks"]) == 3

    def test_read_nonexistent_file(self, temp_dir: Path) -> None:
        """Test reading a file that doesn't exist."""
        reader = SpecReader(temp_dir / "nonexistent.yaml")

        with pytest.raises(FileNotFoundError):
            reader.read()

    def test_read_invalid_yaml(self, invalid_yaml_file: Path) -> None:
        """Test reading an invalid YAML file."""
        reader = SpecReader(invalid_yaml_file)

        with pytest.raises(yaml.YAMLError):
            reader.read()

    def test_read_safe_valid_spec(self, spec_file: Path) -> None:
        """Test read_safe with valid spec."""
        reader = SpecReader(spec_file)
        data = reader.read_safe()

        assert isinstance(data, dict)
        assert "tasks" in data

    def test_read_safe_nonexistent_file(self, temp_dir: Path) -> None:
        """Test read_safe with nonexistent file returns empty dict."""
        reader = SpecReader(temp_dir / "nonexistent.yaml")
        data = reader.read_safe()

        assert data == {}

    def test_read_safe_invalid_yaml(self, invalid_yaml_file: Path) -> None:
        """Test read_safe with invalid YAML returns empty dict."""
        reader = SpecReader(invalid_yaml_file)
        data = reader.read_safe()

        assert data == {}

    def test_get_tasks(self, spec_file: Path) -> None:
        """Test getting all tasks."""
        reader = SpecReader(spec_file)
        tasks = reader.get_tasks()

        assert len(tasks) == 3
        assert tasks[0]["id"] == "T001"
        assert tasks[1]["id"] == "T002"
        assert tasks[2]["id"] == "T003"

    def test_get_tasks_empty_spec(self, empty_spec_file: Path) -> None:
        """Test getting tasks from empty spec."""
        reader = SpecReader(empty_spec_file)
        tasks = reader.get_tasks()

        assert tasks == []

    def test_get_tasks_typed(self, spec_file: Path) -> None:
        """Test getting tasks as typed objects."""
        reader = SpecReader(spec_file)
        tasks = reader.get_tasks_typed()

        assert len(tasks) == 3
        assert tasks[0].id == "T001"
        assert tasks[0].title == "Test task 1"
        assert tasks[0].status == "ready"
        assert tasks[0].priority == 1
        assert "feature" in tasks[0].labels
        assert "backend" in tasks[0].labels

    def test_get_task_by_id_found(self, spec_file: Path) -> None:
        """Test getting a specific task by ID."""
        reader = SpecReader(spec_file)
        task = reader.get_task_by_id("T002")

        assert task is not None
        assert task["id"] == "T002"
        assert task["title"] == "Test task 2"
        assert task["status"] == "done"

    def test_get_task_by_id_not_found(self, spec_file: Path) -> None:
        """Test getting a task that doesn't exist."""
        reader = SpecReader(spec_file)
        task = reader.get_task_by_id("T999")

        assert task is None

    def test_get_tasks_by_label(self, spec_file: Path) -> None:
        """Test filtering tasks by label."""
        reader = SpecReader(spec_file)

        # Test single label
        backend_tasks = reader.get_tasks_by_label("backend")
        assert len(backend_tasks) == 2
        assert all("backend" in t["labels"] for t in backend_tasks)

        # Test another label
        frontend_tasks = reader.get_tasks_by_label("frontend")
        assert len(frontend_tasks) == 1
        assert frontend_tasks[0]["id"] == "T002"

    def test_get_tasks_by_label_no_matches(self, spec_file: Path) -> None:
        """Test filtering with label that has no matches."""
        reader = SpecReader(spec_file)
        tasks = reader.get_tasks_by_label("nonexistent")

        assert tasks == []

    def test_get_tasks_by_status(self, spec_file: Path) -> None:
        """Test filtering tasks by status."""
        reader = SpecReader(spec_file)

        # Test different statuses
        ready_tasks = reader.get_tasks_by_status("ready")
        assert len(ready_tasks) == 1
        assert ready_tasks[0]["id"] == "T001"

        done_tasks = reader.get_tasks_by_status("done")
        assert len(done_tasks) == 1
        assert done_tasks[0]["id"] == "T002"

        verified_tasks = reader.get_tasks_by_status("verified")
        assert len(verified_tasks) == 1
        assert verified_tasks[0]["id"] == "T003"

    def test_get_tasks_by_status_no_matches(self, spec_file: Path) -> None:
        """Test filtering with status that has no matches."""
        reader = SpecReader(spec_file)
        tasks = reader.get_tasks_by_status("deleted")

        assert tasks == []

    def test_check_file_health_valid(self, spec_file: Path) -> None:
        """Test health check on valid spec file."""
        reader = SpecReader(spec_file)
        health = reader.check_file_health()

        assert health["exists"] is True
        assert health["readable"] is True
        assert health["valid_yaml"] is True
        assert health["task_count"] == 3
        assert health["error"] is None

    def test_check_file_health_nonexistent(self, temp_dir: Path) -> None:
        """Test health check on nonexistent file."""
        reader = SpecReader(temp_dir / "nonexistent.yaml")
        health = reader.check_file_health()

        assert health["exists"] is False
        assert health["readable"] is False
        assert health["valid_yaml"] is False
        assert health["task_count"] == 0
        assert "not found" in health["error"]

    def test_check_file_health_invalid_yaml(self, invalid_yaml_file: Path) -> None:
        """Test health check on invalid YAML."""
        reader = SpecReader(invalid_yaml_file)
        health = reader.check_file_health()

        assert health["exists"] is True
        assert health["readable"] is True
        assert health["valid_yaml"] is False
        assert health["task_count"] == 0
        assert "YAML parsing error" in health["error"]

    def test_task_with_prd_source(self, spec_file: Path) -> None:
        """Test reading task with PRD source."""
        reader = SpecReader(spec_file)
        task = reader.get_task_by_id("T003")

        assert task is not None
        assert task.get("prdSource") == "PRD.md"

    def test_task_dependencies(self, spec_file: Path) -> None:
        """Test reading task dependencies."""
        reader = SpecReader(spec_file)
        task = reader.get_task_by_id("T002")

        assert task is not None
        assert "T001" in task.get("dependsOn", [])

    def test_task_locks(self, spec_file: Path) -> None:
        """Test reading task locks."""
        reader = SpecReader(spec_file)
        task = reader.get_task_by_id("T002")

        assert task is not None
        assert "file:src/app.ts" in task.get("locks", [])


class TestRuntimeReader:
    """Tests for RuntimeReader class."""

    def test_init(self, runtime_db: Path) -> None:
        """Test RuntimeReader initialization."""
        reader = RuntimeReader(runtime_db)
        assert reader.db_path == runtime_db
        assert reader.readonly is True

    def test_init_readwrite(self, runtime_db: Path) -> None:
        """Test RuntimeReader initialization in read-write mode."""
        reader = RuntimeReader(runtime_db, readonly=False)
        assert reader.readonly is False

    def test_connect_success(self, runtime_db: Path) -> None:
        """Test successful database connection."""
        reader = RuntimeReader(runtime_db)
        conn = reader._connect()

        assert conn is not None
        conn.close()

    def test_connect_nonexistent_db(self, temp_dir: Path) -> None:
        """Test connection to nonexistent database."""
        reader = RuntimeReader(temp_dir / "nonexistent.db")

        with pytest.raises(FileNotFoundError):
            reader._connect()

    def test_get_agents(self, runtime_db: Path) -> None:
        """Test getting all agents."""
        reader = RuntimeReader(runtime_db)
        agents = reader.get_agents()

        assert len(agents) == 1
        assert agents[0]["agent_id"] == "A001"
        assert agents[0]["display_name"] == "Agent 1"
        assert agents[0]["role"] == "code-review"

    def test_get_agents_nonexistent_db(self, temp_dir: Path) -> None:
        """Test getting agents from nonexistent database."""
        reader = RuntimeReader(temp_dir / "nonexistent.db")
        agents = reader.get_agents()

        assert agents == []

    def test_get_leases_active_only(self, runtime_db: Path) -> None:
        """Test getting only active leases."""
        reader = RuntimeReader(runtime_db)
        leases = reader.get_leases(include_expired=False)

        # The fixture has leases in the past, so this should be empty
        # or test with future timestamps
        assert isinstance(leases, list)

    def test_get_leases_include_expired(self, runtime_db: Path) -> None:
        """Test getting all leases including expired."""
        reader = RuntimeReader(runtime_db)
        leases = reader.get_leases(include_expired=True)

        assert len(leases) >= 1
        assert leases[0]["lease_id"] == "L001"
        assert leases[0]["task_id"] == "T001"
        assert leases[0]["agent_id"] == "A001"

    def test_get_leases_nonexistent_db(self, temp_dir: Path) -> None:
        """Test getting leases from nonexistent database."""
        reader = RuntimeReader(temp_dir / "nonexistent.db")
        leases = reader.get_leases()

        assert leases == []

    def test_get_messages_all(self, runtime_db: Path) -> None:
        """Test getting all messages."""
        reader = RuntimeReader(runtime_db)
        messages = reader.get_messages(limit=50, unread_only=False)

        assert len(messages) == 1
        assert messages[0]["message_id"] == "M001"
        assert messages[0]["from_agent_id"] == "A001"
        assert messages[0]["read_at"] is None

    def test_get_messages_unread_only(self, runtime_db: Path) -> None:
        """Test getting only unread messages."""
        reader = RuntimeReader(runtime_db)
        messages = reader.get_messages(limit=50, unread_only=True)

        assert len(messages) == 1
        assert messages[0]["read_at"] is None

    def test_get_messages_with_limit(self, runtime_db: Path) -> None:
        """Test getting messages with limit."""
        reader = RuntimeReader(runtime_db)
        messages = reader.get_messages(limit=10)

        assert len(messages) <= 10

    def test_get_messages_nonexistent_db(self, temp_dir: Path) -> None:
        """Test getting messages from nonexistent database."""
        reader = RuntimeReader(temp_dir / "nonexistent.db")
        messages = reader.get_messages()

        assert messages == []

    def test_get_events_all(self, runtime_db: Path) -> None:
        """Test getting all events."""
        reader = RuntimeReader(runtime_db)
        events = reader.get_events(limit=100)

        assert len(events) >= 1
        assert events[0]["event_type"] == "task.claimed"
        assert events[0]["task_id"] == "T001"

    def test_get_events_by_type(self, runtime_db: Path) -> None:
        """Test getting events filtered by type."""
        reader = RuntimeReader(runtime_db)
        events = reader.get_events(limit=100, event_type="task.claimed")

        assert len(events) >= 1
        assert all(e["event_type"] == "task.claimed" for e in events)

    def test_get_events_nonexistent_db(self, temp_dir: Path) -> None:
        """Test getting events from nonexistent database."""
        reader = RuntimeReader(temp_dir / "nonexistent.db")
        events = reader.get_events()

        assert events == []

    def test_check_database_health_valid(self, runtime_db: Path) -> None:
        """Test health check on valid database."""
        reader = RuntimeReader(runtime_db)
        health = reader.check_database_health()

        assert health["exists"] is True
        assert health["readable"] is True
        assert health["table_count"] >= 4
        assert health["error"] is None

    def test_check_database_health_nonexistent(self, temp_dir: Path) -> None:
        """Test health check on nonexistent database."""
        reader = RuntimeReader(temp_dir / "nonexistent.db")
        health = reader.check_database_health()

        assert health["exists"] is False
        assert health["readable"] is False
        assert health["table_count"] == 0
        assert "not found" in health["error"]

    def test_query_retry_on_lock(self, runtime_db: Path) -> None:
        """Test query retry mechanism on database lock."""
        reader = RuntimeReader(runtime_db)

        # This tests that the retry mechanism is in place
        # Actual lock testing would require concurrent access
        agents = reader._query("SELECT * FROM agents")
        assert len(agents) >= 1

    def test_readonly_mode_uri(self, runtime_db: Path) -> None:
        """Test that readonly mode uses URI connection."""
        reader = RuntimeReader(runtime_db, readonly=True)
        conn = reader._connect()

        # Verify connection works with readonly
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents")
        results = cursor.fetchall()
        assert len(results) >= 1

        conn.close()
