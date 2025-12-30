"""Pytest configuration and fixtures."""

import sqlite3
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def lodestar_dir(temp_dir: Path) -> Path:
    """Create a .lodestar directory structure."""
    lodestar = temp_dir / ".lodestar"
    lodestar.mkdir()
    return lodestar


@pytest.fixture
def spec_file(lodestar_dir: Path) -> Path:
    """Create a spec.yaml file with sample tasks."""
    spec_path = lodestar_dir / "spec.yaml"
    spec_data = {
        "tasks": {
            "T001": {
                "title": "Test task 1",
                "description": "Description 1",
                "status": "ready",
                "priority": 1,
                "labels": ["feature", "backend"],
                "locks": [],
                "dependsOn": [],
                "createdAt": "2025-01-01T00:00:00Z",
            },
            "T002": {
                "title": "Test task 2",
                "description": "Description 2",
                "status": "done",
                "priority": 2,
                "labels": ["frontend"],
                "locks": ["file:src/app.ts"],
                "dependsOn": ["T001"],
                "createdAt": "2025-01-01T00:00:00Z",
            },
            "T003": {
                "title": "Test task 3",
                "description": "Description 3",
                "status": "verified",
                "priority": 3,
                "labels": ["backend", "testing"],
                "locks": [],
                "dependsOn": [],
                "prdSource": "PRD.md",
                "createdAt": "2025-01-01T00:00:00Z",
            },
        }
    }
    with open(spec_path, "w") as f:
        yaml.dump(spec_data, f)
    return spec_path


@pytest.fixture
def runtime_db(lodestar_dir: Path) -> Path:
    """Create a runtime.sqlite database with sample data matching schema.md."""
    db_path = lodestar_dir / "runtime.sqlite"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tables matching schema.md
    cursor.execute(
        """
        CREATE TABLE agents (
            agent_id TEXT PRIMARY KEY,
            display_name TEXT DEFAULT '',
            role TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            capabilities TEXT DEFAULT '[]',
            session_meta TEXT DEFAULT '{}'
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE leases (
            lease_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE messages (
            message_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            from_agent_id TEXT NOT NULL,
            to_type TEXT NOT NULL,
            to_id TEXT NOT NULL,
            text TEXT NOT NULL,
            meta TEXT DEFAULT '{}',
            read_at TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            agent_id TEXT,
            task_id TEXT,
            target_agent_id TEXT,
            correlation_id TEXT,
            data TEXT DEFAULT '{}'
        )
    """
    )

    # Insert sample data matching schema.md format
    # Use a recent timestamp for last_seen_at so agent appears online
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    recent = (now - timedelta(minutes=5)).isoformat() + "Z"

    cursor.execute(
        "INSERT INTO agents VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("A001", "Agent 1", "code-review", "2025-01-01T00:00:00Z", recent, "[]", "{}"),
    )

    cursor.execute(
        "INSERT INTO leases VALUES (?, ?, ?, ?, ?)",
        ("L001", "T001", "A001", "2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z"),
    )

    cursor.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "M001",
            "2025-01-01T00:00:00Z",
            "A001",
            "agent",
            "A002",
            "Body",
            '{"subject": "Test", "severity": "info"}',
            None,
        ),
    )

    cursor.execute(
        (
            "INSERT INTO events (created_at, event_type, agent_id, task_id, data) "
            "VALUES (?, ?, ?, ?, ?)"
        ),
        ("2025-01-01T00:00:00Z", "task.claimed", "A001", "T001", '{"key": "value"}'),
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def empty_spec_file(lodestar_dir: Path) -> Path:
    """Create an empty spec.yaml file."""
    spec_path = lodestar_dir / "spec.yaml"
    spec_path.write_text("")
    return spec_path


@pytest.fixture
def invalid_yaml_file(lodestar_dir: Path) -> Path:
    """Create an invalid YAML file."""
    spec_path = lodestar_dir / "spec.yaml"
    spec_path.write_text("invalid: yaml: content: [\n")
    return spec_path
