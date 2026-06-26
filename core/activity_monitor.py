"""Activity monitor — accumulates active seconds via a pluggable IdleDetector."""

import threading
import logging
from typing import Optional, Callable

from core.config import Config, default_config
from core.idle_detector import IdleDetector, get_default_idle_detector

logger = logging.getLogger(__name__)


class ActivityMonitor:
    """
    Tracks user activity by polling an IdleDetector once per second.
    No keyboard/mouse hooks, so no extra permissions or compatibility issues.
    """

    def __init__(self, config: Optional[Config] = None,
                 idle_detector: Optional[IdleDetector] = None) -> None:
        self._config = config or default_config
        self.idle_threshold = float(self._config.idle_threshold_seconds)
        # Injectable for testing (see tests/test_activity_monitor.py) and
        # for adding non-Windows backends later without touching this class.
        self._idle_detector = idle_detector or get_default_idle_detector()
        self._active_seconds = 0
        self._running = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._on_tick_callback: Optional[Callable[[int], None]] = None
        self._tick_thread: Optional[threading.Thread] = None

    def start(self, on_tick: Optional[Callable[[int], None]] = None) -> None:
        """Start the activity monitor."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._on_tick_callback = on_tick
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._tick_thread.start()

    def stop(self) -> None:
        """Stop the activity monitor."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._tick_thread and self._tick_thread.is_alive():
            self._tick_thread.join(timeout=1.0)

    def _tick_loop(self) -> None:
        """Tick once per second and update active_seconds."""
        while not self._stop_event.is_set():
            idle_sec = self._idle_detector.get_idle_seconds()
            with self._lock:
                if idle_sec < self.idle_threshold:
                    self._active_seconds += 1
                current_active = self._active_seconds

            if self._on_tick_callback:
                try:
                    self._on_tick_callback(current_active)
                except Exception as e:
                    # NOTE: this catch keeps the background thread alive —
                    # it does NOT reset active_seconds. That responsibility
                    # belongs to main.py's try/finally around _on_break, so
                    # there is exactly one place that decides when a break
                    # has been "handled." Logged at ERROR (not DEBUG) so a
                    # real failure here is actually visible.
                    logger.error("Tick callback error: %s", e)

            self._stop_event.wait(1.0)

    @property
    def active_seconds(self) -> int:
        with self._lock:
            return self._active_seconds

    @active_seconds.setter
    def active_seconds(self, value: int) -> None:
        with self._lock:
            self._active_seconds = value

    def reset(self) -> None:
        with self._lock:
            self._active_seconds = 0