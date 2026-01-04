# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **BREAKING:** Updated messaging system for Lodestar 0.9.0 compatibility
  - Messages now use `read_by` array instead of `read_at` timestamp
  - Messages are task-focused only (removed agent-to-agent messaging)
  - `task_id` is now required for all messages
  - Multiple agents can mark messages as read independently
- Updated Message model API to return `readBy` (array) instead of `readAt` (timestamp)
- Updated RuntimeReader to support filtering messages by agent read status
- Updated schema documentation to reflect Lodestar 0.9.0 messaging changes

### Note

This version requires Lodestar 0.9.0 or later for full messaging support.

## [0.1.0] - 2025-12-29

### Added

- Initial release of lsspy
- Real-time visualization dashboard for Lodestar-managed repositories
- WebSocket support for live updates of tasks, agents, leases, messages, and events
- REST API endpoints for programmatic integration
  - `/api/tasks` - Task management and status
  - `/api/agents` - Agent information
  - `/api/leases` - Active lease monitoring
  - `/api/messages` - Message feed
  - `/api/events` - Event stream
  - `/api/statistics` - Repository statistics
- Interactive web dashboard built with React and TypeScript
  - Task board with status filtering
  - Agent panel showing active agents and their status
  - Lease monitor for tracking claim expirations
  - Message feed for agent communication
  - Event timeline for audit trail
  - Dependency graph visualization
  - Statistics panel with completion rates and activity metrics
- CLI command `lsspy start` with options:
  - Auto-detection of `.lodestar` directory
  - Configurable port and host
  - Optional browser auto-open
  - Configurable file polling interval
  - Debug logging support
- File watcher for automatic updates when spec.yaml or runtime.sqlite change
- Support for Python 3.12+
- Comprehensive test suite with pytest
- Type checking with mypy
- Code linting with ruff

[0.1.0]: https://github.com/ThomasRohde/lsspy/releases/tag/v0.1.0
