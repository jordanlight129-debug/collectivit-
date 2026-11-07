"""Contrat de la page Cotisations parallèles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ParallelMemberInfo:
    id: int
    carnet: str
    name: str
    sex: str
    expected: int
    collected: int
    debt: int
    status: str


@dataclass(frozen=True)
class ParallelSubscription:
    id: int
    name: str
    start_date: str
    end_date: str
    amount_man: int
    amount_woman: int
    total_collected: int
    total_expected: int
    members: tuple[ParallelMemberInfo, ...] = ()


@dataclass(frozen=True)
class ParallelData:
    exercise_label: str
    is_open: bool
    subscriptions: tuple[ParallelSubscription, ...]


class ParallelPort(Protocol):
    def load(self, exercise_label: str) -> ParallelData: ...

    def add_subscription(self, nom: str, date_debut: str, date_fin: str,
                         montant_homme: int, montant_femme: int) -> int: ...

    def record_payment(self, exercise_label: str, membre_id: int, cotisation_id: int,
                       montant: int, date_versement: str, mode: str = "global", note: str = "",
                       confirmer_excedent: bool = False) -> int: ...
