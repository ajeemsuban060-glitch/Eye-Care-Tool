#!/usr/bin/env python3
"""Entry point – Tkinter event‑driven version with GUI dialogs."""

import logging
import signal
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

from core.config import default_config
from core.activity_monitor import ActivityMonitor
from core.scheduler import Scheduler
from notify.desktop_notifier import DesktopNotifier
from notify.telegram_notifier import TelegramNotifier
from storage.db import Database

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class EyeCareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Eye Care Tool")
        self.root.withdraw()          # hide main window (runs in background)

        self.config = default_config
        self.db = Database(self.config)
        self.monitor = ActivityMonitor(self.config)
        self.scheduler = Scheduler(self.config)
        self.desktop_notifier = DesktopNotifier(self.config)
        self.telegram_notifier = TelegramNotifier(self.config)

        self.current_session_id = 0
        self._shutdown_requested = False

        # Set scheduler callback
        self.scheduler.set_break_callback(self._on_break)

        # Start a new session
        self._start_session()

        # Start the activity monitor (runs in background thread)
        self.monitor.start(on_tick=self._activity_tick)
        self.scheduler.start()

        logger.info("Eye Care Tool started (Tkinter backend).")

        # Schedule the first check immediately, then every second
        self._check_loop()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _start_session(self):
        now = datetime.now().isoformat()
        conn = self.db.connection
        cursor = conn.execute("INSERT INTO sessions (started_at) VALUES (?)", (now,))
        self.current_session_id = cursor.lastrowid
        conn.commit()
        logger.info("Started session ID %d", self.current_session_id)

    def _end_current_session(self):
        if self.current_session_id:
            now = datetime.now().isoformat()
            self.db.connection.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ?",
                (now, self.current_session_id)
            )
            self.db.connection.commit()
            logger.info("Ended session ID %d", self.current_session_id)

    def _activity_tick(self, active_seconds):
        """Called every second by the activity monitor."""
        self.scheduler.tick(active_seconds)

    def _check_loop(self):
        """Called repeatedly via Tkinter's after() to keep the app alive."""
        if self._shutdown_requested:
            return
        # Check for any pending events (like shutdown signal)
        self.root.after(1000, self._check_loop)

    def _on_break(self):
        """Break callback – shows a modal dialog with buttons."""
        active_secs = self.monitor.active_seconds
        triggered_at = datetime.now().isoformat()
        conn = self.db.connection

        # Insert break record
        cursor = conn.execute(
            """INSERT INTO breaks
               (session_id, triggered_at, trigger_reason, active_seconds_before_break)
               VALUES (?, ?, ?, ?)""",
            (self.current_session_id, triggered_at, "time", active_secs)
        )
        break_id = cursor.lastrowid
        conn.commit()

        # Send desktop and Telegram notifications (non‑blocking)
        if "desktop" in self.config.notification_channels:
            self.desktop_notifier.send()
        if "telegram" in self.config.notification_channels:
            self.telegram_notifier.send()

        # Now show a modal Tkinter dialog (blocks until user clicks)
        response = self._show_dialog()

        # Handle snooze
        if response == "snoozed":
            self.scheduler.snooze(self.config.snooze_duration_seconds)

        # Update break row with user_response
        conn.execute(
            "UPDATE breaks SET user_response = ? WHERE id = ?",
            (response, break_id)
        )
        conn.commit()

        # Reset active seconds
        self.monitor.reset()
        logger.info("Break triggered, active seconds=%d, response=%s",
                    active_secs, response)

    def _show_dialog(self):
        """Create a modal dialog with Dismiss and Snooze buttons."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Eye Break")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.attributes('-topmost', True)
        dialog.grab_set()   # modal

        # Load locale messages (use Tamil if configured)
        from notify.desktop_notifier import DesktopNotifier
        notifier = DesktopNotifier(self.config)
        messages = notifier._messages
        title = messages.get("break_title", "Eye Break")
        body = messages.get("break_body", "Look 20 feet away for 20 seconds.")

        # Message
        label = tk.Label(dialog, text=body, wraplength=300, justify="center", font=("Arial", 12))
        label.pack(pady=10)

        # Response variable
        response_var = tk.StringVar(value="unknown")

        def on_dismiss():
            response_var.set("taken")
            dialog.destroy()

        def on_snooze():
            response_var.set("snoozed")
            dialog.destroy()

        # Buttons
        frame = tk.Frame(dialog)
        frame.pack(pady=10)
        btn_dismiss = tk.Button(frame, text="Dismiss (Done)", command=on_dismiss, width=12)
        btn_dismiss.pack(side=tk.LEFT, padx=5)
        btn_snooze = tk.Button(frame, text="Snooze (1 min)", command=on_snooze, width=12)
        btn_snooze.pack(side=tk.RIGHT, padx=5)

        # If user closes window via X, treat as Dismiss
        dialog.protocol("WM_DELETE_WINDOW", on_dismiss)

        # Center the window
        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        # Wait for the dialog to close
        self.root.wait_window(dialog)
        return response_var.get()

    def shutdown(self):
        """Clean shutdown."""
        if self._shutdown_requested:
            return
        self._shutdown_requested = True
        logger.info("Shutting down...")
        self.monitor.stop()
        self.scheduler.stop()
        self._end_current_session()
        self.db.close()
        self.root.quit()
        self.root.destroy()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    root = tk.Tk()
    app = EyeCareApp(root)
    root.mainloop()