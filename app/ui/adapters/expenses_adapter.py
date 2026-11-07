"""Adaptateur des dépenses : connecte ExpensesPort aux services."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.database.connection import get_connection
from app.repositories import exercices, depenses
from app.services.depense_service import DepenseError, resume, enregistrer_depense, supprimer_depense
from app.security.session import PermissionDenied, Session
from app.ui.ports_expenses import (
    ExpensesData, ExpenseRecord, ExpensesLoadError, ExpensesSaveError,
)


class ExpensesAdapter:
    """Implémente ExpensesPort en utilisant les services."""

    def __init__(self) -> None:
        self._session = Session()

    def load(self, exercise_label: str) -> ExpensesData:
        conn = get_connection()
        try:
            exercice = exercices.get_by_libelle(conn, exercise_label)

            if not exercice:
                raise ExpensesLoadError("L’exercice sélectionné est introuvable.")

            exercice_id = exercice.id
            is_open = exercice.statut == "ouvert"

            # Récupérer les dépenses
            expenses = depenses.list_(conn, exercice_id)

            # Convertir en ExpenseRecord
            records = []
            for ligne in expenses:
                e = ligne.depense
                records.append(ExpenseRecord(
                    id=e.id,
                    date=e.date_depense.isoformat(),
                    label=e.libelle,
                    beneficiary=e.beneficiaire,
                    amount_planned=e.montant_prevu,
                    amount_spent=e.montant_depense,
                ))

            # Totaux
            totals = resume(conn, exercice_id)
            total_planned = totals.prevu
            total_spent = totals.depense

            return ExpensesData(
                exercise_label=exercise_label,
                is_open=is_open,
                total_planned=total_planned,
                total_spent=total_spent,
                records=tuple(records)
            )
        except ExpensesLoadError:
            raise
        except Exception as exc:
            raise ExpensesLoadError(
                "Impossible de charger les dépenses. Vérifiez la base de données puis réessayez."
            ) from exc
        finally:
            conn.close()

    def add_expense(self, exercise_label: str, libelle: str, beneficiaire: str | None,
                    montant_prevu: Decimal, montant_depense: Decimal, date_depense: str) -> int:
        """Ajoute une nouvelle dépense."""
        conn = get_connection()
        try:
            exercice = exercices.get_by_libelle(conn, exercise_label)
            if not exercice:
                raise ExpensesSaveError("L’exercice sélectionné est introuvable.")

            depense_date = date.fromisoformat(date_depense)

            depense = enregistrer_depense(
                conn, self._session, libelle, montant_depense, beneficiaire,
                montant_prevu, depense_date, today=date.today()
            )
        except (DepenseError, PermissionDenied, ExpensesSaveError):
            raise
        except Exception as exc:
            raise ExpensesSaveError(
                "Impossible d’enregistrer la dépense. Vérifiez les informations puis réessayez."
            ) from exc
        finally:
            conn.close()
        return depense.id

    def delete_expense(self, expense_id: int) -> None:
        conn = get_connection()
        try:
            supprimer_depense(conn, self._session, expense_id)
        finally:
            conn.close()
