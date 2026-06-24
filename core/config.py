"""Configuration settings for the eye care tool."""

import json
import os
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Config:
    """User-configurable parameters."""
    idle_threshold_seconds: int = 10
    active_interval_seconds: int = 1200
    locale: str = "ta"
    notification_channels: List[str] = field(default_factory=lambda: ["desktop"])
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[int] = None
    db_path: str = "eye_care.sqlite"
    snooze_duration_seconds: int = 60
    fallback_to_console: bool = True

    @classmethod
    def load_from_file(cls, file_path: str = "config.json") -> "Config":
        """Load configuration from a JSON file, falling back to defaults."""
        if not os.path.exists(file_path):
            return cls()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filter only keys that exist in dataclass fields
            valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in valid_keys}
            return cls(**filtered)
        except Exception as e:
            print(f"Error loading config.json: {e}. Using defaults.")
            return cls()

# Default global instance loaded from config.json
default_config = Config.load_from_file()