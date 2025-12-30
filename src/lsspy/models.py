"""Pydantic models for API responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CamelCaseModel(BaseModel):
    """Base model that serializes to camelCase for frontend compatibility."""

    model_config = ConfigDict(
        populate_by_name=True,
    )


class Agent(CamelCaseModel):
    """Agent information."""

    id: str = Field(..., description="Agent ID")
    display_name: str | None = Field(None, alias="displayName", description="Display name")
    role: str | None = Field(None, description="Agent role (e.g., 'code-review')")
    status: str = Field(..., description="Agent status (online/idle/offline)")
    last_seen_at: datetime | None = Field(
        None, alias="lastSeenAt", description="Last seen timestamp"
    )
    registered_at: datetime | None = Field(
        None, alias="registeredAt", description="Registration timestamp"
    )
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    session_meta: dict[str, str] | None = Field(
        None, alias="sessionMeta", description="Session metadata"
    )


class Task(CamelCaseModel):
    """Task information."""

    id: str = Field(..., description="Task ID")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        alias="acceptanceCriteria",
        description="Acceptance criteria",
    )
    status: str = Field(..., description="Task status (todo/ready/blocked/done/verified/deleted)")
    priority: int = Field(..., description="Task priority")
    labels: list[str] = Field(default_factory=list, description="Task labels")
    locks: list[str] = Field(default_factory=list, description="Task locks")
    dependencies: list[str] = Field(default_factory=list, description="Dependencies")
    dependents: list[str] = Field(default_factory=list, description="Dependent tasks")
    created_at: datetime | None = Field(None, alias="createdAt", description="Creation timestamp")
    updated_at: datetime | None = Field(None, alias="updatedAt", description="Update timestamp")
    prd_source: str | None = Field(None, alias="prdSource", description="PRD source file")


class Lease(CamelCaseModel):
    """Lease information."""

    lease_id: str = Field(..., alias="leaseId", description="Lease ID")
    task_id: str = Field(..., alias="taskId", description="Task ID")
    agent_id: str = Field(..., alias="agentId", description="Agent ID")
    expires_at: datetime = Field(..., alias="expiresAt", description="Expiration timestamp")
    ttl_seconds: int = Field(900, alias="ttlSeconds", description="TTL in seconds")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")


class Message(CamelCaseModel):
    """Message information."""

    id: str = Field(..., description="Message ID")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    from_agent: str = Field(..., alias="from", description="Sender agent ID")
    to_agent: str | None = Field(None, alias="to", description="Recipient agent ID")
    body: str = Field(..., description="Message body")
    task_id: str | None = Field(None, alias="taskId", description="Associated task ID")
    subject: str | None = Field(None, description="Message subject")
    severity: str | None = Field(None, description="Message severity")
    read_at: datetime | None = Field(None, alias="readAt", description="Read timestamp")


class Event(CamelCaseModel):
    """Event information."""

    id: int = Field(..., description="Event ID")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    type: str = Field(..., description="Event type")
    actor_agent_id: str | None = Field(None, alias="actorAgentId", description="Actor agent ID")
    task_id: str | None = Field(None, alias="taskId", description="Associated task ID")
    target_agent_id: str | None = Field(None, alias="targetAgentId", description="Target agent ID")
    correlation_id: str | None = Field(
        None, alias="correlationId", description="Correlation ID for related events"
    )
    payload: dict[str, Any] = Field(default_factory=dict, description="Event payload")


class DashboardData(BaseModel):
    """Complete dashboard data."""

    agents: list[Agent] = Field(default_factory=list, description="All agents")
    tasks: list[Task] = Field(default_factory=list, description="All tasks")
    leases: list[Lease] = Field(default_factory=list, description="Active leases")
    messages: list[Message] = Field(default_factory=list, description="Recent messages")
    events: list[Event] = Field(default_factory=list, description="Recent events")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data timestamp")


class Status(BaseModel):
    """System status information."""

    status: str = Field(..., description="Overall status (ok/error)")
    version: str = Field(..., description="Application version")
    lodestar_dir: str | None = Field(None, description="Monitored .lodestar directory")
    db_exists: bool = Field(False, description="Whether runtime.sqlite exists")
    spec_exists: bool = Field(False, description="Whether spec.yaml exists")
    uptime_seconds: float | None = Field(None, description="Server uptime in seconds")


class HealthResponse(BaseModel):
    """Health check API response."""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")


class ErrorResponse(BaseModel):
    """Error API response."""

    error: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")


# WebSocket message models


class WSSubscribeMessage(BaseModel):
    """WebSocket subscription request."""

    type: str = Field("subscribe", description="Message type")
    scopes: list[str] = Field(
        default_factory=list,
        description="Scopes to subscribe to (agents, tasks, leases, messages, events, all)",
    )


class WSUnsubscribeMessage(BaseModel):
    """WebSocket unsubscribe request."""

    type: str = Field("unsubscribe", description="Message type")
    scopes: list[str] = Field(default_factory=list, description="Scopes to unsubscribe from")


class WSUpdateMessage(BaseModel):
    """WebSocket update message sent to clients."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    type: str = Field("update", description="Message type")
    scope: str = Field(..., description="Data scope (agents, tasks, leases, messages, events)")
    data: Any = Field(..., description="Updated data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")


class WSErrorMessage(BaseModel):
    """WebSocket error message."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    type: str = Field("error", description="Message type")
    error: str = Field(..., description="Error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class WSConnectedMessage(BaseModel):
    """WebSocket connection acknowledgment."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    type: str = Field("connected", description="Message type")
    client_id: str = Field(..., description="Assigned client ID")
    subscriptions: list[str] = Field(default_factory=list, description="Current subscriptions")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Connection timestamp")
