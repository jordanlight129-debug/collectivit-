"""Adaptateur des dépenses : connecte ExpensesPort aux services."""
from __future__ import annotations

import sqlite3
from datetime import date

from app.database.connection import get_connection
from app.repositories import exercices, depenses
from app.services.depense_service import resume, enregistrer_depense
from app.security.session import Session, CurrentUser, Role
from app.ui.ports_expenses import ExpensesData, ExpenseRecord


class ExpensesAdapter:
    """Implémente ExpensesPort en utilisant les services."""

    def __init__(self) -> None:
        pass

    def load(self, exercise_label: str) -> ExpensesData:
        conn = get_connection()
        try:
            from app.repositories import exercices
            exercice = exercices.get_by_libelle(conn, exercise_label)

            if not exercice:
                conn.close()
                return self._empty_data(exercise_label)

            exercice_id = exercice.id
            is_open = exercice.statut == "ouvert"

            # Récupérer les dépenses
            expenses = depenses.list_(conn, exercice_id)

            # Convertir en ExpenseRecord
            records = []
            for e in expenses:
                records.append(ExpenseRecord(
                    id=e.id,
                    date=e.date_depense,
                    label=e.libelle,
                    beneficiary=e.beneficiaire,
                    amount_planned=e.montant_prevu,
                    amount_spent=e.montant_depense,
                ))

            # Totaux
            totals = resume(conn, exercice_id)
            total_planned = totals.prevu
            total_spent = totals.depense

            conn.close()
            return ExpensesData(
                exercise_label=exercise_label,
                is_open=is_open,
                total_planned=total_planned,
                total_spent=total_spent,
                records=tuple(records)
            )
        except Exception as e:
            conn.close()
            print(f"Erreur expenses adapter: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_data(exercise_label)

    def add_expense(self, exercise_label: str, libelle: str, beneficiaire: str | None,
                    montant_prevu: int, montant_depense: int, date_depense: str) -> int:
        """Ajoute une nouvelle dépense."""
        conn = get_connection()
        try:
            exercice = exercices.get_by_libelle(conn, exercise_label)
            if not exercice:
                raise Exception("Exercice introuvable")

            # Créer une session temporaire
            session = Session()
            session.login(CurrentUser(1, "admin", "Administrateur", Role.ADMINISTRATEUR))

            # Convertir la date
            depense_date = date.fromisoformat(date_depense)

            # Enregistrer la dépense
            depense_id = enregistrer_depense(
                conn, session, libelle, montant_depense, beneficiaire,
                None, depense_date, today=date.today()
            )

            conn.commit()
            conn.close()
            return depense_id
        except Exception as e:
            conn.close()
            raise Exception(f"Erreur lors de l'ajout de la dépense: {e}")

    def _empty_data(self, exercise_label: str) -> ExpensesData:
        return ExpensesData(
            exercise_label=exercise_label,
            is_open=True,
            total_planned=0,
            total_spent=0,
            records=()
        )
