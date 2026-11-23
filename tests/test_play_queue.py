import unittest

from core.play_queue import PlayQueue, RepeatMode


def make_queue(count=4, start=0):
    queue = PlayQueue()
    queue.set_tracks([f"t{i}" for i in range(count)], start)
    return queue


class PlayQueueTestCase(unittest.TestCase):
    def test_empty_queue(self):
        queue = PlayQueue()
        self.assertIsNone(queue.current)
        self.assertIsNone(queue.next())
        self.assertIsNone(queue.previous())
        self.assertEqual(queue.current_index, -1)

    def test_next_and_previous(self):
        queue = make_queue()
        self.assertEqual(queue.current, "t0")
        self.assertEqual(queue.next(), "t1")
        self.assertEqual(queue.next(), "t2")
        self.assertEqual(queue.previous(), "t1")

    def test_end_of_queue_without_repeat(self):
        queue = make_queue(2, start=1)
        self.assertIsNone(queue.next())
        self.assertIsNone(queue.next(auto=True))
        self.assertEqual(queue.current, "t1")

    def test_previous_at_start_stays(self):
        queue = make_queue()
        self.assertEqual(queue.previous(), "t0")

    def test_repeat_playlist_wraps_around(self):
        queue = make_queue(2, start=1)
        queue.repeat = RepeatMode.PLAYLIST
        self.assertEqual(queue.next(), "t0")
        self.assertEqual(queue.previous(), "t1")

    def test_repeat_track_only_for_auto_next(self):
        queue = make_queue()
        queue.repeat = RepeatMode.TRACK
        self.assertEqual(queue.next(auto=True), "t0")
        self.assertEqual(queue.next(auto=False), "t1")

    def test_cycle_repeat(self):
        queue = PlayQueue()
        self.assertEqual(queue.cycle_repeat(), RepeatMode.TRACK)
        self.assertEqual(queue.cycle_repeat(), RepeatMode.PLAYLIST)
        self.assertEqual(queue.cycle_repeat(), RepeatMode.OFF)

    def test_shuffle_plays_every_track_once_and_keeps_current_first(self):
        queue = make_queue(20, start=5)
        queue.set_shuffle(True)
        self.assertEqual(queue.current, "t5")
        seen = [queue.current]
        while True:
            track = queue.next()
            if track is None:
                break
            seen.append(track)
        self.assertEqual(sorted(seen), sorted(f"t{i}" for i in range(20)))

    def test_shuffle_off_restores_order_and_current(self):
        queue = make_queue(10, start=3)
        queue.set_shuffle(True)
        queue.next()
        current = queue.current
        queue.set_shuffle(False)
        self.assertEqual(queue.current, current)
        expected = f"t{(int(current[1:]) + 1) % 10}"
        if current != "t9":
            self.assertEqual(queue.next(), expected)

    def test_shuffle_with_repeat_playlist_never_ends(self):
        queue = make_queue(5)
        queue.set_shuffle(True)
        queue.repeat = RepeatMode.PLAYLIST
        for _ in range(30):
            self.assertIsNotNone(queue.next(auto=True))

    def test_select_and_append(self):
        queue = make_queue(3)
        self.assertEqual(queue.select(2), "t2")
        queue.append(["x", "y"])
        self.assertEqual(len(queue), 5)
        self.assertEqual(queue.next(), "x")
        self.assertIsNone(queue.select(99))

    def test_append_to_empty_queue_makes_first_current(self):
        queue = PlayQueue()
        queue.append(["a", "b"])
        self.assertEqual(queue.current, "a")

    def test_start_index_is_clamped(self):
        queue = make_queue(3, start=10)
        self.assertEqual(queue.current, "t2")


if __name__ == "__main__":
    unittest.main()
