"""SQLite runtime database reader."""

import sqlite3
import time
from pathlib import Path
from typing import Any


class RuntimeReader:
    """Read data from runtime.sqlite."""

    def __init__(self, db_path: Path, readonly: bool = True, timeout: float = 5.0) -> None:
        """Initialize the reader.

        Args:
            db_path: Path to runtime.sqlite file
            readonly: Open in read-only mode (compatible with WAL)
            timeout: Connection timeout in seconds
        """
        self.db_path = db_path
        self.readonly = readonly
        self.timeout = timeout

    def _connect(self) -> sqlite3.Connection:
        """Create a database connection.

        Returns:
            SQLite connection

        Raises:
            FileNotFoundError: If database file doesn't exist
            sqlite3.Error: If connection fails
        """
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        uri = f"file:{self.db_path}?mode=ro" if self.readonly else str(self.db_path)
        conn = sqlite3.connect(uri, timeout=self.timeout, uri=self.readonly)
        conn.row_factory = sqlite3.Row
        return conn

    def _query(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ) -> list[dict[str, Any]]:
        """Execute a query and return results as dictionaries.

        Args:
            sql: SQL query string
            params: Query parameters
            max_retries: Maximum retry attempts on database lock
            retry_delay: Delay between retries in seconds

        Returns:
            List of row dictionaries

        Raises:
            sqlite3.Error: If query fails after retries
        """
        last_error = None
        for attempt in range(max_retries):
            conn = None
            try:
                conn = self._connect()
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return rows
            except sqlite3.OperationalError as e:
                last_error = e
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise
            except Exception:
                if conn:
                    conn.close()
                raise

        if last_error:
            raise last_error
        return []

    def get_agents(self) -> list[dict[str, Any]]:
        """Get all agents.

        Returns:
            List of agent dictionaries
        """
        try:
            return self._query("SELECT * FROM agents ORDER BY last_seen_at DESC")
        except FileNotFoundError:
            return []
        except sqlite3.Error as e:
            print(f"Error in get_agents: {e}")
            return []

    def get_leases(self, include_expired: bool = False) -> list[dict[str, Any]]:
        """Get leases.

        Args:
            include_expired: Include expired leases

        Returns:
            List of lease dictionaries
        """
        try:
            if include_expired:
                sql = "SELECT * FROM leases ORDER BY expires_at DESC"
            else:
                sql = "SELECT * FROM leases WHERE expires_at > datetime('now') ORDER BY expires_at"
            return self._query(sql)
        except FileNotFoundError:
            return []
        except sqlite3.Error:
            return []

    def get_messages(self, limit: int = 50, unread_only: bool = False) -> list[dict[str, Any]]:
        """Get recent messages.

        Args:
            limit: Maximum number of messages
            unread_only: Only return unread messages

        Returns:
            List of message dictionaries
        """
        try:
            if unread_only:
                sql = (
                    "SELECT * FROM messages WHERE read_at IS NULL ORDER BY created_at DESC LIMIT ?"
                )
            else:
                sql = "SELECT * FROM messages ORDER BY created_at DESC LIMIT ?"
            return self._query(sql, (limit,))
        except FileNotFoundError:
            return []
        except sqlite3.Error:
            return []

    def get_events(self, limit: int = 100, event_type: str | None = None) -> list[dict[str, Any]]:
        """Get recent events.

        Args:
            limit: Maximum number of events
            event_type: Filter by event type

        Returns:
            List of event dictionaries
        """
        try:
            if event_type:
                sql = "SELECT * FROM events WHERE event_type = ? ORDER BY event_id DESC LIMIT ?"
                params: tuple[str, int] | tuple[int] = (event_type, limit)
            else:
                sql = "SELECT * FROM events ORDER BY event_id DESC LIMIT ?"
                params = (limit,)
            return self._query(sql, params)
        except FileNotFoundError:
            return []
        except sqlite3.Error:
            return []

    def check_database_health(self) -> dict[str, Any]:
        """Check database health and accessibility.

        Returns:
            Health status dictionary
        """
        health: dict[str, Any] = {
            "exists": self.db_path.exists(),
            "readable": False,
            "wal_mode": False,
            "table_count": 0,
            "error": None,
        }

        if not health["exists"]:
            health["error"] = "Database file not found"
            return health

        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Check if database is readable
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            health["readable"] = True
            health["table_count"] = len(tables)

            # Check WAL mode
            cursor.execute("PRAGMA journal_mode")
            mode_result = cursor.fetchone()
            mode = mode_result[0] if mode_result else None
            health["wal_mode"] = str(mode).lower() == "wal" if mode else False

            conn.close()
        except Exception as e:
            health["error"] = str(e)

        return health
