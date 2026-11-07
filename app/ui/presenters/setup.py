"""Présentateur de l'écran de premier démarrage."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.services.auth_service import create_first_admin, AuthError
from app.security.passwords import validate_policy
from app.ui.views.setup import SetupView


class SetupPresenter(QObject):
    setup_completed = Signal()

    def __init__(self, view: SetupView, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        view.submitted.connect(self._create_admin)

    def _create_admin(self, identifiant: str, nom_complet: str, mot_de_passe: str) -> None:
        identifiant = identifiant.strip()
        nom_complet = nom_complet.strip()
        mot_de_passe = mot_de_passe.strip()

        # Validation des champs
        errors = {}
        if not identifiant:
            errors["identifiant"] = "L'identifiant est obligatoire"
        if not nom_complet:
            errors["nom"] = "Le nom complet est obligatoire"
        if not mot_de_passe:
            errors["password"] = "Le mot de passe est obligatoire"
        if mot_de_passe and len(mot_de_passe) < 8:
            errors["password"] = "Le mot de passe doit contenir au moins 8 caractères"
        if mot_de_passe and mot_de_passe != self._view.mot_de_passe_confirmation.text():
            errors["confirmation"] = "Les mots de passe ne correspondent pas"

        if errors:
            self._view.show_field_errors(
                errors.get("identifiant"),
                errors.get("nom"),
                errors.get("password"),
                errors.get("confirmation")
            )
            return

        # Validation de la politique de mot de passe
        try:
            validate_policy(mot_de_passe)
        except Exception as e:
            self._view.show_field_errors(None, None, str(e), None)
            return

        # Création de l'administrateur
        self._view.set_busy(True)
        try:
            from app.database.connection import get_connection, transaction

            conn = get_connection()
            with transaction(conn):
                user_id = create_first_admin(conn, identifiant, nom_complet, mot_de_passe)
            conn.commit()
            conn.close()

            self._view.set_busy(False)
            # Signal de succès
            self.setup_completed.emit()

        except AuthError as e:
            self._view.set_busy(False)
            self._view.show_error(str(e))
        except Exception as e:
            self._view.set_busy(False)
            self._view.show_error(f"Erreur lors de la création : {e}")
