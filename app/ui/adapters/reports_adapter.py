"""Adaptateur des rapports : connecte ReportsPort aux services."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path

from app.database.connection import get_connection
from app.repositories import exercices
from app.security import audit
from app.security.audit import Action
from app.security.session import Permission, Session
from app.services import export_service
from app.ui.ports_reports import ReportsData


class ReportsAdapter:
    """Implémente ReportsPort en utilisant les services."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session or Session()

    def set_session(self, session: Session) -> None:
        self._session = session

    def load(self, exercise_label: str) -> ReportsData:
        # À implémenter plus tard avec les services de génération de rapports
        conn = get_connection()
        try:
            exercice = exercices.get_by_libelle(conn, exercise_label)
            if not exercice:
                return self._empty_data(exercise_label)
            return ReportsData(
                exercise_label=exercise_label,
                is_open=exercice.statut == "ouvert",
            )
        except Exception as e:
            print(f"Erreur reports adapter: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_data(exercise_label)
        finally:
            conn.close()

    def _empty_data(self, exercise_label: str) -> ReportsData:
        return ReportsData(exercise_label=exercise_label, is_open=True)

    def export_report(self, exercise_label: str, report_key: str, file_format: str) -> Path:
        self._session.require(Permission.EXPORT)
        with closing(get_connection()) as conn:
            path = export_service.export_report(conn, exercise_label, report_key, file_format)
            audit.log(conn, self._session.user, Action.EXPORT, report_key,
                      f"{file_format.upper()} · {path.name} · exercice {exercise_label}")
            conn.commit()
            return path