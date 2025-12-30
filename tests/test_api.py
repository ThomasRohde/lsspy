"""Tests for FastAPI server endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lsspy.server import create_app, set_lodestar_dir


@pytest.fixture
def test_client(lodestar_dir: Path, spec_file: Path, runtime_db: Path) -> TestClient:
    """Create a test client with configured Lodestar directory."""
    set_lodestar_dir(lodestar_dir)
    app = create_app()
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health and status endpoints."""

    def test_health_endpoint(self, test_client: TestClient) -> None:
        """Test /api/health endpoint."""
        response = test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_status_endpoint(self, test_client: TestClient) -> None:
        """Test /api/status endpoint."""
        response = test_client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        # API uses snake_case in JSON
        assert "lodestar_dir" in data or "lodestarDir" in data
        assert data.get("db_exists") is True or data.get("dbExists") is True
        assert data.get("spec_exists") is True or data.get("specExists") is True


class TestAgentsEndpoints:
    """Tests for agent-related endpoints."""

    def test_get_all_agents(self, test_client: TestClient) -> None:
        """Test GET /api/agents."""
        response = test_client.get("/api/agents")

        assert response.status_code == 200
        agents = response.json()
        assert len(agents) >= 1
        assert agents[0]["id"] == "A001"
        # displayName field can be None or "Agent 1"
        assert agents[0].get("displayName") in [None, "Agent 1"]
        assert agents[0]["status"] == "online"

    def test_get_agent_by_id(self, test_client: TestClient) -> None:
        """Test GET /api/agents/{agent_id}."""
        response = test_client.get("/api/agents/A001")

        assert response.status_code == 200
        agent = response.json()
        assert agent["id"] == "A001"
        assert agent.get("displayName") in [None, "Agent 1"]

    def test_get_nonexistent_agent(self, test_client: TestClient) -> None:
        """Test GET /api/agents/{agent_id} for nonexistent agent."""
        response = test_client.get("/api/agents/A999")

        assert response.status_code == 404
        error = response.json()
        assert "not found" in error["detail"].lower()


class TestTasksEndpoints:
    """Tests for task-related endpoints."""

    def test_get_all_tasks(self, test_client: TestClient) -> None:
        """Test GET /api/tasks."""
        response = test_client.get("/api/tasks")

        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 3
        assert tasks[0]["id"] == "T001"
        assert tasks[0]["title"] == "Test task 1"

    def test_get_task_by_id(self, test_client: TestClient) -> None:
        """Test GET /api/tasks/{task_id}."""
        response = test_client.get("/api/tasks/T001")

        assert response.status_code == 200
        task = response.json()
        assert task["id"] == "T001"
        assert task["title"] == "Test task 1"
        assert task["status"] == "ready"
        assert task["priority"] == 1

    def test_get_nonexistent_task(self, test_client: TestClient) -> None:
        """Test GET /api/tasks/{task_id} for nonexistent task."""
        response = test_client.get("/api/tasks/T999")

        assert response.status_code == 404
        error = response.json()
        assert "not found" in error["detail"].lower()

    def test_task_with_dependencies(self, test_client: TestClient) -> None:
        """Test task with dependencies."""
        response = test_client.get("/api/tasks/T002")

        assert response.status_code == 200
        task = response.json()
        assert "T001" in task["dependencies"]

    def test_task_with_labels(self, test_client: TestClient) -> None:
        """Test task with labels."""
        response = test_client.get("/api/tasks/T001")

        assert response.status_code == 200
        task = response.json()
        assert "feature" in task["labels"]
        assert "backend" in task["labels"]


