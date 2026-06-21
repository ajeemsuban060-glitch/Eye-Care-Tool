"""SQLite database connection and schema initialization."""

import sqlite3
import os
from typing import Optional

from core.config import Config, default_config

class Database:
    """
    Singleton database manager for the eye care tool.
    """

    _instance: Optional["Database"] = None

    def __new__(cls, config: Optional[Config] = None) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[Config] = None) -> None:
        if self._initialized:
            return
        self._config = config or default_config
        self.db_path = self._config.db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
        self._initialized = True

    def _init_db(self) -> None:
        """Create database file and tables if they don't exist."""
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        # Create tables as per schema (Section 6)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS breaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id),
                triggered_at TEXT NOT NULL,
                trigger_reason TEXT CHECK(trigger_reason IN ('time', 'fatigue')),
                active_seconds_before_break INTEGER,
                fatigue_score REAL,
                user_response TEXT CHECK(user_response IN ('taken', 'skipped', 'snoozed'))
            )
        """)
        self._conn.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the SQLite connection."""
        if self._conn is None:
            self._init_db()
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None