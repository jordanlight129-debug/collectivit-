"""Adaptateur des paramètres : connecte aux services de paramètres."""
from __future__ import annotations

from app.database.connection import get_connection
from app.models.sexe import Sexe
from app.repositories import exercices
from app.security.session import Permission, Session
from app.services import exercice_service, user_service
from app.ui.ports_settings import ManagedUser, SettingsData, Parameter


class SettingsAdapter:
    """Implémente l'interface pour les paramètres."""

    def __init__(self) -> None:
        self._session = Session()

    def set_session(self, session: Session) -> None:
        self._session = session

    def load(self, exercise_label: str) -> SettingsData:
        """Charge les paramètres."""
        conn = get_connection()
        try:
            params = conn.execute("SELECT cle, valeur FROM parametres").fetchall()
            exercice = exercices.get_by_libelle(conn, exercise_label)

            # Paramètres par défaut avec descriptions
            default_params = {
                "association_name": "Nom de l'association",
                "brand_initials": "Initiales de la marque",
                "default_tarif_homme": "Tarif mensuel par défaut (hommes)",
                "default_tarif_femme": "Tarif mensuel par défaut (femmes)",
            }

            parameters = []
            for row in params:
                key = row["cle"]
                value = row["valeur"]
                description = default_params.get(key, "")
                parameters.append(Parameter(key=key, value=value, description=description))

            monthly = exercice_service.get_tarifs(conn, exercice.id) if exercice else {}
            funeral = exercice_service.get_funeral_tarifs(conn, exercice.id) if exercice else {}
            users = ()
            if self._session.can(Permission.USERS_MANAGE):
                users = tuple(
                    ManagedUser(user.id, user.identifiant, user.nom_complet, user.role, user.actif)
                    for user in user_service.list_users(conn, self._session)
                )
            return SettingsData(
                exercise_label=exercise_label,
                parameters=tuple(parameters),
                is_open=bool(exercice and exercice.statut == "ouvert"),
                monthly_men=monthly.get(Sexe.HOMME, 0),
                monthly_women=monthly.get(Sexe.FEMME, 0),
                funeral_men=funeral.get(Sexe.HOMME, 0),
                funeral_women=funeral.get(Sexe.FEMME, 0),
                users=users,
            )
        except Exception as e:
            print(f"Erreur settings adapter: {e}")
            import traceback
            traceback.print_exc()
            return SettingsData(
                exercise_label=exercise_label,
                parameters=()
            )
        finally:
            conn.close()

    def get_parameter(self, key: str, default: str = "") -> str:
        """Récupère un paramètre."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT valeur FROM parametres WHERE cle = ?", (key,)).fetchone()
            conn.close()
            return row[0] if row else default
        except Exception:
            conn.close()
            return default

    def set_parameter(self, key: str, value: str) -> None:
        """Définit un paramètre."""
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO parametres (cle, valeur) VALUES (?, ?) "
                "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
                (key, value)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            conn.close()
            raise Exception(f"Erreur lors de la sauvegarde du paramètre: {e}")

    def set_tariffs(self, exercise_label: str, monthly_men: int, monthly_women: int,
                    funeral_men: int, funeral_women: int) -> None:
        conn = get_connection()
        try:
            exercice = exercices.get_by_libelle(conn, exercise_label)
            if exercice is None:
                raise ValueError(f"Exercice introuvable : {exercise_label}")
            exercice_service.set_tarifs(
                conn, self._session, exercice.id, monthly_men, monthly_women)
            exercice_service.set_funeral_tarifs(
                conn, self._session, exercice.id, funeral_men, funeral_women)
        finally:
            conn.close()

    def create_secretary(self, identifiant: str, nom_complet: str, password: str) -> None:
        conn = get_connection()
        try:
            user_service.creer_secretaire(conn, self._session, identifiant, nom_complet, password)
        finally:
            conn.close()

    def set_user_active(self, user_id: int, actif: bool) -> None:
        conn = get_connection()
        try:
            user_service.set_actif(conn, self._session, user_id, actif)
        finally:
            conn.close()

    def reset_user_password(self, user_id: int, password: str) -> None:
        conn = get_connection()
        try:
            user_service.reinitialiser_mot_de_passe(conn, self._session, user_id, password)
        finally:
            conn.close()
