"""Telegram notification sender via Bot API."""

import json
import os
import logging
import requests
from typing import Optional

from core.config import Config, default_config

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Send break reminders via Telegram."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or default_config
        self.token = self._config.telegram_bot_token
        self.chat_id = self._config.telegram_chat_id
        self.enabled = bool(self.token and self.chat_id)

    def _load_messages(self) -> dict:
        """Load locale messages (duplicate from DesktopNotifier)."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        locale_path = os.path.join(base_dir, "notify", "locales", f"{self._config.locale}.json")
        try:
            with open(locale_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "break_title": "Eye Break",
                "break_body": "Time to rest your eyes!",
                "snooze": "Remind again",
                "dismiss": "Done"
            }

    def send(self, title_key: str = "break_title", body_key: str = "break_body") -> bool:
        """Send a Telegram message."""
        if not self.enabled:
            logger.info("Telegram not configured, skipping.")
            return False

        messages = self._load_messages()
        title = messages.get(title_key, "Eye Care Reminder")
        body = messages.get(body_key, "Look 20 feet away for 20 seconds.")
        message = f"*{title}*\n{body}"

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram notification sent.")
                return True
            else:
                logger.error("Telegram error: %s", response.text)
                return False
        except Exception as e:
            logger.error("Telegram send failed: %s", e)
            return False