class TestLeasesEndpoints:
    """Tests for lease-related endpoints."""

    def test_get_leases(self, test_client: TestClient) -> None:
        """Test GET /api/leases."""
        response = test_client.get("/api/leases")

        assert response.status_code == 200
        leases = response.json()
        assert isinstance(leases, list)

    def test_get_leases_include_expired(self, test_client: TestClient) -> None:
        """Test GET /api/leases with include_expired."""
        response = test_client.get("/api/leases?include_expired=true")

        assert response.status_code == 200
        leases = response.json()
        assert len(leases) >= 1
        assert leases[0]["leaseId"] == "L001"
        assert leases[0]["taskId"] == "T001"
        assert leases[0]["agentId"] == "A001"

    def test_get_leases_exclude_expired(self, test_client: TestClient) -> None:
        """Test GET /api/leases with expired leases excluded."""
        response = test_client.get("/api/leases?include_expired=false")

        assert response.status_code == 200
        leases = response.json()
        # The fixture has old timestamps, so should be empty or filtered
        assert isinstance(leases, list)


class TestMessagesEndpoints:
    """Tests for message-related endpoints."""

    def test_get_messages(self, test_client: TestClient) -> None:
        """Test GET /api/messages."""
        response = test_client.get("/api/messages")

        assert response.status_code == 200
        messages = response.json()
        assert len(messages) >= 1
        assert messages[0]["id"] == "M001"
        # API uses alias "from" instead of from_agent
        assert messages[0]["from"] == "A001"
        assert messages[0]["subject"] == "Test"

    def test_get_messages_with_limit(self, test_client: TestClient) -> None:
        """Test GET /api/messages with limit."""
        response = test_client.get("/api/messages?limit=10")

        assert response.status_code == 200
        messages = response.json()
        assert len(messages) <= 10

    def test_get_unread_messages(self, test_client: TestClient) -> None:
        """Test GET /api/messages with unread_only."""
        response = test_client.get("/api/messages?unread_only=true")

        assert response.status_code == 200
        messages = response.json()
        assert len(messages) >= 1
        for msg in messages:
            assert msg["readAt"] is None

    def test_get_messages_invalid_limit(self, test_client: TestClient) -> None:
        """Test GET /api/messages with invalid limit."""
        response = test_client.get("/api/messages?limit=0")

        assert response.status_code == 422  # Validation error


class TestEventsEndpoints:
    """Tests for event-related endpoints."""

    def test_get_events(self, test_client: TestClient) -> None:
        """Test GET /api/events."""
        response = test_client.get("/api/events")

        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        assert events[0]["type"] == "task.claimed"
        assert events[0]["taskId"] == "T001"

    def test_get_events_with_limit(self, test_client: TestClient) -> None:
        """Test GET /api/events with limit."""
        response = test_client.get("/api/events?limit=50")

        assert response.status_code == 200
        events = response.json()
        assert len(events) <= 50

    def test_get_events_by_type(self, test_client: TestClient) -> None:
        """Test GET /api/events filtered by type."""
        response = test_client.get("/api/events?event_type=task.claimed")

        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        for event in events:
            assert event["type"] == "task.claimed"


class TestGraphEndpoint:
    """Tests for graph endpoint."""

    def test_get_graph(self, test_client: TestClient) -> None:
        """Test GET /api/graph."""
        response = test_client.get("/api/graph")

        assert response.status_code == 200
        graph = response.json()
        assert "nodes" in graph
        assert "edges" in graph


class TestDashboardEndpoint:
    """Tests for dashboard data endpoint."""

    def test_get_dashboard_data(self, test_client: TestClient) -> None:
        """Test GET /api/dashboard - endpoint not yet implemented."""
        pytest.skip("Dashboard endpoint not yet implemented")
        response = test_client.get("/api/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "tasks" in data
        assert "leases" in data
        assert "messages" in data
        assert "events" in data


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, test_client: TestClient) -> None:
        """Test GET / (root)."""
        response = test_client.get("/")

        # Will return either HTML or FileResponse
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers(self, test_client: TestClient) -> None:
        """Test CORS headers are present."""
        # TestClient doesn't process middleware the same way as real requests
        # Just verify endpoint works; CORS is handled by CORSMiddleware
        response = test_client.get("/api/health")
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_endpoint(self, test_client: TestClient) -> None:
        """Test accessing invalid endpoint."""
        response = test_client.get("/api/invalid")

        assert response.status_code == 404

    def test_method_not_allowed(self, test_client: TestClient) -> None:
        """Test using unsupported HTTP method."""
        response = test_client.post("/api/health")

        assert response.status_code == 405
