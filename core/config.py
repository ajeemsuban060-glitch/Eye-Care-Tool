"""Configuration settings for the eye care tool."""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """User-configurable parameters."""

    # Activity detection
    idle_threshold_seconds: int = 10          # seconds of no input = idle
    active_interval_seconds: int = 1200       # 20 minutes

    # Locale
    locale: str = "en"                        # "en" or "ta"

    # Notification (Telegram will be added later)
    telegram_chat_id: Optional[str] = None

    # Database
    db_path: str = "eye_care.sqlite"

    # Snooze duration (not used in Phase 1)
    snooze_duration_seconds: int = 60

    # Desktop notification fallback: if plyer fails, print to console
    fallback_to_console: bool = True

# Default global instance
default_config = Config()