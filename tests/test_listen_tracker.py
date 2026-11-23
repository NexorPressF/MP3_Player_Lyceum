import unittest

from core.listen_tracker import ListenTracker


class ListenTrackerTestCase(unittest.TestCase):
    def play(self, tracker, start_ms, end_ms, step_ms=100):
        for position in range(start_ms, end_ms + 1, step_ms):
            tracker.update(position)

    def test_counts_continuous_playback(self):
        tracker = ListenTracker()
        self.play(tracker, 0, 31_000)
        self.assertEqual(tracker.listened_seconds, 31)
        self.assertTrue(tracker.is_loggable)

    def test_short_listen_is_not_loggable(self):
        tracker = ListenTracker()
        self.play(tracker, 0, 10_000)
        self.assertFalse(tracker.is_loggable)

    def test_seek_is_not_counted(self):
        tracker = ListenTracker()
        self.play(tracker, 0, 5_000)
        tracker.update(120_000)
        self.play(tracker, 120_000, 125_000)
        self.assertEqual(tracker.listened_seconds, 10)
        tracker.update(0)
        self.assertEqual(tracker.listened_seconds, 10)

    def test_pause_adds_nothing(self):
        tracker = ListenTracker()
        self.play(tracker, 0, 5_000)
        self.play(tracker, 5_000, 8_000)
        self.assertEqual(tracker.listened_seconds, 8)

    def test_reset(self):
        tracker = ListenTracker()
        self.play(tracker, 0, 40_000)
        tracker.reset()
        self.assertEqual(tracker.listened_seconds, 0)
        tracker.update(500)
        self.assertEqual(tracker.listened_seconds, 0)


if __name__ == "__main__":
    unittest.main()
