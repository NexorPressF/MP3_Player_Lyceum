from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget

from core.formatting import format_seconds
from core.library import add_files_to_library, find_mp3_files
from data.database import SORT_ORDERS
from paths import resource_path
from windows.common import (
    confirm, fill_table, selected_rows, setup_table, wait_cursor,
)

UI_FILE = resource_path("ui", "library_window.ui")
HEADERS = ["Название", "Исполнитель", "Альбом", "Длительность"]
DURATION_COLUMN = 3


class LibraryWindow(QWidget):
    play_requested = pyqtSignal(object, int)
    library_changed = pyqtSignal()

    def __init__(self, db):
        super().__init__()
        uic.loadUi(str(UI_FILE), self)
        self.db = db
        self._tracks = []
        self.sortCombo.addItems(list(SORT_ORDERS))
        setup_table(self.tracksTable, HEADERS, stretch_columns=(0, 1, 2),
                    multi_select=True)
        self._connect_signals()

    def _connect_signals(self):
        self.searchEdit.textChanged.connect(self.load_data)
        self.sortCombo.currentIndexChanged.connect(self.load_data)
        self.tracksTable.itemDoubleClicked.connect(self.on_double_clicked)
        self.addFilesButton.clicked.connect(self.on_add_files)
        self.addFolderButton.clicked.connect(self.on_add_folder)
        self.editButton.clicked.connect(self.on_edit)
        self.deleteButton.clicked.connect(self.on_delete)
        self.toPlaylistButton.clicked.connect(self.on_add_to_playlist)
        self.playButton.clicked.connect(self.on_play)

    def load_data(self):
        self._tracks = self.db.get_tracks(
            self.searchEdit.text(), self.sortCombo.currentText()
        )
        rows = [
            [t["title"], t["artist"], t["album"] or "", format_seconds(t["duration_sec"])]
            for t in self._tracks
        ]
        fill_table(self.tracksTable, rows, right_columns=(DURATION_COLUMN,))
        self.countLabel.setText(f"Треков: {len(self._tracks)}")

    def on_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Выберите MP3", "", "MP3 (*.mp3)"
        )
        self._import(paths)

    def on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с музыкой")
        if not folder:
            return
        paths = find_mp3_files(folder)
        if not paths:
            QMessageBox.information(self, "Добавление", "В этой папке нет MP3-файлов.")
            return
        self._import(paths)

    def _import(self, paths):
        if not paths:
            return
        with wait_cursor():
            ids, skipped = add_files_to_library(self.db, paths)
        self.load_data()
        self.library_changed.emit()
        text = f"Добавлено треков: {len(ids)}."
        if skipped:
            text += f"\nПропущено: {len(skipped)} (файла нет или это не MP3)."
        QMessageBox.information(self, "Добавление", text)

    def on_edit(self):
        rows = selected_rows(self.tracksTable)
        if len(rows) != 1:
            QMessageBox.information(self, "Изменить", "Выберите один трек.")
            return
        track = self._tracks[rows[0]]
        title, ok = QInputDialog.getText(
            self, "Изменить трек", "Название:", text=track["title"]
        )
        if not ok:
            return
        artist, ok = QInputDialog.getText(
            self, "Изменить трек", "Исполнитель:", text=track["artist"]
        )
        if not ok:
            return
        self.db.update_track(
            track["id"], title.strip() or track["title"], artist.strip() or track["artist"]
        )
        self.load_data()
        self.library_changed.emit()

    def on_delete(self):
        rows = selected_rows(self.tracksTable)
        if not rows:
            QMessageBox.information(self, "Удаление", "Выберите треки для удаления.")
            return
        question = (f"Удалить из библиотеки выбранные треки ({len(rows)})?\n"
                    "Сами файлы на диске останутся.")
        if not confirm(self, "Удаление", question):
            return
        for row in rows:
            self.db.delete_track(self._tracks[row]["id"])
        self.load_data()
        self.library_changed.emit()

    def on_add_to_playlist(self):
        rows = selected_rows(self.tracksTable)
        if not rows:
            QMessageBox.information(self, "В плейлист", "Выберите треки.")
            return
        playlists = self.db.get_playlists()
        if not playlists:
            QMessageBox.information(
                self, "В плейлист", "Сначала создайте плейлист в окне «Плейлисты»."
            )
            return
        names = [playlist["name"] for playlist in playlists]
        name, ok = QInputDialog.getItem(
            self, "В плейлист", "Выберите плейлист:", names, 0, False
        )
        if not ok:
            return
        playlist_id = playlists[names.index(name)]["id"]
        added = sum(
            self.db.add_track_to_playlist(playlist_id, self._tracks[row]["id"])
            for row in rows
        )
        QMessageBox.information(
            self, "В плейлист",
            f"Добавлено: {added} из {len(rows)} (остальные уже были в плейлисте).",
        )

    def on_play(self):
        rows = selected_rows(self.tracksTable)
        if self._tracks:
            self.play_requested.emit(self._tracks, rows[0] if rows else 0)

    def on_double_clicked(self, item):
        self.play_requested.emit(self._tracks, item.row())
