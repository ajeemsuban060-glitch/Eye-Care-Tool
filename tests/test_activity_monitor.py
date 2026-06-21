"""Unit tests for ActivityMonitor (mocking time)."""

import time
import threading
from unittest import TestCase, main
from core.activity_monitor import ActivityMonitor

class TestActivityMonitor(TestCase):
    def test_activity_accumulation(self):
        """Test that active seconds increment when input events occur."""
        monitor = ActivityMonitor()
        # Override idle threshold to a small value for test
        monitor.idle_threshold = 2.0
        monitor.start()

        # Simulate an input event
        monitor._on_input_event()
        time.sleep(0.5)  # wait for tick
        # Should have incremented at least once
        self.assertGreaterEqual(monitor.active_seconds, 1)

        # Stop
        monitor.stop()

    def test_idle_does_not_increment(self):
        """Test that after idle timeout, active seconds stop increasing."""
        monitor = ActivityMonitor()
        monitor.idle_threshold = 1.0  # 1 second idle threshold
        monitor.start()

        # Set last activity far in the past
        monitor._last_activity = time.monotonic() - 5.0
        time.sleep(1.5)
        # Should not have incremented
        self.assertEqual(monitor.active_seconds, 0)

        monitor.stop()

if __name__ == "__main__":
    main()