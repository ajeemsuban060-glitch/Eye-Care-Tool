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
    Supports snooze delay.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or default_config
        self.active_interval = self._config.active_interval_seconds
        self._break_callback: Optional[Callable[[], None]] = None
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._snooze_until: float = 0.0  # timestamp when snooze ends

    def set_break_callback(self, callback: Callable[[], None]) -> None:
        self._break_callback = callback

    def start(self) -> None:
        if self._running:
            return
        if self._break_callback is None:
            raise ValueError("Break callback not set; call set_break_callback first.")
        self._running = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)

    def snooze(self, duration_seconds: int) -> None:
        """Set a snooze delay, ignoring break triggers for duration."""
        self._snooze_until = time.time() + duration_seconds
        logger.info("Snoozed until %s", time.ctime(self._snooze_until))

    def _monitor_loop(self) -> None:
        """Periodically check active_seconds and trigger break when threshold reached."""
        # We rely on the main loop calling tick() each second.
        # This thread just sleeps until stop.
        while not self._stop_event.is_set():
            time.sleep(0.1)

    def tick(self, active_seconds: int) -> None:
        """Called every second with current active seconds."""
        if not self._running:
            return
        if self._break_callback is None:
            return
        # Check snooze
        if self._snooze_until > time.time():
            # Snooze active, do not trigger
            return
        if active_seconds >= self.active_interval:
            self._break_callback()