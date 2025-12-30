"""FastAPI server for LSSPY dashboard."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from lsspy import __version__
from lsspy.models import (
    Agent,
    Event,
    HealthResponse,
    Lease,
    Message,
    Status,
    Task,
    WSConnectedMessage,
    WSErrorMessage,
    WSUpdateMessage,
)
from lsspy.readers.runtime import RuntimeReader
from lsspy.readers.spec import SpecReader
from lsspy.watcher import LodestarWatcher

# Get the package directory
PACKAGE_DIR = Path(__file__).parent
STATIC_DIR = PACKAGE_DIR / "static"

# Global state - will be set by CLI
_lodestar_dir: Path | None = None
_runtime_reader: RuntimeReader | None = None
_spec_reader: SpecReader | None = None
_watcher: LodestarWatcher | None = None
_shutting_down: bool = False

# Valid WebSocket subscription scopes
VALID_SCOPES = {"agents", "tasks", "leases", "messages", "events", "all"}


class ConnectionManager:
    """Manage WebSocket connections and subscriptions."""

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self._connections: dict[str, WebSocket] = {}
        self._subscriptions: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection

        Returns:
            Client ID assigned to this connection
        """
        await websocket.accept()
        client_id = f"WS{uuid.uuid4().hex[:8].upper()}"

        async with self._lock:
            self._connections[client_id] = websocket
            self._subscriptions[client_id] = set()

        # Send connection acknowledgment
        msg = WSConnectedMessage(
            type="connected", client_id=client_id, subscriptions=[], timestamp=datetime.utcnow()
        )
        await websocket.send_text(msg.model_dump_json())

        return client_id

    async def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            client_id: Client ID to disconnect
        """
        async with self._lock:
            self._connections.pop(client_id, None)
            self._subscriptions.pop(client_id, None)

    async def subscribe(self, client_id: str, scopes: list[str]) -> list[str]:
        """Subscribe a client to scopes.

        Args:
            client_id: Client ID
            scopes: List of scopes to subscribe to

        Returns:
            List of current subscriptions after update
        """
        async with self._lock:
            if client_id not in self._subscriptions:
                return []

            for scope in scopes:
                if scope in VALID_SCOPES:
                    if scope == "all":
                        # Subscribe to all data scopes
                        self._subscriptions[client_id] = {
                            "agents",
                            "tasks",
                            "leases",
                            "messages",
                            "events",
                        }
                    else:
                        self._subscriptions[client_id].add(scope)

            return list(self._subscriptions[client_id])

    async def unsubscribe(self, client_id: str, scopes: list[str]) -> list[str]:
        """Unsubscribe a client from scopes.

        Args:
            client_id: Client ID
            scopes: List of scopes to unsubscribe from

        Returns:
            List of current subscriptions after update
        """
        async with self._lock:
            if client_id not in self._subscriptions:
                return []

            for scope in scopes:
                if scope == "all":
                    self._subscriptions[client_id].clear()
                else:
                    self._subscriptions[client_id].discard(scope)

            return list(self._subscriptions[client_id])

    async def get_subscriptions(self, client_id: str) -> list[str]:
        """Get current subscriptions for a client.

        Args:
            client_id: Client ID

        Returns:
            List of subscribed scopes
        """
        async with self._lock:
            return list(self._subscriptions.get(client_id, set()))

    async def broadcast(self, scope: str, data: Any) -> int:
        """Broadcast data to all clients subscribed to a scope.

        Args:
            scope: Data scope
            data: Data to broadcast

        Returns:
            Number of clients that received the message
        """
        msg = WSUpdateMessage(type="update", scope=scope, data=data, timestamp=datetime.utcnow())
        msg_json = msg.model_dump_json()

        sent_count = 0
        disconnected = []

        async with self._lock:
            for client_id, subscriptions in self._subscriptions.items():
                if scope in subscriptions:
                    websocket = self._connections.get(client_id)
                    if websocket:
                        try:
                            await websocket.send_text(msg_json)
                            sent_count += 1
                        except Exception:
                            disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)

        return sent_count

    async def broadcast_all(self) -> None:
        """Broadcast all current data to subscribed clients."""
        if not _runtime_reader or not _spec_reader or _shutting_down:
            return

        # Run blocking data gathering in a thread
        try:
            scopes_data = await asyncio.to_thread(self._gather_data_sync)
        except Exception:
            # If data gathering fails (e.g. DB locked or shutdown), just return
            return

        # Broadcast each scope
        for scope, data in scopes_data.items():
            await self.broadcast(scope, data)

    def _gather_data_sync(self) -> dict[str, Any]:
        """Gather all data for broadcast synchronously.

        This runs in a thread to avoid blocking the event loop.
        """
        if not _runtime_reader or not _spec_reader:
            return {}

        scopes_data: dict[str, Any] = {}

        # Get agents
        agents_data = _runtime_reader.get_agents()
        agents = []
        for a in agents_data:
            # Parse capabilities and session_meta
            capabilities = []
            if a.get("capabilities"):
                try:
                    capabilities = json.loads(a.get("capabilities") or "[]")
                except (json.JSONDecodeError, TypeError):
                    capabilities = (a.get("capabilities") or "").split(",")

            session_meta = None
            if a.get("session_meta"):
                try:
                    session_meta = json.loads(a.get("session_meta") or "null")
                except (json.JSONDecodeError, TypeError):
                    pass

            # Determine status based on last_seen_at (schema: 15min idle, 60min offline)
            status = "offline"
            if a.get("last_seen_at"):
                try:
                    last_seen_str = a.get("last_seen_at") or ""
                    last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                    elapsed_seconds = (
                        datetime.utcnow().replace(tzinfo=None) - last_seen.replace(tzinfo=None)
                    ).total_seconds()
                    if elapsed_seconds < 900:  # 15 minutes
                        status = "online"
                    elif elapsed_seconds < 3600:  # 60 minutes
                        status = "idle"
                except Exception:
                    pass

            agents.append(
                Agent(
                    id=a.get("agent_id", ""),
                    displayName=a.get("display_name"),
                    role=a.get("role"),
                    status=status,
                    lastSeenAt=a.get("last_seen_at"),
                    registeredAt=a.get("created_at"),
                    capabilities=capabilities,
                    sessionMeta=session_meta,
                ).model_dump(mode="json", by_alias=True)
            )
        scopes_data["agents"] = agents

        # Get tasks
        tasks = [t.model_dump(mode="json", by_alias=True) for t in _spec_reader.get_tasks_typed()]
        scopes_data["tasks"] = tasks

        # Get leases
        leases_data = _runtime_reader.get_leases(include_expired=False)
        leases = [
            Lease(
                leaseId=lease.get("lease_id", ""),
                taskId=lease.get("task_id", ""),
                agentId=lease.get("agent_id", ""),
                expiresAt=lease.get("expires_at") or datetime.utcnow(),
                ttlSeconds=900,  # Default, not in DB
                createdAt=lease.get("created_at") or datetime.utcnow(),
            ).model_dump(mode="json", by_alias=True)
            for lease in leases_data
        ]
        scopes_data["leases"] = leases

        # Get messages
        messages_data = _runtime_reader.get_messages(limit=50, unread_only=False)
        messages = []
        for m in messages_data:
            # Parse meta
            meta = {}
            if m.get("meta"):
                try:
                    meta = json.loads(m.get("meta") or "{}")
                except (json.JSONDecodeError, TypeError):
                    pass

            messages.append(
                Message(
                    id=m.get("message_id", ""),
                    createdAt=m.get("created_at") or datetime.utcnow(),
                    **{"from": m.get("from_agent_id", "")},
                    to=m.get("to_id") if m.get("to_type") == "agent" else None,
                    body=m.get("text", ""),
                    taskId=m.get("to_id") if m.get("to_type") == "task" else None,
                    subject=meta.get("subject"),
                    severity=meta.get("severity"),
                    readAt=m.get("read_at"),
                ).model_dump(mode="json", by_alias=True)
            )
        scopes_data["messages"] = messages

        # Get events
        events_data = _runtime_reader.get_events(limit=100, event_type=None)
        events = []
        for e in events_data:
            data = e.get("data", {})
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    data = {}

            events.append(
                Event(
                    id=e.get("event_id", 0),
                    createdAt=e.get("created_at") or datetime.utcnow(),
                    type=e.get("event_type", ""),
                    actorAgentId=e.get("agent_id"),
                    taskId=e.get("task_id"),
                    targetAgentId=e.get("target_agent_id"),
                    correlationId=e.get("correlation_id"),
                    payload=data,
                ).model_dump(mode="json", by_alias=True)
            )
        scopes_data["events"] = events

        return scopes_data

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)


# Global connection manager instance
connection_manager = ConnectionManager()


def set_lodestar_dir(lodestar_dir: Path) -> None:
    """Set the Lodestar directory to monitor.

    Args:
        lodestar_dir: Path to .lodestar directory
    """
    global _lodestar_dir, _runtime_reader, _spec_reader
    _lodestar_dir = lodestar_dir
    _runtime_reader = RuntimeReader(lodestar_dir / "runtime.sqlite")
    _spec_reader = SpecReader(lodestar_dir / "spec.yaml")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup/shutdown events."""
    global _watcher, _event_loop

    # Store event loop for cross-thread broadcasting
    _event_loop = asyncio.get_event_loop()

    # Start file watcher if lodestar dir is configured
    if _lodestar_dir is not None:
        _watcher = LodestarWatcher(
            _lodestar_dir,
            on_change=trigger_broadcast,
            debounce_ms=100,
            use_polling=False,
        )
        _watcher.start()

    yield

    # Signal shutdown to prevent new operations
    global _shutting_down
    _shutting_down = True

    # Shutdown: stop watcher
    if _watcher is not None:
        _watcher.stop()
        _watcher = None

    # Cancel and wait for background tasks
    if _background_tasks:
        for task in _background_tasks:
            task.cancel()

        # Wait for tasks to complete/cancel
        try:
            await asyncio.gather(*_background_tasks, return_exceptions=True)
        except Exception:
            pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LSSPY",
        description="Lodestar Visualizer Dashboard",
        version=__version__,
        lifespan=lifespan,
    )

    # CORS middleware for WebSocket and API access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files if directory exists
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/")
        async def root() -> FileResponse:
            """Serve the dashboard HTML with no-cache headers."""
            index_file = STATIC_DIR / "index.html"
            if index_file.exists():
                response = FileResponse(index_file)
                # Prevent browser caching of the HTML file
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
            return FileResponse(str(STATIC_DIR / "index.html"))

    else:

        @app.get("/")
        async def root_placeholder() -> HTMLResponse:
            """Serve placeholder HTML when static files not built."""
            return HTMLResponse(
                "<h1>LSSPY Dashboard</h1>"
                "<p>Frontend not yet built. Run frontend build process first.</p>"
            )

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(status="ok", version=__version__)

    @app.get("/api/status", response_model=Status)
    async def status() -> Status:
        """Get system status."""
        if not _lodestar_dir:
            raise HTTPException(status_code=503, detail="Lodestar directory not configured")

        runtime_db = _lodestar_dir / "runtime.sqlite"
        spec_file = _lodestar_dir / "spec.yaml"

        return Status(
            status="ok",
            version=__version__,
            lodestar_dir=str(_lodestar_dir.absolute()),
            db_exists=runtime_db.exists(),
            spec_exists=spec_file.exists(),
            uptime_seconds=None,  # TODO: Track uptime
        )

    @app.get("/api/agents", response_model=list[Agent])
    async def get_agents() -> list[Agent]:
        """Get all agents."""
        if not _runtime_reader:
            raise HTTPException(status_code=503, detail="Runtime reader not initialized")

        agents_data = _runtime_reader.get_agents()
        agents = []

        for a in agents_data:
            # Parse capabilities and session_meta
            capabilities = []
            if a.get("capabilities"):
                try:
                    capabilities = json.loads(a.get("capabilities") or "[]")
                except (json.JSONDecodeError, TypeError):
                    capabilities = (a.get("capabilities") or "").split(",")

            session_meta = None
            if a.get("session_meta"):
                try:
                    session_meta = json.loads(a.get("session_meta") or "null")
                except (json.JSONDecodeError, TypeError):
                    pass

            # Determine status based on last_seen_at (schema: 15min idle, 60min offline)
            status = "offline"
            if a.get("last_seen_at"):
                try:
                    last_seen_str = a.get("last_seen_at") or ""
                    last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                    elapsed_seconds = (
                        datetime.utcnow().replace(tzinfo=None) - last_seen.replace(tzinfo=None)
                    ).total_seconds()
                    if elapsed_seconds < 900:  # 15 minutes
                        status = "online"
                    elif elapsed_seconds < 3600:  # 60 minutes
                        status = "idle"
                except Exception:
                    pass

            agent = Agent(
                id=a.get("agent_id", ""),
                displayName=a.get("display_name"),
                role=a.get("role"),
                status=status,
                lastSeenAt=a.get("last_seen_at"),
                registeredAt=a.get("created_at"),
                capabilities=capabilities,
                sessionMeta=session_meta,
            )
            agents.append(agent)

        return agents

    @app.get("/api/agents/{agent_id}", response_model=Agent)
    async def get_agent(agent_id: str) -> Agent:
        """Get a specific agent by ID."""
        if not _runtime_reader:
            raise HTTPException(status_code=503, detail="Runtime reader not initialized")

        agents = _runtime_reader.get_agents()
        for agent_dict in agents:
            if agent_dict.get("agent_id") == agent_id:
                # Parse capabilities and session_meta
                capabilities = []
                if agent_dict.get("capabilities"):
                    try:
                        capabilities = json.loads(agent_dict.get("capabilities") or "[]")
                    except (json.JSONDecodeError, TypeError):
                        capabilities = (agent_dict.get("capabilities") or "").split(",")

                session_meta = None
                if agent_dict.get("session_meta"):
                    try:
                        session_meta = json.loads(agent_dict.get("session_meta") or "null")
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Determine status based on last_seen_at (schema: 15min idle, 60min offline)
                status = "offline"
                if agent_dict.get("last_seen_at"):
                    try:
                        last_seen_str = agent_dict.get("last_seen_at") or ""
                        last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                        elapsed_seconds = (
                            datetime.utcnow().replace(tzinfo=None) - last_seen.replace(tzinfo=None)
                        ).total_seconds()
                        if elapsed_seconds < 900:  # 15 minutes
                            status = "online"
                        elif elapsed_seconds < 3600:  # 60 minutes
                            status = "idle"
                    except Exception:
                        pass

                return Agent(
                    id=agent_dict.get("agent_id", ""),
                    displayName=agent_dict.get("display_name"),
                    role=agent_dict.get("role"),
                    status=status,
                    lastSeenAt=agent_dict.get("last_seen_at"),
                    registeredAt=agent_dict.get("created_at"),
                    capabilities=capabilities,
                    sessionMeta=session_meta,
                )

        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    @app.get("/api/tasks", response_model=list[Task])
    async def get_tasks() -> list[Task]:
        """Get all tasks."""
        if not _spec_reader:
            raise HTTPException(status_code=503, detail="Spec reader not initialized")

        return _spec_reader.get_tasks_typed()

    @app.get("/api/tasks/{task_id}", response_model=Task)
    async def get_task(task_id: str) -> Task:
        """Get a specific task by ID."""
        if not _spec_reader:
            raise HTTPException(status_code=503, detail="Spec reader not initialized")

        task_dict = _spec_reader.get_task_by_id(task_id)
        if not task_dict:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return Task(
            id=task_dict.get("id", ""),
            title=task_dict.get("title", ""),
            description=task_dict.get("description", ""),
            acceptanceCriteria=task_dict.get(
                "acceptance_criteria", task_dict.get("acceptanceCriteria", [])
            ),
            status=task_dict.get("status", "ready"),
            priority=task_dict.get("priority", 999),
            labels=task_dict.get("labels", []),
            locks=task_dict.get("locks", []),
            dependencies=task_dict.get("depends_on", task_dict.get("dependsOn", [])),
            dependents=task_dict.get("dependents", []),
            createdAt=task_dict.get("created_at", task_dict.get("createdAt")),
            updatedAt=task_dict.get("updated_at", task_dict.get("updatedAt")),
            prdSource=task_dict.get("prd_source", task_dict.get("prdSource")),
        )

    @app.get("/api/leases", response_model=list[Lease])
    async def get_leases(include_expired: bool = Query(False)) -> list[Lease]:
        """Get leases."""
        if not _runtime_reader:
            raise HTTPException(status_code=503, detail="Runtime reader not initialized")

        leases_data = _runtime_reader.get_leases(include_expired=include_expired)
        leases = []

        for lease_data in leases_data:
            lease = Lease(
                leaseId=lease_data.get("lease_id", ""),
                taskId=lease_data.get("task_id", ""),
                agentId=lease_data.get("agent_id", ""),
                expiresAt=lease_data.get("expires_at") or datetime.utcnow(),
                ttlSeconds=900,
                createdAt=lease_data.get("created_at") or datetime.utcnow(),
            )
            leases.append(lease)

        return leases

    @app.get("/api/messages", response_model=list[Message])
    async def get_messages(
        limit: int = Query(50, ge=1, le=200), unread_only: bool = Query(False)
    ) -> list[Message]:
        """Get messages with pagination."""
        if not _runtime_reader:
            raise HTTPException(status_code=503, detail="Runtime reader not initialized")

        messages_data = _runtime_reader.get_messages(limit=limit, unread_only=unread_only)
        messages = []

        for m in messages_data:
            # Parse meta
            meta = {}
            if m.get("meta"):
                try:
                    meta = json.loads(m.get("meta") or "{}")
                except (json.JSONDecodeError, TypeError):
                    pass

            message = Message(
                id=m.get("message_id", ""),
                createdAt=m.get("created_at") or datetime.utcnow(),
                **{"from": m.get("from_agent_id", "")},
                to=m.get("to_id") if m.get("to_type") == "agent" else None,
                body=m.get("text", ""),
                taskId=m.get("to_id") if m.get("to_type") == "task" else None,
                subject=meta.get("subject"),
                severity=meta.get("severity"),
                readAt=m.get("read_at"),
            )
            messages.append(message)

        return messages

    @app.get("/api/events", response_model=list[Event])
    async def get_events(
        limit: int = Query(100, ge=1, le=500), event_type: str | None = Query(None)
    ) -> list[Event]:
        """Get events with pagination."""
        if not _runtime_reader:
            raise HTTPException(status_code=503, detail="Runtime reader not initialized")

        events_data = _runtime_reader.get_events(limit=limit, event_type=event_type)
        events = []

        for e in events_data:
            # Parse payload if it's a JSON string
            payload = e.get("data", {})
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except (json.JSONDecodeError, TypeError):
                    payload = {}

            event = Event(
                id=e.get("event_id", 0),
                createdAt=e.get("created_at") or datetime.utcnow(),
                type=e.get("event_type", ""),
                actorAgentId=e.get("agent_id"),
                taskId=e.get("task_id"),
                targetAgentId=e.get("target_agent_id"),
                correlationId=e.get("correlation_id"),
                payload=payload,
            )
            events.append(event)

        return events

    @app.get("/api/graph")
    async def get_graph() -> dict[str, list[dict[str, Any]]]:
        """Get dependency graph data."""
        if not _spec_reader:
            raise HTTPException(status_code=503, detail="Spec reader not initialized")

        tasks = _spec_reader.get_tasks()

        # Build nodes and edges
        nodes = []
        edges = []

        for task in tasks:
            nodes.append(
                {
                    "id": task.get("id"),
                    "label": task.get("title", ""),
                    "status": task.get("status", "ready"),
                    "priority": task.get("priority", 999),
                    "labels": task.get("labels", []),
                }
            )

            # Create edges for dependencies
            for dep in task.get("dependsOn", []):
                edges.append({"from": dep, "to": task.get("id")})

        return {"nodes": nodes, "edges": edges}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time updates.

        Clients can send JSON messages to subscribe/unsubscribe:
        - {"type": "subscribe", "scopes": ["agents", "tasks", ...]}
        - {"type": "unsubscribe", "scopes": ["agents"]}

        Valid scopes: agents, tasks, leases, messages, events, all

        Server sends updates in format:
        - {"type": "update", "scope": "agents", "data": [...], "timestamp": "..."}
        """
        client_id = await connection_manager.connect(websocket)

        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()

                try:
                    msg = json.loads(data)
                    msg_type = msg.get("type", "")

                    if msg_type == "subscribe":
                        scopes = msg.get("scopes", [])
                        if not isinstance(scopes, list):
                            scopes = [scopes]
                        current_subs = await connection_manager.subscribe(client_id, scopes)

                        # Send acknowledgment with current subscriptions
                        response = {
                            "type": "subscribed",
                            "subscriptions": current_subs,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        await websocket.send_text(json.dumps(response))

                        # Send initial data for newly subscribed scopes
                        await _send_initial_data(websocket, scopes)

                    elif msg_type == "unsubscribe":
                        scopes = msg.get("scopes", [])
                        if not isinstance(scopes, list):
                            scopes = [scopes]
                        current_subs = await connection_manager.unsubscribe(client_id, scopes)

                        # Send acknowledgment with current subscriptions
                        response = {
                            "type": "unsubscribed",
                            "subscriptions": current_subs,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        await websocket.send_text(json.dumps(response))

                    elif msg_type == "ping":
                        # Respond to ping with pong
                        response = {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        await websocket.send_text(json.dumps(response))

                    else:
                        # Unknown message type
                        error_msg = WSErrorMessage(
                            type="error",
                            error=f"Unknown message type: {msg_type}",
                            timestamp=datetime.utcnow(),
                        )
                        await websocket.send_text(error_msg.model_dump_json())

                except json.JSONDecodeError:
                    error_msg = WSErrorMessage(
                        type="error",
                        error="Invalid JSON message",
                        timestamp=datetime.utcnow(),
                    )
                    await websocket.send_text(error_msg.model_dump_json())

        except WebSocketDisconnect:
            pass  # Normal disconnect, cleanup handled in finally
        except asyncio.CancelledError:
            pass  # Server shutdown, cleanup handled in finally
        except Exception:
            pass  # Other errors, cleanup handled in finally
        finally:
            # Always try to clean up the connection
            try:
                await connection_manager.disconnect(client_id)
            except (asyncio.CancelledError, Exception):
                # If we can't disconnect gracefully during shutdown, just remove from dicts
                connection_manager._connections.pop(client_id, None)
                connection_manager._subscriptions.pop(client_id, None)

    async def _send_initial_data(websocket: WebSocket, scopes: list[str]) -> None:
        """Send initial data for subscribed scopes.

        Args:
            websocket: WebSocket connection
            scopes: List of scopes to send data for
        """
        if not _runtime_reader or not _spec_reader:
            return

        # Expand "all" to all scopes
        if "all" in scopes:
            scopes = ["agents", "tasks", "leases", "messages", "events"]

        for scope in scopes:
            if scope not in VALID_SCOPES or scope == "all":
                continue

            data: Any = None

            if scope == "agents":
                agents_data = _runtime_reader.get_agents()
                data = []
                for a in agents_data:
                    # Parse capabilities and session_meta
                    capabilities = []
                    if a.get("capabilities"):
                        try:
                            capabilities = json.loads(a.get("capabilities") or "[]")
                        except (json.JSONDecodeError, TypeError):
                            capabilities = (a.get("capabilities") or "").split(",")

                    session_meta = None
                    if a.get("session_meta"):
                        try:
                            session_meta = json.loads(a.get("session_meta") or "null")
                        except (json.JSONDecodeError, TypeError):
                            pass

                    # Determine status based on last_seen_at (schema: 15min idle, 60min offline)
                    status = "offline"
                    if a.get("last_seen_at"):
                        try:
                            last_seen_str = a.get("last_seen_at") or ""
                            last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                            elapsed_seconds = (
                                datetime.utcnow().replace(tzinfo=None)
                                - last_seen.replace(tzinfo=None)
                            ).total_seconds()
                            if elapsed_seconds < 900:  # 15 minutes
                                status = "online"
                            elif elapsed_seconds < 3600:  # 60 minutes
                                status = "idle"
                        except Exception:
                            pass

                    data.append(
                        Agent(
                            id=a.get("agent_id", ""),
                            displayName=a.get("display_name"),
                            role=a.get("role"),
                            status=status,
                            lastSeenAt=a.get("last_seen_at"),
                            registeredAt=a.get("created_at"),
                            capabilities=capabilities,
                            sessionMeta=session_meta,
                        ).model_dump(mode="json", by_alias=True)
                    )

            elif scope == "tasks":
                data = [
                    t.model_dump(mode="json", by_alias=True) for t in _spec_reader.get_tasks_typed()
                ]

            elif scope == "leases":
                leases_data = _runtime_reader.get_leases(include_expired=False)
                data = [
                    Lease(
                        leaseId=lease.get("lease_id", ""),
                        taskId=lease.get("task_id", ""),
                        agentId=lease.get("agent_id", ""),
                        expiresAt=lease.get("expires_at") or datetime.utcnow(),
                        ttlSeconds=900,
                        createdAt=lease.get("created_at") or datetime.utcnow(),
                    ).model_dump(mode="json", by_alias=True)
                    for lease in leases_data
                ]

            elif scope == "messages":
                messages_data = _runtime_reader.get_messages(limit=50, unread_only=False)
                data = []
                for m in messages_data:
                    # Parse meta
                    meta = {}
                    if m.get("meta"):
                        try:
                            meta = json.loads(m.get("meta") or "{}")
                        except (json.JSONDecodeError, TypeError):
                            pass

                    data.append(
                        Message(
                            id=m.get("message_id", ""),
                            createdAt=m.get("created_at") or datetime.utcnow(),
                            **{"from": m.get("from_agent_id", "")},
                            to=(m.get("to_id") if m.get("to_type") == "agent" else None),
                            body=m.get("text", ""),
                            taskId=(m.get("to_id") if m.get("to_type") == "task" else None),
                            subject=meta.get("subject"),
                            severity=meta.get("severity"),
                            readAt=m.get("read_at"),
                        ).model_dump(mode="json", by_alias=True)
                    )

            elif scope == "events":
                events_data = _runtime_reader.get_events(limit=100, event_type=None)
                data = []
                for e in events_data:
                    payload = e.get("data", {})
                    if isinstance(payload, str):
                        try:
                            payload = json.loads(payload)
                        except (json.JSONDecodeError, TypeError):
                            payload = {}

                    data.append(
                        Event(
                            id=e.get("event_id", 0),
                            createdAt=e.get("created_at") or datetime.utcnow(),
                            type=e.get("event_type", ""),
                            actorAgentId=e.get("agent_id"),
                            taskId=e.get("task_id"),
                            targetAgentId=e.get("target_agent_id"),
                            correlationId=e.get("correlation_id"),
                            payload=payload,
                        ).model_dump(mode="json", by_alias=True)
                    )

            if data is not None:
                msg = WSUpdateMessage(
                    type="update", scope=scope, data=data, timestamp=datetime.utcnow()
                )
                await websocket.send_text(msg.model_dump_json())

    # SPA catch-all route - must be defined after all API routes
    # This serves index.html for any non-API, non-static path (client-side routing)
    if STATIC_DIR.exists():

        @app.get("/{full_path:path}")
        async def spa_catch_all(full_path: str) -> FileResponse:
            """Serve index.html for SPA client-side routing."""
            # Don't intercept API routes or static files
            if full_path.startswith("api/") or full_path.startswith("static/"):
                raise HTTPException(status_code=404, detail="Not Found")

            index_file = STATIC_DIR / "index.html"
            if index_file.exists():
                response = FileResponse(index_file)
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
            raise HTTPException(status_code=404, detail="Frontend not built")

    return app


# Create the app instance
app = create_app()


# Async event loop reference for cross-thread broadcasting
_event_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Set the event loop for cross-thread broadcasting.

    Args:
        loop: The asyncio event loop to use for broadcasts
    """
    global _event_loop
    _event_loop = loop


# Background tasks set for cleanup
_background_tasks: set[asyncio.Task[Any]] = set()


def trigger_broadcast() -> None:
    """Trigger a broadcast to all WebSocket clients.

    This function is safe to call from a synchronous context (like file watcher callbacks).
    It schedules the broadcast on the event loop.
    """
    if _event_loop is None or _shutting_down:
        return

    def schedule() -> None:
        task = asyncio.create_task(connection_manager.broadcast_all())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    try:
        _event_loop.call_soon_threadsafe(schedule)
    except Exception:
        pass


def get_connection_count() -> int:
    """Get the current number of WebSocket connections.

    Returns:
        Number of active WebSocket connections
    """
    return connection_manager.connection_count
