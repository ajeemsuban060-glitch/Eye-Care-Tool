"""Unit tests for ActivityMonitor, using a FakeIdleDetector so these run on
any OS (not just Windows) and don't depend on real input devices."""

import time
from unittest import TestCase, main

from core.activity_monitor import ActivityMonitor
from core.config import Config
from core.idle_detector import IdleDetector


class FakeIdleDetector(IdleDetector):
    """Test double: returns whatever idle value the test sets."""

    def __init__(self):
        self.idle_seconds = 0.0

    def get_idle_seconds(self) -> float:
        return self.idle_seconds


class TestActivityMonitor(TestCase):
    def setUp(self):
        self.config = Config(idle_threshold_seconds=1)
        self.fake_idle = FakeIdleDetector()
        self.monitor = ActivityMonitor(self.config, idle_detector=self.fake_idle)

    def tearDown(self):
        self.monitor.stop()

    def test_active_seconds_increment_when_not_idle(self):
        self.fake_idle.idle_seconds = 0.0  # always "active"
        self.monitor.start()
        time.sleep(2.2)
        self.assertGreaterEqual(self.monitor.active_seconds, 2)

    def test_active_seconds_do_not_increment_when_idle(self):
        self.fake_idle.idle_seconds = 999.0  # always "idle"
        self.monitor.start()
        time.sleep(1.5)
        self.assertEqual(self.monitor.active_seconds, 0)

    def test_reset_zeros_the_counter(self):
        self.fake_idle.idle_seconds = 0.0
        self.monitor.start()
        time.sleep(1.2)
        self.assertGreater(self.monitor.active_seconds, 0)
        self.monitor.reset()
        self.assertEqual(self.monitor.active_seconds, 0)

    def test_tick_callback_exception_does_not_kill_monitor_thread(self):
        """A broken callback (e.g. a notifier that raises) must not crash
        the monitor's background thread — it should keep ticking."""
        self.fake_idle.idle_seconds = 0.0

        def bad_callback(active_seconds):
            raise RuntimeError("simulated notifier failure")

        self.monitor.start(on_tick=bad_callback)
        time.sleep(1.5)
        self.assertTrue(self.monitor._tick_thread.is_alive())


if __name__ == "__main__":
    main()