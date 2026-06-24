"""Interactive notification using Tkinter (Windows-friendly)."""

import tkinter as tk
from tkinter import messagebox
import threading
import logging
from typing import Optional

from core.config import Config, default_config

logger = logging.getLogger(__name__)

class InteractiveNotifier:
    """
    Shows a modal dialog with Dismiss and Snooze buttons.
    Blocks the main thread until user responds.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or default_config
        self._response = None
        self._root = None
        self._event = threading.Event()

    def show(self, title_key: str = "break_title", body_key: str = "break_body") -> str:
        """
        Show a dialog and return user response: 'taken' or 'snoozed'.
        """
        # Load locale strings
        # We'll temporarily load from desktop_notifier's locale loading? 
        # Better to have a locale loader in a shared module. For now, we'll load directly.
        from notify.desktop_notifier import DesktopNotifier
        notifier = DesktopNotifier(self._config)
        messages = notifier._messages  # private, but okay for now
        title = messages.get(title_key, "Eye Break")
        body = messages.get(body_key, "Time to rest your eyes!")

        self._response = None
        self._event.clear()

        # Run Tkinter in a separate thread
        thread = threading.Thread(target=self._run_gui, args=(title, body), daemon=True)
        thread.start()

        # Wait for response
        self._event.wait()

        # Clean up
        if self._root:
            self._root.quit()
            self._root.destroy()

        return self._response

    def _run_gui(self, title: str, body: str) -> None:
        try:
            self._root = tk.Tk()
            self._root.title("Eye Care Tool")
            self._root.geometry("350x150")
            self._root.resizable(False, False)
            self._root.attributes('-topmost', True)  # keep on top

            # Set icon if you have one (optional)

            # Message
            label = tk.Label(self._root, text=body, wraplength=300, justify="center", font=("Arial", 12))
            label.pack(pady=10)

            # Buttons
            frame = tk.Frame(self._root)
            frame.pack(pady=10)

            def on_dismiss():
                self._response = "taken"
                self._event.set()

            def on_snooze():
                self._response = "snoozed"
                self._event.set()

            btn_dismiss = tk.Button(frame, text="Dismiss (Done)", command=on_dismiss, width=12)
            btn_dismiss.pack(side=tk.LEFT, padx=5)

            btn_snooze = tk.Button(frame, text="Snooze (1 min)", command=on_snooze, width=12)
            btn_snooze.pack(side=tk.RIGHT, padx=5)

            # Close window on X button also as dismiss? We'll treat it as dismiss.
            self._root.protocol("WM_DELETE_WINDOW", on_dismiss)

            # Center the window on screen
            self._root.update_idletasks()
            width = self._root.winfo_width()
            height = self._root.winfo_height()
            x = (self._root.winfo_screenwidth() // 2) - (width // 2)
            y = (self._root.winfo_screenheight() // 2) - (height // 2)
            self._root.geometry(f"{width}x{height}+{x}+{y}")

            self._root.mainloop()
        except Exception as e:
            logger.error("Failed to show interactive dialog: %s", e)
            # Fallback: treat as taken
            self._response = "taken"
            self._event.set()