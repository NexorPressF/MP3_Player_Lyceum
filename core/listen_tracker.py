MIN_LOG_SECONDS = 30
MAX_STEP_MS = 2000
MS_IN_SECOND = 1000


class ListenTracker:
    def __init__(self):
        self._listened_ms = 0
        self._last_position = None

    def reset(self):
        self._listened_ms = 0
        self._last_position = None

    def update(self, position_ms):
        if self._last_position is not None:
            step = position_ms - self._last_position
            if 0 < step <= MAX_STEP_MS:
                self._listened_ms += step
        self._last_position = position_ms

    @property
    def listened_seconds(self):
        return self._listened_ms // MS_IN_SECOND

    @property
    def is_loggable(self):
        return self.listened_seconds >= MIN_LOG_SECONDS
