# lsspy

Real-time visualization dashboard for [Lodestar](https://github.com/lodestar-cli/lodestar)-managed repositories.

[![PyPI version](https://badge.fury.io/py/lsspy.svg)](https://badge.fury.io/py/lsspy)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

**lsspy** provides a web-based dashboard for monitoring and visualizing Lodestar-managed repositories in real-time. It offers live updates on tasks, agents, leases, messages, and events through a modern, interactive UI.

## Features

- 📊 **Real-time Monitoring**: Live updates of tasks, agents, leases, and events
- 🔌 **WebSocket Support**: Instant notifications of state changes
- 🌐 **REST API**: Full API access for programmatic integration
- 💻 **Interactive Dashboard**: Modern UI built with React and TypeScript
- 📈 **Statistics & Analytics**: Task completion rates, agent activity, and more
- 🔍 **Dependency Visualization**: Interactive graph of task dependencies

## Installation

```bash
pip install lsspy-cli
```

## Quick Start

Navigate to your Lodestar-managed project and start the dashboard:

```bash
cd /path/to/your/project
lsspy start
```

The dashboard will automatically detect the `.lodestar` directory and open in your browser at `http://localhost:8000`.

## CLI Reference

### start

Start the LSSPY dashboard server.

```bash
lsspy start [PATH] [OPTIONS]
```

**Arguments:**

- `PATH` (optional): Path to the `.lodestar` directory or parent directory. If not provided, auto-detects `.lodestar` in the current directory.

**Options:**

- `-p, --port INTEGER`: Port to run the web server on (default: 8000)
- `-h, --host TEXT`: Host address to bind to (default: 127.0.0.1)
- `--no-open`: Don't automatically open browser
- `--poll-interval INTEGER`: File polling interval in seconds (default: 1)
- `--debug`: Enable debug logging
- `-v, --version`: Show version and exit

**Examples:**

```bash
# Start with auto-detection
lsspy start

# Specify .lodestar directory
lsspy start /path/to/.lodestar

# Specify parent directory (will find .lodestar inside)
lsspy start /path/to/project

# Custom port and host
lsspy start --port 9000 --host 0.0.0.0

# Don't open browser automatically
lsspy start --no-open

# Enable debug logging
lsspy start --debug
```

## Architecture

### Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Browser / Client                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │  React UI      │  │  WebSocket     │  │  REST API      │ │
│  │  Components    │  │  Client        │  │  Client        │ │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘ │
└───────────┼──────────────────┼──────────────────┼───────────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   FastAPI Server  │
                    │   (lsspy.server)  │
                    └─────────┬─────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
    ┌───────▼────────┐ ┌──────▼──────┐ ┌───────▼────────┐
    │  RuntimeReader │ │  SpecReader │ │ ConnectionMgr  │
    │   (SQLite)     │ │   (YAML)    │ │  (WebSocket)   │
    └───────┬────────┘ └──────┬──────┘ └───────┬────────┘
            │                 │                 │
            │                 │                 │
    ┌───────▼─────────────────▼─────────────────▼────────┐
    │          .lodestar/ Directory                       │
    │  ┌──────────────────┐  ┌──────────────────┐        │
    │  │  runtime.sqlite  │  │    spec.yaml     │        │
    │  │  (runtime state) │  │  (task specs)    │        │
    │  └──────────────────┘  └──────────────────┘        │
    └─────────────────────────────────────────────────────┘
```

### Components

**Frontend (React + TypeScript + Vite)**
- Modern, responsive UI components
- Real-time updates via WebSocket
- Task board, agent panel, event timeline
- Dependency graph visualization

**Backend (FastAPI + Python)**
- RESTful API endpoints for data access
- WebSocket server for real-time notifications
- File watching for automatic updates
- SQLite and YAML readers for Lodestar data

**Data Sources**
- `runtime.sqlite`: Dynamic state (agents, leases, messages, events)
- `spec.yaml`: Static task specifications and dependencies

### Data Flow

1. **Initial Load**: Client requests dashboard data via REST API
2. **WebSocket Connection**: Client establishes WebSocket connection
3. **Subscriptions**: Client subscribes to specific data scopes (tasks, agents, etc.)
4. **File Watching**: Server monitors `.lodestar` directory for changes
5. **Change Detection**: File changes trigger data refresh
6. **Broadcast**: Server broadcasts updates to subscribed WebSocket clients
7. **UI Update**: Client receives updates and refreshes UI components

## Configuration

### Environment Variables

- `LSSPY_HOST`: Default host address (default: `127.0.0.1`)
- `LSSPY_PORT`: Default port number (default: `8000`)
- `LSSPY_DEBUG`: Enable debug mode (`true` or `false`)

### Specify Lodestar Directory

```bash
lsspy start --port 9000 --host 0.0.0.0
```

### Specify Lodestar Directory

```bash
lsspy start /path/to/.lodestar --port 8080
```

## Requirements

- Python 3.12 or higher
- A Lodestar-managed repository with `.lodestar` directory

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/ThomasRohde/lsspy.git
cd lsspy

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

### Frontend Development

The frontend is built with Vite + React + TypeScript:

```bash
cd frontend
npm install
npm run dev      # Development server
npm run build    # Production build
```

## API Endpoints

- `GET /api/health` - Server health check
- `GET /api/dashboard` - Complete dashboard data
- `GET /api/tasks` - List all tasks
- `GET /api/agents` - List all agents
- `GET /api/leases` - List active leases
- `GET /api/messages` - List recent messages
- `GET /api/events` - List recent events
- `WS /ws` - WebSocket connection for real-time updates

## WebSocket Subscriptions

Connect to `/ws` and subscribe to specific data streams:

```json
{
  "type": "subscribe",
  "scopes": ["tasks", "agents", "events"]
}
```

Available scopes: `tasks`, `agents`, `leases`, `messages`, `events`, `all`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **Homepage**: https://github.com/ThomasRohde/lsspy
- **Documentation**: https://github.com/ThomasRohde/lsspy
- **Issue Tracker**: https://github.com/ThomasRohde/lsspy/issues
- **Lodestar CLI**: https://github.com/lodestar-cli/lodestar
