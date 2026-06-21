#!/usr/bin/env python3
"""Entry point for the 20-20-20 Eye Care Tool (Phase 1)."""

import logging
import time
import signal
import sys
from datetime import datetime

from core.config import default_config
from core.activity_monitor import ActivityMonitor
from core.scheduler import Scheduler
from notify.desktop_notifier import DesktopNotifier
from storage.db import Database
from storage.models import Session

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class EyeCareApp:
    """
    Main application that wires together all components.
    """

    def __init__(self) -> None:
        self.config = default_config
        self.db = Database(self.config)
        self.monitor = ActivityMonitor(self.config)
        self.scheduler = Scheduler(self.config)
        self.notifier = DesktopNotifier(self.config)

        self.current_session_id: int = 0
        self._shutdown_requested = False

        # Set scheduler callback
        self.scheduler.set_break_callback(self._on_break)

        # Start a new session
        self._start_session()

    def _start_session(self) -> None:
        """Insert a new session record and store its ID."""
        now = datetime.now().isoformat()
        conn = self.db.connection
        cursor = conn.execute(
            "INSERT INTO sessions (started_at) VALUES (?)",
            (now,)
        )
        self.current_session_id = cursor.lastrowid
        conn.commit()
        logger.info("Started session ID %d", self.current_session_id)

    def _end_current_session(self) -> None:
        """Update the current session's ended_at timestamp."""
        if self.current_session_id:
            now = datetime.now().isoformat()
            self.db.connection.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ?",
                (now, self.current_session_id)
            )
            self.db.connection.commit()
            logger.info("Ended session ID %d", self.current_session_id)

    def _on_break(self) -> None:
        """Called when a break is triggered."""
        active_secs = self.monitor.active_seconds
        triggered_at = datetime.now().isoformat()

        # Log the break event
        conn = self.db.connection
        conn.execute(
            """INSERT INTO breaks
               (session_id, triggered_at, trigger_reason, active_seconds_before_break)
               VALUES (?, ?, ?, ?)""",
            (self.current_session_id, triggered_at, "time", active_secs)
        )
        conn.commit()

        # Send desktop notification
        self.notifier.send()

        # Reset active seconds
        self.monitor.reset()
        logger.info("Break triggered at %s, active seconds=%d", triggered_at, active_secs)

    def _activity_tick(self, active_seconds: int) -> None:
        """Called every second by the activity monitor."""
        self.scheduler.tick(active_seconds)

    def run(self) -> None:
        """Start the application and run until shutdown signal."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.monitor.start(on_tick=self._activity_tick)
        self.scheduler.start()

        logger.info("Eye Care Tool started. Press Ctrl+C to stop.")
        while not self._shutdown_requested:
            time.sleep(1)

        self.shutdown()

    def _signal_handler(self, signum, frame) -> None:
        logger.info("Received shutdown signal.")
        self._shutdown_requested = True

    def shutdown(self) -> None:
        """Clean shutdown of all components."""
        logger.info("Shutting down...")
        self.monitor.stop()
        self.scheduler.stop()
        self._end_current_session()
        self.db.close()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    app = EyeCareApp()
    app.run()