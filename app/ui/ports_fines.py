"""Contrat de la page Amendes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FineRecord:
    id: int
    member_carnet: str
    member_name: str
    label: str
    date: str
    amount_expected: int
    amount_collected: int
    remaining: int


@dataclass(frozen=True)
class FinesData:
    exercise_label: str
    is_open: bool
    records: tuple[FineRecord, ...]
    total_expected: int = 0
    total_collected: int = 0


class FinesPort(Protocol):
    def load(self, exercise_label: str) -> FinesData: ...

    def add_fine(self, membre_id: int, nom: str, libelle: str,
                 montant_attendu: int, date_amende: str) -> int: ...

    def collect_fine(self, amende_id: int, montant: int, date_encaissement: str) -> None: ...
