import csv
import tempfile
import unittest
from pathlib import Path

from data.exchange import export_playlist_csv, read_paths_txt


class ExchangeTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_export_csv(self):
        tracks = [
            {"title": "Песня", "artist": "Группа", "album": None,
             "duration_sec": 185, "path": "C:\\Music\\a.mp3"},
            {"title": "Song; with semicolon", "artist": "A", "album": "B",
             "duration_sec": 60, "path": "b.mp3"},
        ]
        target = self.dir / "list.csv"
        self.assertEqual(export_playlist_csv(target, tracks), 2)
        with open(target, encoding="utf-8-sig", newline="") as file:
            rows = list(csv.reader(file, delimiter=";"))
        self.assertEqual(rows[0][0], "Название")
        self.assertEqual(rows[1], ["Песня", "Группа", "", "185", "C:\\Music\\a.mp3"])
        self.assertEqual(rows[2][0], "Song; with semicolon")

    def test_read_paths_skips_comments_blanks_and_quotes(self):
        source = self.dir / "paths.txt"
        source.write_text('# мой список\n\n"C:\\Music\\a.mp3"\n  D:\\b.mp3  \n',
                          encoding="utf-8")
        self.assertEqual(read_paths_txt(source), ["C:\\Music\\a.mp3", "D:\\b.mp3"])

    def test_read_paths_cp1251(self):
        source = self.dir / "paths.txt"
        source.write_bytes("C:\\Музыка\\песня.mp3\n".encode("cp1251"))
        self.assertEqual(read_paths_txt(source), ["C:\\Музыка\\песня.mp3"])


if __name__ == "__main__":
    unittest.main()
