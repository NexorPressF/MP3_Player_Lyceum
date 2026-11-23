from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFileDialog, QInputDialog, QLabel, QMainWindow, QMessageBox,
)

from core.audio_player import AudioPlayer
from core.formatting import format_ms, format_seconds
from core.library import add_files_to_library, find_mp3_files
from core.listen_tracker import ListenTracker
from core.play_queue import PlayQueue, RepeatMode
from core.sleep_timer import SleepTimer
from core.tags import read_cover
from paths import resource_path
from windows.common import icon, wait_cursor
from windows.library_window import LibraryWindow
from windows.playlist_window import PlaylistWindow
from windows.stats_window import StatsWindow

UI_FILE = resource_path("ui", "main_window.ui")
COVER_SIZE = 220
STATUS_MS = 3000
RESTART_MS = 3000
SLEEP_DEFAULT_MINUTES = 30
SLEEP_MAX_MINUTES = 600

REPEAT_ICONS = {
    RepeatMode.OFF: "repeat_off",
    RepeatMode.TRACK: "repeat_one",
    RepeatMode.PLAYLIST: "repeat_all",
}
REPEAT_TIPS = {
    RepeatMode.OFF: "Повтор: выключен",
    RepeatMode.TRACK: "Повтор: один трек",
    RepeatMode.PLAYLIST: "Повтор: весь список",
}


