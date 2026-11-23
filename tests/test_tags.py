import tempfile
import unittest
from pathlib import Path

from core.library import add_files_to_library, find_mp3_files
from core.tags import fix_encoding, read_cover, read_tags
from data.database import Database
from tests.helpers import make_mp3, make_png


class TagsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_read_tags_and_duration(self):
        path = make_mp3(self.dir / "x.mp3", "Песня", "Исполнитель", "Альбом")
        info = read_tags(path)
        self.assertEqual(info["title"], "Песня")
        self.assertEqual(info["artist"], "Исполнитель")
        self.assertEqual(info["album"], "Альбом")
        self.assertEqual(info["duration_sec"], 5)

    def test_file_without_tags_uses_file_name(self):
        path = make_mp3(self.dir / "Без тегов.mp3")
        info = read_tags(path)
        self.assertEqual(info["title"], "Без тегов")
        self.assertEqual(info["artist"], "Неизвестный")

    def test_broken_file_does_not_crash(self):
        path = self.dir / "broken.mp3"
        path.write_bytes(b"not an mp3 at all")
        info = read_tags(path)
        self.assertEqual(info["title"], "broken")
        self.assertEqual(info["duration_sec"], 0)

    def test_cover(self):
        png = make_png()
        with_cover = make_mp3(self.dir / "c.mp3", "T", "A", cover=png)
        without = make_mp3(self.dir / "n.mp3", "T", "A")
        self.assertEqual(read_cover(with_cover), png)
        self.assertIsNone(read_cover(without))
        self.assertIsNone(read_cover(self.dir / "missing.mp3"))

    def test_fix_encoding(self):
        broken = "Песня".encode("cp1251").decode("latin-1")
        self.assertEqual(fix_encoding(broken), "Песня")
        self.assertEqual(fix_encoding("Café"), "Café")
        self.assertEqual(fix_encoding("Нормальный текст"), "Нормальный текст")
        self.assertEqual(fix_encoding("Song 2000"), "Song 2000")

    def test_add_files_and_folder_scan(self):
        sub = self.dir / "album"
        sub.mkdir()
        make_mp3(self.dir / "a.mp3", "A", "X")
        make_mp3(sub / "b.MP3", "B", "Y")
        (self.dir / "note.txt").write_text("hi")
        found = find_mp3_files(self.dir)
        self.assertEqual([p.name for p in found], ["a.mp3", "b.MP3"])

        db = Database(self.dir / "t.db")
        paths = [str(p) for p in found] + [str(self.dir / "note.txt"),
                                           str(self.dir / "ghost.mp3")]
        ids, skipped = add_files_to_library(db, paths)
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(skipped), 2)
        ids_again, _ = add_files_to_library(db, [str(found[0])])
        self.assertEqual(ids_again, ids[:1])
        self.assertEqual(len(db.get_tracks()), 2)
        db.close()


if __name__ == "__main__":
    unittest.main()
