"""Présentateur de la page Sauvegardes."""
from __future__ import annotations

from PySide6.QtCore import QObject

from app.ui.ports_backups import BackupsData, BackupsPort
from app.ui.views.backups import BackupsView


class BackupsPresenter(QObject):
    def __init__(self, view: BackupsView, port: BackupsPort, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        self._port = port

    def show_exercise(self, exercise_label: str) -> None:
        data = self._port.load(exercise_label)
        self._view.set_model(data)
