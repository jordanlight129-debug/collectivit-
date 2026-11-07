"""Présentateur de la page Sauvegardes."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.ui.ports_backups import BackupsData, BackupsPort
from app.ui.views.backups import BackupsView


class BackupsPresenter(QObject):
    backup_created = Signal(str)
    backup_failed = Signal(str)
    backup_restored = Signal(str)
    restore_failed = Signal(str)

    def __init__(self, view: BackupsView, port: BackupsPort, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        self._port = port
        self._exercise_label = ""

    def show_exercise(self, exercise_label: str) -> None:
        self._exercise_label = exercise_label
        data = self._port.load(exercise_label)
        self._view.set_model(data)

    def create_backup(self) -> None:
        try:
            message = self._port.create_backup()
            self.show_exercise(self._exercise_label)
        except Exception as error:
            self.backup_failed.emit(str(error))
            return
        self.backup_created.emit(message)

    def restore_backup(self, filename: str) -> None:
        try:
            message = self._port.restore_backup(filename)
        except Exception as error:
            self.restore_failed.emit(str(error))
            return
        self.show_exercise(self._exercise_label)
        self.backup_restored.emit(message)
