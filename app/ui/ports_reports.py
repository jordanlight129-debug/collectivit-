"""Contrat de la page Rapports et exports."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ReportsData:
    exercise_label: str
    is_open: bool


class ReportsPort(Protocol):
    def load(self, exercise_label: str) -> ReportsData: ...