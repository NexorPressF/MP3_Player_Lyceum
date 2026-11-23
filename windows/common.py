from contextlib import contextmanager

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QHeaderView, QMessageBox, QTableWidgetItem,
)

from paths import resource_path


def icon(name):
    return QIcon(str(resource_path("assets", f"{name}.png")))


@contextmanager
def wait_cursor():
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


def confirm(parent, title, text):
    answer = QMessageBox.question(
        parent, title, text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return answer == QMessageBox.StandardButton.Yes


def setup_table(table, headers, stretch_columns=(0,), multi_select=False):
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    mode = (QAbstractItemView.SelectionMode.ExtendedSelection if multi_select
            else QAbstractItemView.SelectionMode.SingleSelection)
    table.setSelectionMode(mode)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    header = table.horizontalHeader()
    for column in range(len(headers)):
        resize = (QHeaderView.ResizeMode.Stretch if column in stretch_columns
                  else QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(column, resize)


def fill_table(table, rows, right_columns=()):
    table.setRowCount(len(rows))
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if column in right_columns:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            table.setItem(row, column, item)


def selected_rows(table):
    return sorted({item.row() for item in table.selectedItems()})
