"""Présentateur de la page Rapports."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.ui.ports_reports import ReportsData, ReportsPort
from app.ui.views.reports import ReportsView


class ReportsPresenter(QObject):
    export_completed = Signal(str)
    export_failed = Signal(str)

    def __init__(self, view: ReportsView, port: ReportsPort, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        self._port = port
        self._exercise_label = ""

    def show_exercise(self, exercise_label: str) -> None:
        self._exercise_label = exercise_label
        data = self._port.load(exercise_label)
        self._view.set_model(data)

    def export_report(self, report_key: str, file_format: str) -> None:
        try:
            path = self._port.export_report(self._exercise_label, report_key, file_format)
        except Exception as error:
            self.export_failed.emit(str(error))
            return
        self.export_completed.emit(str(path))
