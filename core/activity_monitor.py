"""Monitors keyboard/mouse activity and accumulates active seconds."""

import threading
import time
from typing import Optional, Callable

from pynput import keyboard, mouse

from core.config import Config, default_config

class ActivityMonitor:
    """
    Tracks user activity via global input hooks.

    Attributes:
        active_seconds (int): Total active seconds accumulated.
        last_activity_timestamp (float): Monotonic time of last input event.
        idle_threshold (float): Seconds of no activity to consider idle.
        running (bool): Whether the monitor is active.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or default_config
        self.idle_threshold = float(self._config.idle_threshold_seconds)
        self.active_seconds = 0
        self._last_activity = time.monotonic()
        self._running = False
        self._lock = threading.Lock()
        self._listener_thread: Optional[threading.Thread] = None
        self._tick_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_tick_callback: Optional[Callable[[int], None]] = None

    def start(self, on_tick: Optional[Callable[[int], None]] = None) -> None:
        """
        Start the activity monitor.

        Args:
            on_tick: Callback invoked every second with active_seconds.
        """
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._on_tick_callback = on_tick

        # Start input listeners
        self._listener_thread = threading.Thread(
            target=self._run_listeners, daemon=True
        )
        self._listener_thread.start()

        # Start tick loop
        self._tick_thread = threading.Thread(
            target=self._tick_loop, daemon=True
        )
        self._tick_thread.start()

    def stop(self) -> None:
        """Stop the activity monitor and release listeners."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.0)
        if self._tick_thread and self._tick_thread.is_alive():
            self._tick_thread.join(timeout=1.0)

    def _on_input_event(self) -> None:
        """Update the last activity timestamp."""
        with self._lock:
            self._last_activity = time.monotonic()

    def _run_listeners(self) -> None:
        """Run pynput keyboard and mouse listeners in a single thread."""
        with keyboard.Listener(on_press=lambda _: self._on_input_event()) as k_listener, \
             mouse.Listener(on_move=lambda x, y: self._on_input_event(),
                            on_click=lambda x, y, b, p: self._on_input_event(),
                            on_scroll=lambda x, y, dx, dy: self._on_input_event()) as m_listener:
            # Keep the thread alive until stop is requested
            while not self._stop_event.is_set():
                time.sleep(0.1)

    def _tick_loop(self) -> None:
        """Tick once per second and update active_seconds."""
        while not self._stop_event.is_set():
            now = time.monotonic()
            with self._lock:
                if now - self._last_activity < self.idle_threshold:
                    self.active_seconds += 1
                # else: idle, do not increment
                current_active = self.active_seconds

            if self._on_tick_callback:
                try:
                    self._on_tick_callback(current_active)
                except Exception:
                    # Log but don't crash the loop
                    pass

            # Wait one second, but allow early stop
            self._stop_event.wait(1.0)

    @property
    def active_seconds(self) -> int:
        """Current active seconds accumulated since last reset."""
        with self._lock:
            return self._active_seconds

    @active_seconds.setter
    def active_seconds(self, value: int) -> None:
        with self._lock:
            self._active_seconds = value

    def reset(self) -> None:
        """Reset the accumulated active seconds to zero."""
        with self._lock:
            self._active_seconds = 0