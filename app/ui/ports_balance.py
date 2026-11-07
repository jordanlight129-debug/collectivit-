"""Contrat de la page Bilan financier."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class BalanceData:
    exercise_label: str
    is_open: bool
    period_start: str
    period_end: str
    total_revenue: int
    total_expenses: Decimal
    balance: Decimal
    carried_forward: int
    closing_balance: Decimal


class BalancePort(Protocol):
    def load(self, exercise_label: str) -> BalanceData: ...
