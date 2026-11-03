"""Adaptateur des reliquats : connecte LeftoversPort aux services."""
from __future__ import annotations

import sqlite3

from app.database.connection import get_connection
from app.repositories import exercices, reliquats, depenses
from app.ui.ports_leftovers import LeftoversData, LeftoverRecord


class LeftoversAdapter:
    """Implémente LeftoversPort en utilisant les services."""

    def __init__(self) -> None:
        pass

    def load(self, exercise_label: str) -> LeftoversData:
        conn = get_connection()
        try:
            from app.repositories import exercices
            exercice = exercices.get_by_libelle(conn, exercise_label)

            if not exercice:
                conn.close()
                return self._empty_data(exercise_label)

            exercice_id = exercice.id
            is_open = exercice.statut == "ouvert"

            # Récupérer les reliquats
            leftovers = reliquats.list_for_exercice(conn, exercice_id)

            # Convertir en LeftoverRecord
            records = []
            for r in leftovers:
                # Récupérer la dépense associée
                depense = depenses.get(conn, r.depense_id)

                records.append(LeftoverRecord(
                    id=r.id,
                    name=r.nom,
                    expense_label=depense.libelle if depense else "—",
                    amount=r.montant,
                    date=r.date_reliquat,
                ))

            # Total
            total = sum(r.montant for r in leftovers)

            conn.close()
            return LeftoversData(
                exercise_label=exercise_label,
                is_open=is_open,
                total=total,
                records=tuple(records)
            )
        except Exception as e:
            conn.close()
            print(f"Erreur leftovers adapter: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_data(exercise_label)

    def _empty_data(self, exercise_label: str) -> LeftoversData:
        return LeftoversData(
            exercise_label=exercise_label,
            is_open=True,
            total=0,
            records=()
        )
