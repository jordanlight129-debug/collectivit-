"""Contrat de la page Paramètres."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Parameter:
    """Paramètre de configuration."""
    key: str
    value: str
    description: str


@dataclass(frozen=True)
class SettingsData:
    exercise_label: str
    parameters: tuple[Parameter, ...]


class SettingsPort(Protocol):
    def load(self, exercise_label: str) -> SettingsData: ...
    def get_parameter(self, key: str, default: str = "") -> str: ...
    def set_parameter(self, key: str, value: str) -> None: ...
