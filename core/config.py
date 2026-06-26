"""Configuration settings for the eye care tool.

Non-secret settings come from config.json (or defaults).
Secrets (Telegram token/chat id) come ONLY from environment variables / a
.env file — never from config.json, and never from git history.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional, List

from dotenv import load_dotenv

load_dotenv()  # loads .env into os.environ if present; harmless no-op if missing


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
    def load_from_file(cls, file_path: Optional[str] = None) -> "Config":
        """Load non-secret config from config.json, resolved relative to this
        module's location (not the process's working directory — fixes the
        CWD-fragility issue that already bit the TAMIL-AI.ME FastAPI server).
        Secrets are layered on top from environment variables afterward.
        """
        if file_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base_dir, "config.json")

        if not os.path.exists(file_path):
            config = cls()
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Defensive: even if an old config.json still has these keys
                # (e.g. a leftover stale copy on someone's disk), never read
                # secrets from this file. Env vars are the only source.
                data.pop("telegram_bot_token", None)
                data.pop("telegram_chat_id", None)
                valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
                filtered = {k: v for k, v in data.items() if k in valid_keys}
                config = cls(**filtered)
            except Exception as e:
                print(f"Error loading config.json: {e}. Using defaults.")
                config = cls()

        config.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or None
        chat_id_str = os.environ.get("TELEGRAM_CHAT_ID")
        config.telegram_chat_id = int(chat_id_str) if chat_id_str else None
        return config


# Default global instance, loaded once at import time.
default_config = Config.load_from_file()