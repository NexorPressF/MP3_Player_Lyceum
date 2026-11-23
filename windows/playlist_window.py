from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget

from core.formatting import format_hours_minutes, format_seconds
from core.library import add_files_to_library
from data.exchange import export_playlist_csv, read_paths_txt
from paths import resource_path
from windows.common import (
    confirm, fill_table, selected_rows, setup_table, wait_cursor,
)

UI_FILE = resource_path("ui", "playlist_window.ui")
HEADERS = ["№", "Название", "Исполнитель", "Длительность"]
NUMBER_COLUMN = 0
DURATION_COLUMN = 3
NAME_EXISTS = "Плейлист с таким названием уже есть."


class PlaylistWindow(QWidget):
    play_requested = pyqtSignal(object, int)
    library_changed = pyqtSignal()

    def __init__(self, db):
        super().__init__()
        uic.loadUi(str(UI_FILE), self)
        self.db = db
        self._playlists = []
        self._tracks = []
        setup_table(self.tracksTable, HEADERS, stretch_columns=(1, 2))
        self._connect_signals()

    def _connect_signals(self):
        self.playlistList.currentRowChanged.connect(self.load_tracks)
        self.tracksTable.itemDoubleClicked.connect(self.on_double_clicked)
        self.newButton.clicked.connect(self.on_new)
        self.renameButton.clicked.connect(self.on_rename)
        self.deleteButton.clicked.connect(self.on_delete)
        self.upButton.clicked.connect(self.on_move_up)
        self.downButton.clicked.connect(self.on_move_down)
        self.removeButton.clicked.connect(self.on_remove_track)
        self.playButton.clicked.connect(self.on_play)
        self.exportButton.clicked.connect(self.on_export)
        self.importButton.clicked.connect(self.on_import)

    def load_data(self):
        current = self._current_playlist()
        self._reload(current["id"] if current else None)

    def _reload(self, select_id=None):
        self._playlists = self.db.get_playlists()
        self.playlistList.blockSignals(True)
        self.playlistList.clear()
        selected = 0
        for index, playlist in enumerate(self._playlists):
            self.playlistList.addItem(f"{playlist['name']} ({playlist['track_count']})")
            if playlist["id"] == select_id:
                selected = index
        self.playlistList.setCurrentRow(selected if self._playlists else -1)
        self.playlistList.blockSignals(False)
        self.load_tracks()

    def load_tracks(self):
        playlist = self._current_playlist()
        if playlist is None:
            self._tracks = []
            self.tracksLabel.setText("Выберите плейлист")
        else:
            self._tracks = self.db.get_playlist_tracks(playlist["id"])
            total = sum(track["duration_sec"] for track in self._tracks)
            self.tracksLabel.setText(
                f"«{playlist['name']}»: {len(self._tracks)} тр., "
                f"{format_hours_minutes(total)}"
            )
        rows = [
            [number, t["title"], t["artist"], format_seconds(t["duration_sec"])]
            for number, t in enumerate(self._tracks, start=1)
        ]
        fill_table(self.tracksTable, rows, right_columns=(NUMBER_COLUMN, DURATION_COLUMN))

    def _current_playlist(self):
        row = self.playlistList.currentRow()
        return self._playlists[row] if 0 <= row < len(self._playlists) else None

    def _current_track_row(self):
        rows = selected_rows(self.tracksTable)
        return rows[0] if rows else None

    def on_new(self):
        name, ok = QInputDialog.getText(self, "Новый плейлист", "Название:")
        name = name.strip()
        if not ok or not name:
            return
        playlist_id = self.db.create_playlist(name)
        if playlist_id is None:
            QMessageBox.warning(self, "Новый плейлист", NAME_EXISTS)
            return
        self._reload(playlist_id)

    def on_rename(self):
        playlist = self._current_playlist()
        if playlist is None:
            QMessageBox.information(self, "Переименовать", "Выберите плейлист.")
            return
        name, ok = QInputDialog.getText(
            self, "Переименовать", "Новое название:", text=playlist["name"]
        )
        name = name.strip()
        if not ok or not name:
            return
        if not self.db.rename_playlist(playlist["id"], name):
            QMessageBox.warning(self, "Переименовать", NAME_EXISTS)
            return
        self._reload(playlist["id"])

    def on_delete(self):
        playlist = self._current_playlist()
        if playlist is None:
            QMessageBox.information(self, "Удаление", "Выберите плейлист.")
            return
        question = f"Удалить плейлист «{playlist['name']}»?\nТреки останутся в библиотеке."
        if confirm(self, "Удаление", question):
            self.db.delete_playlist(playlist["id"])
            self._reload()

    def on_move_up(self):
        self._move(-1)

    def on_move_down(self):
        self._move(1)

    def _move(self, offset):
        playlist, row = self._current_playlist(), self._current_track_row()
        if playlist is None or row is None:
            return
        new_row = self.db.move_track_in_playlist(
            playlist["id"], self._tracks[row]["id"], offset
        )
        if new_row is not None:
            self.load_tracks()
            self.tracksTable.selectRow(new_row)

    def on_remove_track(self):
        playlist, row = self._current_playlist(), self._current_track_row()
        if playlist is None or row is None:
            QMessageBox.information(self, "Убрать трек", "Выберите трек в таблице.")
            return
        self.db.remove_track_from_playlist(playlist["id"], self._tracks[row]["id"])
        self._reload(playlist["id"])
        if self._tracks:
            self.tracksTable.selectRow(min(row, len(self._tracks) - 1))

    def on_play(self):
        if self._tracks:
            row = self._current_track_row()
            self.play_requested.emit(self._tracks, row or 0)

    def on_double_clicked(self, item):
        self.play_requested.emit(self._tracks, item.row())

    def on_export(self):
        playlist = self._current_playlist()
        if playlist is None or not self._tracks:
            QMessageBox.information(self, "Экспорт", "Выберите плейлист с треками.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт плейлиста", f"{playlist['name']}.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            count = export_playlist_csv(path, self._tracks)
        except OSError as error:
            QMessageBox.warning(self, "Экспорт", f"Не удалось сохранить файл:\n{error}")
            return
        QMessageBox.information(self, "Экспорт", f"Сохранено треков: {count}.")

    def on_import(self):
        playlist = self._current_playlist()
        if playlist is None:
            QMessageBox.information(self, "Импорт", "Сначала выберите плейлист.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Список путей к MP3 (по одному на строке)", "", "Текст (*.txt)"
        )
        if not path:
            return
        try:
            paths = read_paths_txt(path)
        except OSError as error:
            QMessageBox.warning(self, "Импорт", f"Не удалось прочитать файл:\n{error}")
            return
        with wait_cursor():
            ids, skipped = add_files_to_library(self.db, paths)
            added = sum(self.db.add_track_to_playlist(playlist["id"], i) for i in ids)
        self._reload(playlist["id"])
        self.library_changed.emit()
        QMessageBox.information(
            self, "Импорт",
            f"Добавлено в плейлист: {added}.\nПропущено (нет файла или не MP3): {len(skipped)}.",
        )
