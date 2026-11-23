import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from data.database import Database, period_start


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "test.db")
        self.a = self.db.add_track("a.mp3", "Альфа", "Группа Б", "Альбом", 100)
        self.b = self.db.add_track("b.mp3", "бета", "Artist", "", 200)
        self.c = self.db.add_track("c.mp3", "Гамма", "Артист", "", 300)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_add_track_twice_returns_same_id(self):
        self.assertEqual(self.db.add_track("a.mp3", "Другое", "Другой"), self.a)
        self.assertEqual(len(self.db.get_tracks()), 3)

    def test_search_ignores_case_for_cyrillic(self):
        titles = [t["title"] for t in self.db.get_tracks(search="АЛЬФ")]
        self.assertEqual(titles, ["Альфа"])
        self.assertEqual(len(self.db.get_tracks(search="артист")), 1)
        self.assertEqual(len(self.db.get_tracks(search="ARTIST")), 1)
        self.assertEqual(len(self.db.get_tracks(search="")), 3)

    def test_search_with_special_characters(self):
        self.assertEqual(self.db.get_tracks(search="%"), [])

    def test_sort_options(self):
        by_title = [t["title"] for t in self.db.get_tracks(sort="По названию")]
        self.assertEqual(by_title, ["Альфа", "бета", "Гамма"])
        by_length = [t["id"] for t in self.db.get_tracks(sort="По длительности")]
        self.assertEqual(by_length, [self.c, self.b, self.a])

    def test_update_and_delete_track(self):
        self.db.update_track(self.a, "Новое", "Новый")
        self.assertEqual(self.db.get_track(self.a)["title"], "Новое")
        self.db.delete_track(self.a)
        self.assertIsNone(self.db.get_track(self.a))

    def test_get_tracks_by_ids_keeps_order_and_skips_missing(self):
        rows = self.db.get_tracks_by_ids([self.c, 999, self.a])
        self.assertEqual([r["id"] for r in rows], [self.c, self.a])
        self.assertEqual(self.db.get_tracks_by_ids([]), [])

    def test_playlist_names_are_unique(self):
        first = self.db.create_playlist("Мой")
        self.assertIsNotNone(first)
        self.assertIsNone(self.db.create_playlist("Мой"))
        second = self.db.create_playlist("Другой")
        self.assertFalse(self.db.rename_playlist(second, "Мой"))
        self.assertTrue(self.db.rename_playlist(second, "Третий"))

    def test_playlist_tracks_add_remove_move(self):
        pl = self.db.create_playlist("P")
        self.assertTrue(self.db.add_track_to_playlist(pl, self.a))
        self.assertFalse(self.db.add_track_to_playlist(pl, self.a))
        self.db.add_track_to_playlist(pl, self.b)
        self.db.add_track_to_playlist(pl, self.c)
        ids = lambda: [t["id"] for t in self.db.get_playlist_tracks(pl)]
        self.assertEqual(ids(), [self.a, self.b, self.c])
        self.assertEqual(self.db.move_track_in_playlist(pl, self.c, -1), 1)
        self.assertEqual(ids(), [self.a, self.c, self.b])
        self.assertIsNone(self.db.move_track_in_playlist(pl, self.a, -1))
        self.assertIsNone(self.db.move_track_in_playlist(pl, self.b, 1))
        self.db.remove_track_from_playlist(pl, self.c)
        self.assertEqual(ids(), [self.a, self.b])
        self.assertEqual(self.db.get_playlists()[0]["track_count"], 2)

    def test_deleting_track_removes_it_from_playlist_and_history(self):
        pl = self.db.create_playlist("P")
        self.db.add_track_to_playlist(pl, self.a)
        self.db.log_play(self.a, 60)
        self.db.delete_track(self.a)
        self.assertEqual(self.db.get_playlist_tracks(pl), [])
        self.assertEqual(self.db.get_total_seconds(), 0)

    def test_deleting_playlist_keeps_tracks(self):
        pl = self.db.create_playlist("P")
        self.db.add_track_to_playlist(pl, self.a)
        self.db.delete_playlist(pl)
        self.assertEqual(self.db.get_playlists(), [])
        self.assertEqual(len(self.db.get_tracks()), 3)

    def test_log_play_for_missing_track_is_ignored(self):
        self.assertIsNone(self.db.log_play(999, 60))
        self.assertIsNotNone(self.db.log_play(self.a, 60))

    def test_update_play_seconds(self):
        play_id = self.db.log_play(self.a, 30)
        self.db.update_play_seconds(play_id, 95)
        self.assertEqual(self.db.get_total_seconds("all"), 95)
        self.assertEqual(self.db.get_top_tracks("all")[0]["plays"], 1)

    def test_statistics_by_period(self):
        now = datetime(2026, 11, 19, 15, 0, 0)
        fmt = "%Y-%m-%d %H:%M:%S"
        self.db.log_play(self.a, 100, (now - timedelta(hours=1)).strftime(fmt))
        self.db.log_play(self.a, 50, (now - timedelta(hours=2)).strftime(fmt))
        self.db.log_play(self.b, 400, (now - timedelta(days=3)).strftime(fmt))
        self.db.log_play(self.c, 900, (now - timedelta(days=30)).strftime(fmt))

        day = self.db.get_top_tracks("day", now=now)
        self.assertEqual([(r["id"], r["plays"], r["total_sec"]) for r in day],
                         [(self.a, 2, 150)])
        week = self.db.get_top_tracks("week", now=now)
        self.assertEqual([r["id"] for r in week], [self.a, self.b])
        everything = self.db.get_top_tracks("all", now=now)
        self.assertEqual(len(everything), 3)
        self.assertEqual(self.db.get_total_seconds("day", now=now), 150)
        self.assertEqual(self.db.get_total_seconds("week", now=now), 550)
        self.assertEqual(self.db.get_total_seconds("all", now=now), 1450)

    def test_top_tracks_limit(self):
        for track in (self.a, self.b, self.c):
            self.db.log_play(track, 40)
        self.assertEqual(len(self.db.get_top_tracks("all", limit=2)), 2)

    def test_period_start(self):
        now = datetime(2026, 11, 19, 15, 30, 5)
        self.assertEqual(period_start("day", now), "2026-11-19 00:00:00")
        self.assertEqual(period_start("week", now), "2026-11-12 15:30:05")
        self.assertIsNone(period_start("all", now))


if __name__ == "__main__":
    unittest.main()
