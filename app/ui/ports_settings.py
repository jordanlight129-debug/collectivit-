"""Contrat de la page Paramètres."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.security.session import Role


@dataclass(frozen=True)
class Parameter:
    """Paramètre de configuration."""
    key: str
    value: str
    description: str


@dataclass(frozen=True)
class ManagedUser:
    id: int
    identifiant: str
    nom_complet: str
    role: Role
    actif: bool


@dataclass(frozen=True)
class SettingsData:
    exercise_label: str
    parameters: tuple[Parameter, ...]
    is_open: bool = True
    monthly_men: int = 0
    monthly_women: int = 0
    funeral_men: int = 0
    funeral_women: int = 0
    users: tuple[ManagedUser, ...] = ()


class SettingsPort(Protocol):
    def load(self, exercise_label: str) -> SettingsData: ...
    def get_parameter(self, key: str, default: str = "") -> str: ...
    def set_parameter(self, key: str, value: str) -> None: ...
    def set_tariffs(self, exercise_label: str, monthly_men: int, monthly_women: int,
                    funeral_men: int, funeral_women: int) -> None: ...
    def create_secretary(self, identifiant: str, nom_complet: str, password: str) -> None: ...
    def set_user_active(self, user_id: int, actif: bool) -> None: ...
    def reset_user_password(self, user_id: int, password: str) -> None: ...
