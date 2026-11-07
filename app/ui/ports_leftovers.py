"""Contrat de la page Reliquats."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class LeftoverRecord:
    id: int
    name: str
    expense_label: str
    amount: Decimal
    date: str


@dataclass(frozen=True)
class LeftoversData:
    exercise_label: str
    is_open: bool
    records: tuple[LeftoverRecord, ...]
    total: Decimal


class LeftoversPort(Protocol):
    def load(self, exercise_label: str) -> LeftoversData: ...
