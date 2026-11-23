from PyQt6 import uic
from PyQt6.QtWidgets import QWidget

from core.formatting import format_hours_minutes
from paths import resource_path
from windows.common import fill_table, setup_table

UI_FILE = resource_path("ui", "stats_window.ui")
HEADERS = ["№", "Трек", "Исполнитель", "Прослушиваний", "Время"]
RIGHT_COLUMNS = (0, 3, 4)
PERCENT = 100


class StatsWindow(QWidget):
    def __init__(self, db):
        super().__init__()
        uic.loadUi(str(UI_FILE), self)
        self.db = db
        self._tabs = {
            "day": (self.dayTotalLabel, self.dayTable, self.dayShareLabel, self.dayShareBar),
            "week": (self.weekTotalLabel, self.weekTable, self.weekShareLabel, self.weekShareBar),
            "all": (self.allTotalLabel, self.allTable, self.allShareLabel, self.allShareBar),
        }
        for _, table, _, _ in self._tabs.values():
            setup_table(table, HEADERS, stretch_columns=(1, 2))

    def load_data(self):
        for period, widgets in self._tabs.items():
            self._fill_tab(period, *widgets)

    def _fill_tab(self, period, total_label, table, share_label, share_bar):
        top = self.db.get_top_tracks(period)
        total = self.db.get_total_seconds(period)
        total_label.setText(f"Всего прослушано: {format_hours_minutes(total)}")
        rows = [
            [place, t["title"], t["artist"], t["plays"], format_hours_minutes(t["total_sec"])]
            for place, t in enumerate(top, start=1)
        ]
        fill_table(table, rows, right_columns=RIGHT_COLUMNS)
        if top and total:
            share = round(top[0]["total_sec"] * PERCENT / total)
            share_label.setText(f"Доля времени самого популярного трека («{top[0]['title']}»):")
        else:
            share = 0
            share_label.setText("За этот период ничего не прослушано.")
        share_bar.setValue(min(share, PERCENT))
