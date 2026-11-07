"""Contrat de la page Cotisations funéraires : types échangés entre l'interface et les services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class DeathRecord:
    id: int
    deceased_name: str
    death_type: str
    death_date: str
    member_carnet: str | None
    amount_man: int
    amount_woman: int
    total_collected: int
    total_expected: int
    exempted: bool


@dataclass(frozen=True)
class FuneralCellInfo:
    status: str
    due: int
    paid: int
    reason: str | None = None


@dataclass(frozen=True)
class FuneralMemberInfo:
    id: int
    carnet: str
    name: str
    cells: tuple[FuneralCellInfo, ...]
    due: int
    paid: int
    debt: int


@dataclass(frozen=True)
class FuneralData:
    exercise_label: str
    is_open: bool
    records: tuple[DeathRecord, ...]
    members: tuple[FuneralMemberInfo, ...] = ()
    total_members: int = 0
    total_due: int = 0
    total_paid: int = 0
    total_debt: int = 0


class FuneralPort(Protocol):
    """Données des cotisations funéraires : MockFuneral aujourd'hui, services demain."""

    def load(self, exercise_label: str) -> FuneralData: ...

    def create_collection(self, nom_defunt: str, type_deces: str, date_deces: str,
                          membre_defunt_id: int | None = None,
                          membre_endeuille_id: int | None = None,
                          exempter_endeuille: bool = False) -> int: ...

    def record_payment(self, exercise_label: str, membre_id: int, montant: int,
                       date_versement: str, mode: str = "global", note: str = "",
                       confirmer_excedent: bool = False) -> int: ...
