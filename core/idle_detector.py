"""
Idle-detection abstraction.

Decouples ActivityMonitor from any single OS's idle-time API, so a
Linux/macOS backend can be added later without touching ActivityMonitor
or rewriting tests. Currently only Windows is implemented.
"""

from abc import ABC, abstractmethod


class IdleDetector(ABC):
    """Returns seconds since the last user input, for any platform."""

    @abstractmethod
    def get_idle_seconds(self) -> float:
        ...


class WindowsIdleDetector(IdleDetector):
    """Idle detection via the Win32 GetLastInputInfo API.
    No global hooks, no elevated permissions required."""

    def __init__(self) -> None:
        import ctypes
        import ctypes.wintypes
        self._ctypes = ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.wintypes.UINT),
                ("dwTime", ctypes.wintypes.DWORD),
            ]

        self._LASTINPUTINFO = LASTINPUTINFO
        self._get_last_input = ctypes.windll.user32.GetLastInputInfo
        self._get_last_input.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
        self._get_last_input.restype = ctypes.wintypes.BOOL
        self._get_tick_count = ctypes.windll.kernel32.GetTickCount
        self._get_tick_count.restype = ctypes.wintypes.DWORD

    def get_idle_seconds(self) -> float:
        try:
            lii = self._LASTINPUTINFO()
            lii.cbSize = self._ctypes.sizeof(self._LASTINPUTINFO)
            if not self._get_last_input(self._ctypes.byref(lii)):
                return 0.0  # API call failed — assume active rather than idle
            ticks = self._get_tick_count()
            # GetTickCount wraps every ~49.7 days; idle deltas are always
            # small relative to that, so the unsigned-wrap mask is safe.
            delta_ms = (ticks - lii.dwTime) & 0xFFFFFFFF
            return delta_ms / 1000.0
        except Exception:
            return 0.0


def get_default_idle_detector() -> IdleDetector:
    """Factory: pick the right IdleDetector for the current OS.

    Raises a clear RuntimeError on unsupported platforms instead of
    crashing deep inside ctypes with an unhelpful AttributeError.
    """
    import platform
    system = platform.system()
    if system == "Windows":
        return WindowsIdleDetector()
    raise RuntimeError(
        f"No IdleDetector implementation for platform '{system}' yet. "
        "Currently Windows-only — add a backend here (e.g. xprintidle "
        "on Linux, CGEventSourceSecondsSinceLastEventType on macOS)."
    )