"""Contrats entre l'interface et le reste de l'application (ports).

Les vues ne connaissent que ces types ; les adaptateurs (mock aujourd'hui, services demain)
les implémentent. Aucune règle métier ici.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


class Role:
    ADMINISTRATEUR = "administrateur"
    SECRETAIRE = "secretaire"


ROLE_LABELS = {Role.ADMINISTRATEUR: "Administrateur", Role.SECRETAIRE: "Secrétaire"}


@dataclass(frozen=True)
class UserInfo:
    identifiant: str
    full_name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMINISTRATEUR

    @property
    def role_label(self) -> str:
        return ROLE_LABELS[self.role]


class LoginStatus:
    OK = "ok"
    REFUSED = "refused"
    LOCKED = "locked"


@dataclass(frozen=True)
class LoginResult:
    status: str
    user: UserInfo | None = None
    message: str = ""


class AuthPort(Protocol):
    """Authentification : aujourd'hui MockAuth, demain un adaptateur sur auth_service."""

    def login(self, identifiant: str, password: str) -> LoginResult: ...

    def logout(self) -> None: ...

    def change_password(self, current_password: str, new_password: str) -> None: ...


@dataclass(frozen=True)
class ExerciseInfo:
    label: str            # « 2025–2026 »
    is_open: bool


@dataclass(frozen=True)
class NotificationInfo:
    title: str
    text: str
    when: str


# ---------- Tableau de bord ----------
@dataclass(frozen=True)
class RubriqueFigures:
    """Chiffres bruts d'une rubrique. du=None : pas de « dû » (reliquats)."""
    key: str
    label: str
    du: int | None
    percu: int


@dataclass(frozen=True)
class PaymentInfo:
    member: str
    label: str            # « Cotisation mensuelle », « Arriérés — cotisation funéraire »…
    paid_on: date
    amount: int
    nature: str           # 'courant' | 'arriere'


@dataclass(frozen=True)
class AlertInfo:
    kind: str             # 'info' | 'warning' | 'danger'
    text: str


@dataclass(frozen=True)
class MonthFigures:
    """Entrées et dépenses d'un mois de l'exercice (graphique)."""
    label: str            # « Sep », « Oct »… « Août »
    entrees: int
    depenses: int


@dataclass(frozen=True)
class OperationInfo:
    """Une ligne de « Dernières opérations ». amount : positif = entrée, négatif = sortie."""
    on: date
    label: str
    rubrique: str         # « Mensuelle », « Funéraire », « Dépense », « Amende »…
    amount: int
    status: str           # 'paye' | 'partiel' | 'attente' | 'reliquat'


@dataclass(frozen=True)
class DebtorInfo:
    member: str
    carnet: str           # « Carnet 009 »
    amount: int


@dataclass(frozen=True)
class DashboardData:
    exercise_label: str
    is_open: bool
    period_start: date
    period_end: date
    active_members: int
    deceased_members: int
    rubriques: tuple[RubriqueFigures, ...]
    expenses: int
    debts_total: int          # somme des dettes individuelles à recouvrer
    debtor_members: int
    payments: tuple[PaymentInfo, ...]
    alerts: tuple[AlertInfo, ...]
    # Ajouts pour la maquette Figma : optionnels, vides tant que l'adaptateur ne les fournit pas.
    monthly: tuple[MonthFigures, ...] = ()
    operations: tuple[OperationInfo, ...] = ()
    debtors: tuple[DebtorInfo, ...] = ()


class DashboardPort(Protocol):
    """Chiffres du tableau de bord : MockDashboard aujourd'hui, services demain."""

    def load(self, exercise_label: str) -> DashboardData: ...