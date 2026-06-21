"""Activity monitor for Windows using GetLastInputInfo (no global hooks)."""

import ctypes
import ctypes.wintypes
import threading
import time
import logging
from typing import Optional, Callable

from core.config import Config, default_config

logger = logging.getLogger(__name__)

# Windows API structures
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.UINT),
        ("dwTime", ctypes.wintypes.DWORD),
    ]

class ActivityMonitor:
    """
    Tracks user activity on Windows by querying the last input time.
    No keyboard/mouse hooks, so no permissions or compatibility issues.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or default_config
        self.idle_threshold = float(self._config.idle_threshold_seconds)
        self._active_seconds = 0
        self._running = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._on_tick_callback: Optional[Callable[[int], None]] = None
        self._tick_thread: Optional[threading.Thread] = None

        # Get the Windows API function
        self._get_last_input = ctypes.windll.user32.GetLastInputInfo
        self._get_last_input.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
        self._get_last_input.restype = ctypes.wintypes.BOOL

        # Get tick count function
        self._get_tick_count = ctypes.windll.kernel32.GetTickCount
        self._get_tick_count.restype = ctypes.wintypes.DWORD

    def start(self, on_tick: Optional[Callable[[int], None]] = None) -> None:
        """Start the activity monitor."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._on_tick_callback = on_tick

        # Start tick loop
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

    def _get_idle_seconds(self) -> float:
        """Return the number of seconds since the last user input."""
        try:
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if not self._get_last_input(ctypes.byref(lii)):
                return 0.0  # API call failed, assume active
            ticks = self._get_tick_count()
            # Tick count wraps, but idle time is small, so ignore wrap
            delta_ms = (ticks - lii.dwTime) & 0xFFFFFFFF
            return delta_ms / 1000.0
        except Exception as e:
            logger.debug("Error getting idle time: %s", e)
            return 0.0

    def _tick_loop(self) -> None:
        """Tick once per second and update active_seconds."""
        while not self._stop_event.is_set():
            idle_sec = self._get_idle_seconds()
            with self._lock:
                if idle_sec < self.idle_threshold:
                    self._active_seconds += 1
                # else: idle, do not increment
                current_active = self._active_seconds

            if self._on_tick_callback:
                try:
                    self._on_tick_callback(current_active)
                except Exception as e:
                    logger.debug("Tick callback error: %s", e)

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