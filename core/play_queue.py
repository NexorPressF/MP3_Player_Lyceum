import random
from enum import Enum


class RepeatMode(Enum):
    OFF = 0
    TRACK = 1
    PLAYLIST = 2


class PlayQueue:
    def __init__(self):
        self._tracks = []
        self._order = []
        self._pos = -1
        self.shuffle = False
        self.repeat = RepeatMode.OFF

    @property
    def tracks(self):
        return list(self._tracks)

    def __len__(self):
        return len(self._tracks)

    @property
    def current(self):
        if 0 <= self._pos < len(self._order):
            return self._tracks[self._order[self._pos]]
        return None

    @property
    def current_index(self):
        if 0 <= self._pos < len(self._order):
            return self._order[self._pos]
        return -1

    def set_tracks(self, tracks, start_index=0):
        self._tracks = list(tracks)
        if not self._tracks:
            self._order, self._pos = [], -1
            return
        start_index = min(max(start_index, 0), len(self._tracks) - 1)
        self._order = list(range(len(self._tracks)))
        self._pos = start_index
        if self.shuffle:
            self._shuffle_order()

    def append(self, tracks):
        first_new = len(self._tracks)
        self._tracks.extend(tracks)
        self._order.extend(range(first_new, len(self._tracks)))
        if self._pos == -1 and self._tracks:
            self._pos = 0

    def select(self, index):
        if 0 <= index < len(self._tracks):
            self._pos = self._order.index(index)
            return self.current
        return None

    def set_shuffle(self, enabled):
        if enabled == self.shuffle:
            return
        self.shuffle = enabled
        if not self._tracks:
            return
        if enabled:
            self._shuffle_order()
        else:
            current = self.current_index
            self._order = list(range(len(self._tracks)))
            self._pos = current

    def cycle_repeat(self):
        modes = list(RepeatMode)
        self.repeat = modes[(modes.index(self.repeat) + 1) % len(modes)]
        return self.repeat

    def next(self, auto=False):
        if not self._tracks:
            return None
        if auto and self.repeat == RepeatMode.TRACK:
            return self.current
        if self._pos + 1 < len(self._order):
            self._pos += 1
        elif self.repeat == RepeatMode.PLAYLIST:
            if self.shuffle:
                self._shuffle_order(keep_current=False)
            self._pos = 0
        else:
            return None
        return self.current

    def previous(self):
        if not self._tracks:
            return None
        if self._pos > 0:
            self._pos -= 1
        elif self.repeat == RepeatMode.PLAYLIST:
            self._pos = len(self._order) - 1
        return self.current

    def _shuffle_order(self, keep_current=True):
        last = self.current_index
        if keep_current and last >= 0:
            rest = [i for i in range(len(self._tracks)) if i != last]
            random.shuffle(rest)
            self._order = [last] + rest
            self._pos = 0
            return
        order = list(range(len(self._tracks)))
        random.shuffle(order)
        if len(order) > 1 and order[0] == last:
            order[0], order[-1] = order[-1], order[0]
        self._order = order
        self._pos = 0
