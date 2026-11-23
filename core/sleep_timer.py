from PyQt6.QtCore import QObject, QTimer, pyqtSignal

TICK_MS = 1000
SECONDS_IN_MINUTE = 60


class SleepTimer(QObject):
    tick = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._remaining = 0
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._on_tick)

    @property
    def is_active(self):
        return self._timer.isActive()

    def start(self, minutes):
        self._remaining = minutes * SECONDS_IN_MINUTE
        self._timer.start()
        self.tick.emit(self._remaining)

    def cancel(self):
        self._timer.stop()
        self._remaining = 0

    def _on_tick(self):
        self._remaining -= 1
        self.tick.emit(self._remaining)
        if self._remaining <= 0:
            self._timer.stop()
            self.finished.emit()
