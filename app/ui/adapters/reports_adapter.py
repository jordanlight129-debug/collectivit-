"""Adaptateur des rapports : connecte ReportsPort aux services."""
from __future__ import annotations

from app.database.connection import get_connection
from app.repositories import exercices
from app.ui.ports_reports import ReportsData


class ReportsAdapter:
    """Implémente ReportsPort en utilisant les services."""

    def __init__(self) -> None:
        pass

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