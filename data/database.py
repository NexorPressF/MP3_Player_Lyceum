import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).with_name("player.db")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
WEEK_DAYS = 7

SORT_ORDERS = {
    "По исполнителю": "py_lower(artist), py_lower(title)",
    "По названию": "py_lower(title), py_lower(artist)",
    "По альбому": "py_lower(album), py_lower(title)",
    "По длительности": "duration_sec DESC, py_lower(title)",
    "Недавно добавленные": "id DESC",
}
PERIODS = ("day", "week", "all")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    path         TEXT NOT NULL UNIQUE,
    title        TEXT NOT NULL,
    artist       TEXT NOT NULL,
    album        TEXT,
    duration_sec INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS playlists (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    track_id    INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, track_id)
);
CREATE TABLE IF NOT EXISTS play_history (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id         INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    played_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    seconds_listened INTEGER NOT NULL
);
"""


def _py_lower(text):
    return text.lower() if text else ""


def period_start(period, now=None):
    now = now or datetime.now()
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=WEEK_DAYS)
    else:
        return None
    return start.strftime(TIME_FORMAT)


class Database:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function("py_lower", 1, _py_lower)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def add_track(self, path, title, artist, album="", duration_sec=0):
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO tracks (path, title, artist, album, duration_sec) "
                "VALUES (?, ?, ?, ?, ?)",
                (path, title, artist, album, duration_sec),
            )
        row = self.conn.execute(
            "SELECT id FROM tracks WHERE path = ?", (path,)
        ).fetchone()
        return row["id"]

    def get_tracks(self, search="", sort="По исполнителю"):
        order_by = SORT_ORDERS.get(sort, SORT_ORDERS["По исполнителю"])
        text = search.strip().lower()
        return self.conn.execute(
            "SELECT * FROM tracks "
            "WHERE instr(py_lower(title), ?) > 0 OR instr(py_lower(artist), ?) > 0 "
            f"ORDER BY {order_by}",
            (text, text),
        ).fetchall()

    def get_track(self, track_id):
        return self.conn.execute(
            "SELECT * FROM tracks WHERE id = ?", (track_id,)
        ).fetchone()

    def get_tracks_by_ids(self, track_ids):
        if not track_ids:
            return []
        marks = ", ".join("?" * len(track_ids))
        rows = self.conn.execute(
            f"SELECT * FROM tracks WHERE id IN ({marks})", list(track_ids)
        ).fetchall()
        by_id = {row["id"]: row for row in rows}
        return [by_id[i] for i in track_ids if i in by_id]

    def update_track(self, track_id, title, artist):
        with self.conn:
            self.conn.execute(
                "UPDATE tracks SET title = ?, artist = ? WHERE id = ?",
                (title, artist, track_id),
            )

    def delete_track(self, track_id):
        with self.conn:
            self.conn.execute("DELETE FROM tracks WHERE id = ?", (track_id,))

    def create_playlist(self, name):
        try:
            with self.conn:
                cursor = self.conn.execute(
                    "INSERT INTO playlists (name) VALUES (?)", (name,)
                )
        except sqlite3.IntegrityError:
            return None
        return cursor.lastrowid

    def rename_playlist(self, playlist_id, name):
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE playlists SET name = ? WHERE id = ?", (name, playlist_id)
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def delete_playlist(self, playlist_id):
        with self.conn:
            self.conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))

    def get_playlists(self):
        return self.conn.execute(
            "SELECT p.id, p.name, COUNT(pt.track_id) AS track_count "
            "FROM playlists p LEFT JOIN playlist_tracks pt ON pt.playlist_id = p.id "
            "GROUP BY p.id ORDER BY py_lower(p.name)"
        ).fetchall()

    def add_track_to_playlist(self, playlist_id, track_id):
        with self.conn:
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id, position) "
                "SELECT ?, ?, COALESCE(MAX(position), 0) + 1 "
                "FROM playlist_tracks WHERE playlist_id = ?",
                (playlist_id, track_id, playlist_id),
            )
        return cursor.rowcount > 0

    def remove_track_from_playlist(self, playlist_id, track_id):
        with self.conn:
            self.conn.execute(
                "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
                (playlist_id, track_id),
            )

    def get_playlist_tracks(self, playlist_id):
        return self.conn.execute(
            "SELECT t.* FROM playlist_tracks pt "
            "JOIN tracks t ON t.id = pt.track_id "
            "WHERE pt.playlist_id = ? ORDER BY pt.position",
            (playlist_id,),
        ).fetchall()

    def move_track_in_playlist(self, playlist_id, track_id, offset):
        ids = [row["id"] for row in self.get_playlist_tracks(playlist_id)]
        if track_id not in ids:
            return None
        old = ids.index(track_id)
        new = old + offset
        if not 0 <= new < len(ids):
            return None
        ids.insert(new, ids.pop(old))
        with self.conn:
            for position, tid in enumerate(ids, start=1):
                self.conn.execute(
                    "UPDATE playlist_tracks SET position = ? "
                    "WHERE playlist_id = ? AND track_id = ?",
                    (position, playlist_id, tid),
                )
        return new

    def log_play(self, track_id, seconds_listened, played_at=None):
        played_at = played_at or datetime.now().strftime(TIME_FORMAT)
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO play_history (track_id, played_at, seconds_listened) "
                "SELECT ?, ?, ? WHERE EXISTS (SELECT 1 FROM tracks WHERE id = ?)",
                (track_id, played_at, seconds_listened, track_id),
            )
        return cursor.lastrowid if cursor.rowcount > 0 else None

    def update_play_seconds(self, play_id, seconds_listened):
        with self.conn:
            self.conn.execute(
                "UPDATE play_history SET seconds_listened = ? WHERE id = ?",
                (seconds_listened, play_id),
            )

    def get_top_tracks(self, period="all", limit=10, now=None):
        since = period_start(period, now)
        return self.conn.execute(
            "SELECT t.id, t.title, t.artist, "
            "       COUNT(h.id) AS plays, SUM(h.seconds_listened) AS total_sec "
            "FROM play_history h JOIN tracks t ON t.id = h.track_id "
            "WHERE ? IS NULL OR h.played_at >= ? "
            "GROUP BY t.id ORDER BY plays DESC, total_sec DESC LIMIT ?",
            (since, since, limit),
        ).fetchall()

    def get_total_seconds(self, period="all", now=None):
        since = period_start(period, now)
        row = self.conn.execute(
            "SELECT COALESCE(SUM(seconds_listened), 0) AS total FROM play_history "
            "WHERE ? IS NULL OR played_at >= ?",
            (since, since),
        ).fetchone()
        return row["total"]

    def close(self):
        self.conn.close()
