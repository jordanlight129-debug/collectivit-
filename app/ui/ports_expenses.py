"""Contrat de la page Dépenses."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class ExpensesLoadError(RuntimeError):
    """Échec récupérable lors du chargement des dépenses pour l'interface."""


class ExpensesSaveError(RuntimeError):
    """Échec récupérable lors de l'enregistrement d'une dépense."""


@dataclass(frozen=True)
class ExpenseRecord:
    id: int
    date: str
    label: str
    beneficiary: str | None
    amount_planned: Decimal
    amount_spent: Decimal


@dataclass(frozen=True)
class ExpensesData:
    exercise_label: str
    is_open: bool
    records: tuple[ExpenseRecord, ...]
    total_planned: Decimal
    total_spent: Decimal


class ExpensesPort(Protocol):
    def load(self, exercise_label: str) -> ExpensesData: ...
    def add_expense(self, exercise_label: str, libelle: str, beneficiaire: str | None,
                    montant_prevu: Decimal, montant_depense: Decimal, date_depense: str) -> int: ...
    def delete_expense(self, expense_id: int) -> None: ...
