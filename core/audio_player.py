from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from core.settings import DEFAULT_VOLUME


class AudioPlayer(QObject):
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    track_finished = pyqtSignal()
    state_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._output)
        self.set_volume(DEFAULT_VOLUME)

        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.playbackStateChanged.connect(self._on_state)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.errorOccurred.connect(self._on_error)

    def load(self, path):
        self._player.setSource(QUrl.fromLocalFile(str(path)))

    def play(self):
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

    def set_volume(self, percent):
        self._output.setVolume(percent / 100)

    def seek(self, ms):
        self._player.setPosition(ms)

    def _on_error(self, error, message):
        self.error_occurred.emit(message)

    def _on_position(self, ms):
        self.position_changed.emit(int(ms))

    def _on_duration(self, ms):
        self.duration_changed.emit(int(ms))

    def _on_state(self, state):
        self.state_changed.emit(state == QMediaPlayer.PlaybackState.PlayingState)

    def _on_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.track_finished.emit()
