"""Contrat de la page Membres : types échangés entre l'interface et les services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


class MemberStatus:
    ACTIF = "actif"
    DECEDE = "decede"


@dataclass(frozen=True)
class MemberInfo:
    carnet: str           # « 0001 »
    id: int               # ID en base pour les modifications
    name: str
    sex: str              # 'M' | 'F'
    joined_on: date
    status: str           # MemberStatus
    du: int               # montant dû sur l'exercice
    recu: int             # montant reçu sur l'exercice


@dataclass(frozen=True)
class MembersData:
    exercise_label: str
    is_open: bool
    members: tuple[MemberInfo, ...]


class MembersPort(Protocol):
    """Liste des membres : MockMembers aujourd'hui, services demain."""

    def load(self, exercise_label: str) -> MembersData: ...

    def add_member(self, nom: str, sexe: str, date_adhesion: str) -> int: ...

    def update_member(self, membre_id: int, nom: str, date_adhesion: str) -> None: ...

    def delete_member(self, membre_id: int) -> None: ...

    def declare_deceased(self, membre_id: int, date_deces: str) -> None: ...
