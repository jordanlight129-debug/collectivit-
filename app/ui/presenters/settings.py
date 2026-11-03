"""Présentateur de la page Paramètres."""
from __future__ import annotations

from PySide6.QtCore import QObject

from app.ui.ports_settings import SettingsData, SettingsPort
from app.ui.views.settings import SettingsView


class SettingsPresenter(QObject):
    def __init__(self, view: SettingsView, port: SettingsPort, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        self._port = port

    def show_exercise(self, exercise_label: str) -> None:
        data = self._port.load(exercise_label)
        self._view.set_model(data)
