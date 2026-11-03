"""Présentateur de la page Journal d'audit."""
from __future__ import annotations

from PySide6.QtCore import QObject

from app.ui.ports_audit import AuditData, AuditPort
from app.ui.views.audit import AuditView


class AuditPresenter(QObject):
    def __init__(self, view: AuditView, port: AuditPort, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        self._port = port

    def show_exercise(self, exercise_label: str) -> None:
        data = self._port.load(exercise_label)
        self._view.set_model(data)
