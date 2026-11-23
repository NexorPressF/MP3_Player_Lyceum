from PyQt6.QtCore import QSettings

DEFAULT_VOLUME = 50
NO_TRACK = 0


class AppSettings:
    def __init__(self, path):
        self._settings = QSettings(str(path), QSettings.Format.IniFormat)

    @property
    def volume(self):
        return self._settings.value("volume", DEFAULT_VOLUME, type=int)

    @volume.setter
    def volume(self, value):
        self._settings.setValue("volume", int(value))

    @property
    def last_track_id(self):
        track_id = self._settings.value("last_track_id", NO_TRACK, type=int)
        return track_id or None

    @last_track_id.setter
    def last_track_id(self, track_id):
        self._settings.setValue("last_track_id", track_id or NO_TRACK)

    def save(self):
        self._settings.sync()
