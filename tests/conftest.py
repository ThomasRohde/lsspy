"""Pytest configuration and fixtures."""

import sqlite3
import tempfile
from pathlib import Path
from typing import Generator

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
    """Create a runtime.sqlite database with sample data."""
    db_path = lodestar_dir / "runtime.sqlite"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE agents (
            id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT,
            capabilities TEXT,
            registeredAt TEXT,
            lastSeenAt TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE leases (
            id TEXT PRIMARY KEY,
            taskId TEXT,
            agentId TEXT,
            createdAt TEXT,
            expiresAt TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            fromAgentId TEXT,
            toAgentId TEXT,
            taskId TEXT,
            subject TEXT,
            body TEXT,
            severity TEXT,
            createdAt TEXT,
            readAt TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            actorAgentId TEXT,
            taskId TEXT,
            targetAgentId TEXT,
            payload TEXT,
            createdAt TEXT
        )
    """)
    
    # Insert sample data
    cursor.execute(
        "INSERT INTO agents VALUES (?, ?, ?, ?, ?, ?)",
        ("A001", "Agent 1", "online", "[]", "2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z")
    )
    
    cursor.execute(
        "INSERT INTO leases VALUES (?, ?, ?, ?, ?)",
        ("L001", "T001", "A001", "2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z")
    )
    
    cursor.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("M001", "A001", "A002", "T001", "Test", "Body", "info", "2025-01-01T00:00:00Z", None)
    )
    
    cursor.execute(
        "INSERT INTO events (type, actorAgentId, taskId, payload, createdAt) VALUES (?, ?, ?, ?, ?)",
        ("task.claimed", "A001", "T001", '{"key": "value"}', "2025-01-01T00:00:00Z")
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