class MainWindow(QMainWindow):
    def __init__(self, db, settings):
        super().__init__()
        uic.loadUi(str(UI_FILE), self)
        self.db = db
        self.settings = settings
        self.player = AudioPlayer()
        self.queue = PlayQueue()
        self.tracker = ListenTracker()
        self.sleep_timer = SleepTimer()
        self.current_track = None
        self._play_id = None

        self.library_window = LibraryWindow(db)
        self.playlist_window = PlaylistWindow(db)
        self.stats_window = StatsWindow(db)

        self.sleepLabel = QLabel()
        self.statusbar.addPermanentWidget(self.sleepLabel)
        self.placeholder = QPixmap(str(resource_path("assets", "placeholder.png")))

        self._setup_icons()
        self._connect_signals()
        self._restore_state()

    def _setup_icons(self):
        buttons = {
            self.playButton: "play", self.pauseButton: "pause",
            self.stopButton: "stop", self.nextButton: "next",
            self.prevButton: "prev", self.shuffleButton: "shuffle",
            self.repeatButton: REPEAT_ICONS[RepeatMode.OFF],
        }
        for button, name in buttons.items():
            button.setIcon(icon(name))
        self.setWindowIcon(icon("app_icon"))

    def _connect_signals(self):
        self.addFilesAction.triggered.connect(self.on_add_files)
        self.addFolderAction.triggered.connect(self.on_add_folder)
        self.exitAction.triggered.connect(self.close)
        self.libraryAction.triggered.connect(self.open_library)
        self.playlistsAction.triggered.connect(self.open_playlists)
        self.statsAction.triggered.connect(self.open_stats)
        self.sleepTimerAction.triggered.connect(self.on_sleep_timer)
        self.cancelSleepAction.triggered.connect(self.on_cancel_sleep)
        self.playButton.clicked.connect(self.on_play_clicked)
        self.pauseButton.clicked.connect(self.player.pause)
        self.stopButton.clicked.connect(self.on_stop_clicked)
        self.nextButton.clicked.connect(self.on_next_clicked)
        self.prevButton.clicked.connect(self.on_prev_clicked)
        self.shuffleButton.toggled.connect(self.on_shuffle_toggled)
        self.repeatButton.clicked.connect(self.on_repeat_clicked)
        self.volumeSlider.valueChanged.connect(self.on_volume_changed)
        self.seekSlider.sliderMoved.connect(self.player.seek)
        self.queueList.itemDoubleClicked.connect(self.on_queue_item_double_clicked)
        self.player.position_changed.connect(self.on_position_changed)
        self.player.duration_changed.connect(self.on_duration_changed)
        self.player.state_changed.connect(self.on_state_changed)
        self.player.track_finished.connect(self.on_track_finished)
        self.player.error_occurred.connect(self.on_player_error)
        for window in (self.library_window, self.playlist_window):
            window.play_requested.connect(self.on_play_requested)
            window.library_changed.connect(self.on_library_changed)
        self.sleep_timer.tick.connect(self.on_sleep_tick)
        self.sleep_timer.finished.connect(self.on_sleep_finished)

    def _restore_state(self):
        volume = self.settings.volume
        self.volumeSlider.setValue(volume)
        self.on_volume_changed(volume)
        self.on_state_changed(False)
        self._update_sleep_actions()

        tracks = self.db.get_tracks()
        last_id = self.settings.last_track_id
        start = next((i for i, t in enumerate(tracks) if t["id"] == last_id), 0)
        self.queue.set_tracks(tracks, start)
        self._fill_queue_list()
        track = self.queue.current
        if track is not None and track["id"] == last_id and self._load_track(track):
            return
        self._show_track(None)

    def on_play_clicked(self):
        if self.current_track is not None:
            self.player.play()
            return
        track = self.queue.current
        if track is None:
            QMessageBox.information(
                self, "Плеер", "В библиотеке пока нет треков.\n"
                "Добавьте MP3 через меню «Файл»."
            )
            return
        self._play_track(track)

    def on_stop_clicked(self):
        self._finish_listening()
        self.player.stop()

    def on_next_clicked(self):
        track = self.queue.next()
        if track is not None:
            self._play_track(track)

    def on_prev_clicked(self):
        if self.seekSlider.value() > RESTART_MS:
            self.player.seek(0)
            return
        track = self.queue.previous()
        if track is not None:
            self._play_track(track)

    def on_track_finished(self):
        self._finish_listening()
        track = self.queue.next(auto=True)
        if track is not None:
            self._play_track(track)
        else:
            self.statusbar.showMessage("Очередь закончилась", STATUS_MS)

    def on_queue_item_double_clicked(self, item):
        track = self.queue.select(self.queueList.row(item))
        if track is not None:
            self._play_track(track)

    def on_play_requested(self, tracks, index):
        self.queue.set_tracks(tracks, index)
        self._fill_queue_list()
        track = self.queue.current
        if track is not None:
            self._play_track(track)

    def _play_track(self, track):
        if self._load_track(track):
            self.player.play()

    def _load_track(self, track):
        path = track["path"]
        if not Path(path).exists():
            QMessageBox.warning(self, "Файл не найден", f"Файл не найден:\n{path}")
            return False
        self._finish_listening()
        self.current_track = track
        self.player.load(path)
        self.settings.last_track_id = track["id"]
        self._show_track(track)
        self._highlight_current()
        return True

    def on_shuffle_toggled(self, checked):
        self.queue.set_shuffle(checked)
        state = "включён" if checked else "выключен"
        self.statusbar.showMessage(f"Случайный порядок {state}", STATUS_MS)

    def on_repeat_clicked(self):
        mode = self.queue.cycle_repeat()
        self.repeatButton.setIcon(icon(REPEAT_ICONS[mode]))
        self.repeatButton.setToolTip(REPEAT_TIPS[mode])
        self.statusbar.showMessage(REPEAT_TIPS[mode], STATUS_MS)

    def on_volume_changed(self, value):
        self.player.set_volume(value)
        self.volumeValueLabel.setText(f"{value}%")
        self.settings.volume = value

    def on_position_changed(self, ms):
        self.tracker.update(ms)
        self._log_listening_if_needed()
        if not self.seekSlider.isSliderDown():
            self.seekSlider.setValue(ms)
        self.currentTimeLabel.setText(format_ms(ms))

    def on_duration_changed(self, ms):
        self.seekSlider.setRange(0, ms)
        self.totalTimeLabel.setText(format_ms(ms))

    def on_state_changed(self, playing):
        self.playButton.setEnabled(not playing)
        self.pauseButton.setEnabled(playing)

    def on_player_error(self, message):
        QMessageBox.warning(self, "Ошибка воспроизведения", message)

    def _log_listening_if_needed(self):
        if (self._play_id is None and self.current_track is not None
                and self.tracker.is_loggable):
            self._play_id = self.db.log_play(
                self.current_track["id"], self.tracker.listened_seconds
            )

    def _save_listening(self):
        if self._play_id is not None:
            self.db.update_play_seconds(self._play_id, self.tracker.listened_seconds)

    def _finish_listening(self):
        self._save_listening()
        self.tracker.reset()
        self._play_id = None

    def on_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Выберите MP3", "", "MP3 (*.mp3)"
        )
        self._add_and_play(paths)

    def on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с музыкой")
        if not folder:
            return
        paths = find_mp3_files(folder)
        if not paths:
            QMessageBox.information(self, "Добавление", "В этой папке нет MP3-файлов.")
            return
        self._add_and_play(paths)

    def _add_and_play(self, paths):
        if not paths:
            return
        with wait_cursor():
            ids, skipped = add_files_to_library(self.db, paths)
        if skipped:
            QMessageBox.information(
                self, "Добавление",
                f"Пропущено файлов: {len(skipped)} (файла нет или это не MP3).",
            )
        if not ids:
            return
        known = {track["id"] for track in self.queue.tracks}
        self.queue.append([t for t in self.db.get_tracks_by_ids(ids) if t["id"] not in known])
        queue_ids = [track["id"] for track in self.queue.tracks]
        track = self.queue.select(queue_ids.index(ids[0]))
        self._fill_queue_list()
        self.library_window.load_data()
        self._play_track(track)

    def on_library_changed(self):
        ids = [track["id"] for track in self.queue.tracks]
        fresh = self.db.get_tracks_by_ids(ids) or self.db.get_tracks()
        current_id = self.current_track["id"] if self.current_track else None
        index = next((i for i, t in enumerate(fresh) if t["id"] == current_id), 0)
        self.queue.set_tracks(fresh, index)
        self._fill_queue_list()
        if current_id is not None:
            updated = self.db.get_track(current_id)
            if updated is not None:
                self.current_track = updated
                self._show_track(updated)

    def _fill_queue_list(self):
        self.queueList.clear()
        for track in self.queue.tracks:
            self.queueList.addItem(f"{track['artist']} — {track['title']}")
        self._highlight_current()

    def _highlight_current(self):
        self.queueList.setCurrentRow(self.queue.current_index)

    def _show_track(self, track):
        if track is None:
            self.titleLabel.setText("Файл не выбран")
            self.artistLabel.setText("")
            self.albumLabel.setText("")
            self.setWindowTitle("MP3-плеер")
            self._show_cover(None)
            return
        self.titleLabel.setText(track["title"])
        self.artistLabel.setText(track["artist"])
        self.albumLabel.setText(track["album"] or "")
        self.setWindowTitle(f"{track['artist']} — {track['title']} · MP3-плеер")
        self._show_cover(track["path"])

    def _show_cover(self, path):
        pixmap = QPixmap()
        data = read_cover(path) if path else None
        if not (data and pixmap.loadFromData(data)):
            pixmap = self.placeholder
        self.coverLabel.setPixmap(pixmap.scaled(
            COVER_SIZE, COVER_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def open_library(self):
        self._open_window(self.library_window)

    def open_playlists(self):
        self._open_window(self.playlist_window)

    def open_stats(self):
        self._save_listening()
        self._open_window(self.stats_window)

    @staticmethod
    def _open_window(window):
        window.load_data()
        window.show()
        window.raise_()
        window.activateWindow()

    def on_sleep_timer(self):
        minutes, ok = QInputDialog.getInt(
            self, "Таймер сна", "Остановить музыку через (минут):",
            SLEEP_DEFAULT_MINUTES, 1, SLEEP_MAX_MINUTES,
        )
        if ok:
            self.sleep_timer.start(minutes)
            self._update_sleep_actions()

    def on_cancel_sleep(self):
        self.sleep_timer.cancel()
        self.sleepLabel.setText("")
        self._update_sleep_actions()
        self.statusbar.showMessage("Таймер сна отменён", STATUS_MS)

    def on_sleep_tick(self, seconds):
        self.sleepLabel.setText(f"Таймер сна: {format_seconds(seconds)}")

    def on_sleep_finished(self):
        self.sleepLabel.setText("")
        self._update_sleep_actions()
        self.on_stop_clicked()
        self.statusbar.showMessage("Сработал таймер сна: музыка остановлена", STATUS_MS)

    def _update_sleep_actions(self):
        self.cancelSleepAction.setEnabled(self.sleep_timer.is_active)

    def closeEvent(self, event):
        self._finish_listening()
        self.player.stop()
        self.settings.save()
        for window in (self.library_window, self.playlist_window, self.stats_window):
            window.close()
        super().closeEvent(event)
