# lsspy - Agent Coordination

This repository uses [Lodestar](https://github.com/lodestar-cli/lodestar) for multi-agent coordination.

## MCP Tools (Preferred)

When connected via MCP, use the `lodestar_*` tools directly. MCP is the preferred method for agents.

### Quick Start

```
lodestar_agent_join(name="Your Name")     # Register, SAVE the agentId
lodestar_task_next()                       # Find available work
lodestar_task_claim(task_id="F001", agent_id="YOUR_ID")
```

### Agent Workflow

```
1. JOIN      lodestar_agent_join()         -> Get your agentId
2. FIND      lodestar_task_next()          -> Get claimable tasks
3. CLAIM     lodestar_task_claim()         -> Create 15-min lease
4. CONTEXT   lodestar_task_context()       -> Get PRD context
5. WORK      (implement the task)
6. DONE      lodestar_task_done()          -> Mark complete
7. VERIFY    lodestar_task_verify()        -> Unblock dependents
```

### MCP Tool Reference

| Category | Tool | Purpose |
|----------|------|---------|
| **Repo** | `lodestar_repo_status` | Get project status, task counts, next actions |
| **Agent** | `lodestar_agent_join` | Register as agent (returns agentId) |
| | `lodestar_agent_heartbeat` | Update presence (call every 5 min) |
| | `lodestar_agent_leave` | Mark offline gracefully |
| | `lodestar_agent_list` | List all registered agents |
| **Task Query** | `lodestar_task_next` | Get claimable tasks (dependency-aware) |
| | `lodestar_task_list` | List tasks with filtering |
| | `lodestar_task_get` | Get full task details |
| | `lodestar_task_context` | Get PRD context for a task |
| **Task Mutation** | `lodestar_task_claim` | Claim task (15-min lease) |
| | `lodestar_task_release` | Release claim (if blocked) |
| | `lodestar_task_done` | Mark task complete |
| | `lodestar_task_verify` | Verify task (unblocks deps) |
| **Message** | `lodestar_message_send` | Send to agent or task thread |
| | `lodestar_message_list` | Get inbox messages |
| | `lodestar_message_ack` | Mark messages as read |
| **Events** | `lodestar_events_pull` | Pull event stream |

### Handoff Pattern

When blocked or ending session before completion:

```
lodestar_task_release(task_id="F001", agent_id="YOUR_ID", reason="Blocked on API approval")
lodestar_message_send(task_id="F001", from_agent_id="YOUR_ID", body="Progress: 60% complete. Tests passing.")
```

## CLI Commands (No MCP Equivalent)

These operations require CLI:

| Command | Purpose |
|---------|---------|
| `lodestar init` | Initialize repository |
| `lodestar doctor` | Health check |
| `lodestar task create` | Create new tasks |
| `lodestar task update` | Update task fields |
| `lodestar task delete` | Delete tasks (--cascade for deps) |
| `lodestar task renew` | Extend lease duration |
| `lodestar task graph` | Export dependency graph |
| `lodestar export snapshot` | Export full state |

### Creating Tasks (CLI Only)

```bash
lodestar task create \
    --id "F001" \
    --title "Add authentication" \
    --description "WHAT: Implement OAuth2. WHERE: src/auth/. ACCEPT: Tests pass." \
    --depends-on "F000" \
    --label feature \
    --priority 2
```

### Task with PRD References (CLI Only)

```bash
lodestar task create \
    --title "Implement caching" \
    --prd-source "PRD.md" \
    --prd-ref "#caching-requirements"
```

## Files

| File | Purpose | Git |
|------|---------|-----|
| `.lodestar/spec.yaml` | Task definitions | Commit |
| `.lodestar/runtime.sqlite` | Agent/lease state | Gitignored |

## Help

```bash
lodestar <command> --help     # CLI options
lodestar <command> --explain  # What it does
```
