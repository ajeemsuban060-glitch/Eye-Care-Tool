"""Desktop notification sender using plyer (cross-platform)."""

import json
import os
import logging
from typing import Optional

from plyer import notification

from core.config import Config, default_config

logger = logging.getLogger(__name__)


class DesktopNotifier:
    """
    Sends desktop notifications with locale-aware messages.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or default_config
        self.locale = self._config.locale
        self._messages = self._load_locale(self.locale)
        self.fallback_to_console = self._config.fallback_to_console

    def _load_locale(self, locale: str) -> dict:
        """Load locale JSON file from notify/locales/."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        locale_path = os.path.join(base_dir, "notify", "locales", f"{locale}.json")
        try:
            with open(locale_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error("Failed to load locale '%s': %s. Using English fallback.", locale, e)
            return {
                "break_title": "Eye Break Time!",
                "break_body": "Look at something 20 feet away for 20 seconds.",
                "snooze": "Remind again",
                "dismiss": "Done"
            }

    def send(self, title_key: str = "break_title", body_key: str = "break_body") -> bool:
        """
        Send a desktop notification using the configured locale.

        This method must NEVER raise. A failed notification (plyer backend
        unavailable, OS notification service down, etc.) is a real but
        non-fatal failure — it must never be able to stop the rest of the
        break flow in main.py's _on_break(). That was the root cause of the
        notification-spam bug: this used to `raise` on failure, which
        skipped monitor.reset() and caused the break to re-trigger every
        second forever.

        Returns:
            True if the OS notification was sent, False otherwise (whether
            or not a console fallback was printed).
        """
        title = self._messages.get(title_key, "Eye Care Reminder")
        body = self._messages.get(body_key, "Time to rest your eyes!")

        try:
            notification.notify(
                title=title,
                message=body,
                app_name="Eye Care Tool",
                timeout=10,
            )
            logger.info("Desktop notification sent: %s", title)
            return True
        except Exception as e:
            logger.error("Failed to send desktop notification: %s", e)
            if self.fallback_to_console:
                print("\n" + "=" * 50)
                print(f"[{title}] {body}")
                print("=" * 50 + "\n")
            return False

    def reload_locale(self) -> None:
        """Reload locale messages (useful if config locale changed)."""
        self._messages = self._load_locale(self._config.locale)