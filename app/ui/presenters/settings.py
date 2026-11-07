"""Présentateur de la page Paramètres."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.ui.ports_settings import SettingsData, SettingsPort
from app.ui.views.settings import SettingsView


class SettingsPresenter(QObject):
    saved = Signal()
    save_failed = Signal(str)
    user_operation_completed = Signal(str)

    def __init__(self, view: SettingsView, port: SettingsPort, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        self._port = port
        self._exercise_label = ""

    def show_exercise(self, exercise_label: str) -> None:
        self._exercise_label = exercise_label
        data = self._port.load(exercise_label)
        self._view.set_model(data)

    def save_tariffs(self, monthly_men: int, monthly_women: int,
                     funeral_men: int, funeral_women: int) -> None:
        try:
            self._port.set_tariffs(self._exercise_label, monthly_men, monthly_women,
                                   funeral_men, funeral_women)
            self.show_exercise(self._exercise_label)
        except Exception as error:
            self.save_failed.emit(str(error))
            return
        self.saved.emit()

    def create_secretary(self, identifiant: str, nom_complet: str, password: str) -> None:
        try:
            self._port.create_secretary(identifiant, nom_complet, password)
            self.show_exercise(self._exercise_label)
        except Exception as error:
            self.save_failed.emit(str(error))
            return
        self._view.clear_secretary_form()
        self.user_operation_completed.emit(f"Compte créé pour {identifiant.strip().lower()}.")

    def set_user_active(self, user_id: int, actif: bool) -> None:
        try:
            self._port.set_user_active(user_id, actif)
            self.show_exercise(self._exercise_label)
        except Exception as error:
            self.save_failed.emit(str(error))
            return
        self.user_operation_completed.emit("Compte activé." if actif else "Compte désactivé.")

    def reset_user_password(self, user_id: int, password: str) -> None:
        try:
            self._port.reset_user_password(user_id, password)
            self.show_exercise(self._exercise_label)
        except Exception as error:
            self.save_failed.emit(str(error))
            return
        self.user_operation_completed.emit("Mot de passe réinitialisé et compte déverrouillé.")
