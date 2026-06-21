"""Scheduler that triggers break reminders based on active screen time."""

import threading
import time
import logging
from typing import Optional, Callable

from core.config import Config, default_config

logger = logging.getLogger(__name__)

class Scheduler:
    """
    State machine that monitors active seconds and fires break events.

    It calls a callback when active_seconds reaches ACTIVE_INTERVAL.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or default_config
        self.active_interval = self._config.active_interval_seconds
        self._break_callback: Optional[Callable[[], None]] = None
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def set_break_callback(self, callback: Callable[[], None]) -> None:
        """Set the function to call when a break is due."""
        self._break_callback = callback

    def start(self) -> None:
        """Start the scheduler (must be called after set_break_callback)."""
        if self._running:
            return
        if self._break_callback is None:
            raise ValueError("Break callback not set; call set_break_callback first.")
        self._running = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)

    def _monitor_loop(self) -> None:
        """
        Periodically check active_seconds and trigger break when threshold reached.
        This loop does NOT run every second; it checks every 0.5s for responsiveness.
        """
        # We need a reference to the activity monitor to read active_seconds.
        # This will be set via a method later; for now we assume the main
        # program wires it. We'll use a global variable? Better to pass via constructor.
        # For Phase 1, we'll rely on the main loop to call check() externally.
        # Simpler: we'll have the main loop call scheduler.tick(active_seconds).
        # But the spec says scheduler watches active_seconds. Let's implement
        # a tick method that is called by the activity monitor's on_tick.
        # So scheduler will not have its own loop; it will react to ticks.
        pass

    def tick(self, active_seconds: int) -> None:
        """
        Called every second with the current active seconds.

        If active_seconds >= interval and we are not in a break state,
        trigger the break callback and reset the counter (will be done externally).
        """
        if not self._running:
            return
        if self._break_callback is None:
            return
        if active_seconds >= self.active_interval:
            # Trigger break
            logger.info("Break triggered after %d active seconds.", active_seconds)
            self._break_callback()