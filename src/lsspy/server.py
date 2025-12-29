"""FastAPI server for LSSPY dashboard."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from lsspy import __version__
from lsspy.models import (
    Agent, Task, Lease, Message, Event, Status, HealthResponse, ErrorResponse, DashboardData,
    WSSubscribeMessage, WSUnsubscribeMessage, WSUpdateMessage, WSErrorMessage, WSConnectedMessage
)
from lsspy.readers.runtime import RuntimeReader
from lsspy.readers.spec import SpecReader

# Get the package directory
PACKAGE_DIR = Path(__file__).parent
STATIC_DIR = PACKAGE_DIR / "static"

from lsspy.watcher import LodestarWatcher

# Global state - will be set by CLI
_lodestar_dir: Path | None = None
_runtime_reader: RuntimeReader | None = None
_spec_reader: SpecReader | None = None
_watcher: LodestarWatcher | None = None

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
            client_id=client_id,
            subscriptions=[],
            timestamp=datetime.utcnow()
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
                        self._subscriptions[client_id] = {"agents", "tasks", "leases", "messages", "events"}
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
        msg = WSUpdateMessage(
            type="update",
            scope=scope,
            data=data,
            timestamp=datetime.utcnow()
        )
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
        if not _runtime_reader or not _spec_reader:
            return

        # Fetch and broadcast each scope
        scopes_data: dict[str, Any] = {}

        # Get agents
        agents_data = _runtime_reader.get_agents()
        agents = [
            Agent(
                id=a.get("id", ""),
                display_name=a.get("displayName"),
                status=a.get("status", "unknown"),
                last_seen_at=a.get("lastSeenAt"),
                registered_at=a.get("registeredAt"),
                capabilities=a.get("capabilities", "").split(",") if a.get("capabilities") else [],
                session_meta=a.get("sessionMeta")
            ).model_dump(mode="json", by_alias=True)
            for a in agents_data
        ]
        scopes_data["agents"] = agents

        # Get tasks
        tasks = [t.model_dump(mode="json", by_alias=True) for t in _spec_reader.get_tasks_typed()]
        scopes_data["tasks"] = tasks

        # Get leases
        leases_data = _runtime_reader.get_leases(include_expired=False)
        leases = [
            Lease(
                lease_id=l.get("id", ""),
                task_id=l.get("taskId", ""),
                agent_id=l.get("agentId", ""),
                expires_at=l.get("expiresAt"),
                ttl_seconds=l.get("ttlSeconds", 900),
                created_at=l.get("createdAt")
            ).model_dump(mode="json", by_alias=True)
            for l in leases_data
        ]
        scopes_data["leases"] = leases

        # Get messages
        messages_data = _runtime_reader.get_messages(limit=50, unread_only=False)
        messages = [
            Message(
                id=m.get("id", ""),
                created_at=m.get("createdAt"),
                from_agent=m.get("fromAgentId", ""),
                to_agent=m.get("toAgentId"),
                body=m.get("body", ""),
                task_id=m.get("taskId"),
                subject=m.get("subject"),
                severity=m.get("severity"),
                read_at=m.get("readAt")
            ).model_dump(mode="json", by_alias=True)
            for m in messages_data
        ]
        scopes_data["messages"] = messages

        # Get events
        events_data = _runtime_reader.get_events(limit=100, event_type=None)
        events = [
            Event(
                id=e.get("id", 0),
                created_at=e.get("createdAt"),
                type=e.get("type", ""),
                actor_agent_id=e.get("actorAgentId"),
                task_id=e.get("taskId"),
                target_agent_id=e.get("targetAgentId"),
                payload=e.get("payload", {})
            ).model_dump(mode="json", by_alias=True)
            for e in events_data
        ]
        scopes_data["events"] = events

        # Broadcast each scope
        for scope, data in scopes_data.items():
            await self.broadcast(scope, data)

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
            use_polling=False
        )
        _watcher.start()
    
    yield
    
    # Shutdown: stop watcher
    if _watcher is not None:
        _watcher.stop()
        _watcher = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LSSPY",
        description="Lodestar Visualizer Dashboard",
        version=__version__,
        lifespan=lifespan
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
        async def root() -> HTMLResponse:
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
            uptime_seconds=None  # TODO: Track uptime
        )
    
    @app.get("/api/agents", response_model=list[Agent])
    async def get_agents() -> list[Agent]:
        """Get all agents."""
        if not _runtime_reader:
            raise HTTPException(status_code=503, detail="Runtime reader not initialized")

        agents_data = _runtime_reader.get_agents()
        agents = []

        for agent_dict in agents_data:
            agent = Agent(
                id=agent_dict.get("id", ""),
                display_name=agent_dict.get("displayName"),
                status=agent_dict.get("status", "unknown"),
                last_seen_at=agent_dict.get("lastSeenAt"),
                registered_at=agent_dict.get("registeredAt"),
                capabilities=agent_dict.get("capabilities", "").split(",") if agent_dict.get("capabilities") else [],
                session_meta=agent_dict.get("sessionMeta")
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
            if agent_dict.get("id") == agent_id:
                return Agent(
                    id=agent_dict.get("id", ""),
                    display_name=agent_dict.get("displayName"),
                    status=agent_dict.get("status", "unknown"),
                    last_seen_at=agent_dict.get("lastSeenAt"),
                    registered_at=agent_dict.get("registeredAt"),
                    capabilities=agent_dict.get("capabilities", "").split(",") if agent_dict.get("capabilities") else [],
                    session_meta=agent_dict.get("sessionMeta")
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
            status=task_dict.get("status", "ready"),
            priority=task_dict.get("priority", 999),
            labels=task_dict.get("labels", []),
            locks=task_dict.get("locks", []),
            dependencies=task_dict.get("dependsOn", []),
            dependents=task_dict.get("dependents", []),
            created_at=task_dict.get("createdAt"),
            updated_at=task_dict.get("updatedAt"),
            prd_source=task_dict.get("prdSource")
        )
    
    @app.get("/api/leases", response_model=list[Lease])
    async def get_leases(include_expired: bool = Query(False)) -> list[Lease]:
        """Get leases."""
        if not _runtime_reader:
            raise HTTPException(status_code=503, detail="Runtime reader not initialized")

        leases_data = _runtime_reader.get_leases(include_expired=include_expired)
        leases = []

        for lease_dict in leases_data:
            lease = Lease(
                lease_id=lease_dict.get("id", ""),
                task_id=lease_dict.get("taskId", ""),
                agent_id=lease_dict.get("agentId", ""),
                expires_at=lease_dict.get("expiresAt"),
                ttl_seconds=lease_dict.get("ttlSeconds", 900),
                created_at=lease_dict.get("createdAt")
            )
            leases.append(lease)

        return leases
    
    @app.get("/api/messages", response_model=list[Message])
    async def get_messages(
        limit: int = Query(50, ge=1, le=200),
        unread_only: bool = Query(False)
    ) -> list[Message]:
        """Get messages with pagination."""
        if not _runtime_reader:
            raise HTTPException(status_code=503, detail="Runtime reader not initialized")

        messages_data = _runtime_reader.get_messages(limit=limit, unread_only=unread_only)
        messages = []

        for msg_dict in messages_data:
            message = Message(
                id=msg_dict.get("id", ""),
                created_at=msg_dict.get("createdAt"),
                from_agent=msg_dict.get("fromAgentId", ""),
                to_agent=msg_dict.get("toAgentId"),
                body=msg_dict.get("body", ""),
                task_id=msg_dict.get("taskId"),
                subject=msg_dict.get("subject"),
                severity=msg_dict.get("severity"),
                read_at=msg_dict.get("readAt")
            )
            messages.append(message)

        return messages

    @app.get("/api/events", response_model=list[Event])
    async def get_events(
        limit: int = Query(100, ge=1, le=500),
        event_type: str | None = Query(None)
    ) -> list[Event]:
        """Get events with pagination."""
        if not _runtime_reader:
            raise HTTPException(status_code=503, detail="Runtime reader not initialized")

        events_data = _runtime_reader.get_events(limit=limit, event_type=event_type)
        events = []

        for event_dict in events_data:
            # Parse payload if it's a JSON string
            payload = event_dict.get("payload", {})
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except (json.JSONDecodeError, TypeError):
                    payload = {}
            
            event = Event(
                id=event_dict.get("id", 0),
                created_at=event_dict.get("createdAt"),
                type=event_dict.get("type", ""),
                actor_agent_id=event_dict.get("actorAgentId"),
                task_id=event_dict.get("taskId"),
                target_agent_id=event_dict.get("targetAgentId"),
                payload=payload
            )
            events.append(event)

        return events
    
    @app.get("/api/graph")
    async def get_graph() -> dict:
        """Get dependency graph data."""
        if not _spec_reader:
            raise HTTPException(status_code=503, detail="Spec reader not initialized")
        
        tasks = _spec_reader.get_tasks()
        
        # Build nodes and edges
        nodes = []
        edges = []
        
        for task in tasks:
            nodes.append({
                "id": task.get("id"),
                "label": task.get("title", ""),
                "status": task.get("status", "ready"),
                "priority": task.get("priority", 999),
                "labels": task.get("labels", [])
            })
            
            # Create edges for dependencies
            for dep in task.get("dependsOn", []):
                edges.append({
                    "from": dep,
                    "to": task.get("id")
                })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
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
                            "timestamp": datetime.utcnow().isoformat()
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
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket.send_text(json.dumps(response))

                    elif msg_type == "ping":
                        # Respond to ping with pong
                        response = {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket.send_text(json.dumps(response))

                    else:
                        # Unknown message type
                        error_msg = WSErrorMessage(
                            error=f"Unknown message type: {msg_type}",
                            timestamp=datetime.utcnow()
                        )
                        await websocket.send_text(error_msg.model_dump_json())

                except json.JSONDecodeError:
                    error_msg = WSErrorMessage(
                        error="Invalid JSON message",
                        timestamp=datetime.utcnow()
                    )
                    await websocket.send_text(error_msg.model_dump_json())

        except WebSocketDisconnect:
            await connection_manager.disconnect(client_id)
        except Exception:
            await connection_manager.disconnect(client_id)

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
                data = [
                    Agent(
                        id=a.get("id", ""),
                        display_name=a.get("displayName"),
                        status=a.get("status", "unknown"),
                        last_seen_at=a.get("lastSeenAt"),
                        registered_at=a.get("registeredAt"),
                        capabilities=a.get("capabilities", "").split(",") if a.get("capabilities") else [],
                        session_meta=a.get("sessionMeta")
                    ).model_dump(mode="json", by_alias=True)
                    for a in agents_data
                ]

            elif scope == "tasks":
                data = [t.model_dump(mode="json", by_alias=True) for t in _spec_reader.get_tasks_typed()]

            elif scope == "leases":
                leases_data = _runtime_reader.get_leases(include_expired=False)
                data = [
                    Lease(
                        lease_id=l.get("id", ""),
                        task_id=l.get("taskId", ""),
                        agent_id=l.get("agentId", ""),
                        expires_at=l.get("expiresAt"),
                        ttl_seconds=l.get("ttlSeconds", 900),
                        created_at=l.get("createdAt")
                    ).model_dump(mode="json", by_alias=True)
                    for l in leases_data
                ]

            elif scope == "messages":
                messages_data = _runtime_reader.get_messages(limit=50, unread_only=False)
                data = [
                    Message(
                        id=m.get("id", ""),
                        created_at=m.get("createdAt"),
                        from_agent=m.get("fromAgentId", ""),
                        to_agent=m.get("toAgentId"),
                        body=m.get("body", ""),
                        task_id=m.get("taskId"),
                        subject=m.get("subject"),
                        severity=m.get("severity"),
                        read_at=m.get("readAt")
                    ).model_dump(mode="json", by_alias=True)
                    for m in messages_data
                ]

            elif scope == "events":
                events_data = _runtime_reader.get_events(limit=100, event_type=None)
                data = [
                    Event(
                        id=e.get("id", 0),
                        created_at=e.get("createdAt"),
                        type=e.get("type", ""),
                        actor_agent_id=e.get("actorAgentId"),
                        task_id=e.get("taskId"),
                        target_agent_id=e.get("targetAgentId"),
                        payload=e.get("payload", {})
                    ).model_dump(mode="json", by_alias=True)
                    for e in events_data
                ]

            if data is not None:
                msg = WSUpdateMessage(
                    type="update",
                    scope=scope,
                    data=data,
                    timestamp=datetime.utcnow()
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


def trigger_broadcast() -> None:
    """Trigger a broadcast to all WebSocket clients.

    This function is safe to call from a synchronous context (like file watcher callbacks).
    It schedules the broadcast on the event loop.
    """
    if _event_loop is None:
        return

    try:
        _event_loop.call_soon_threadsafe(
            lambda: asyncio.create_task(connection_manager.broadcast_all())
        )
    except Exception:
        pass


def get_connection_count() -> int:
    """Get the current number of WebSocket connections.

    Returns:
        Number of active WebSocket connections
    """
    return connection_manager.connection_count
