"""Adaptateur des amendes : connecte FinesPort aux services."""
from __future__ import annotations

import sqlite3

from app.database.connection import get_connection
from app.repositories import exercices, amendes, membres
from app.ui.ports_fines import FinesData, FineRecord


class FinesAdapter:
    """Implémente FinesPort en utilisant les services."""

    def __init__(self) -> None:
        pass

    def load(self, exercise_label: str) -> FinesData:
        conn = get_connection()
        try:
            from app.repositories import exercices
            exercice = exercices.get_by_libelle(conn, exercise_label)

            if not exercice:
                conn.close()
                return self._empty_data(exercise_label)

            exercice_id = exercice.id
            is_open = exercice.statut == "ouvert"

            # Récupérer les amendes
            fines = amendes.list_(conn, exercice_id)

            # Convertir en FineRecord
            records = []
            for f in fines:
                membre = membres.get(conn, f.membre_id)

                records.append(FineRecord(
                    id=f.id,
                    member_carnet=membre.numero_carnet if membre else "—",
                    member_name=membre.nom if membre else f.nom,
                    label=f.libelle,
                    date=f.date_amende,
                    amount_expected=f.montant_attendu,
                    amount_collected=f.montant_collecte,
                ))

            conn.close()
            return FinesData(
                exercise_label=exercise_label,
                is_open=is_open,
                records=tuple(records)
            )
        except Exception as e:
            conn.close()
            print(f"Erreur fines adapter: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_data(exercise_label)

    def _empty_data(self, exercise_label: str) -> FinesData:
        return FinesData(
            exercise_label=exercise_label,
            is_open=True,
            records=()
        )
