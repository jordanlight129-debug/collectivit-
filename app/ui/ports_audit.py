"""Contrat de la page Journal d'audit."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AuditLog:
    """Entrée du journal d'audit."""
    id: int
    date: str
    user: str
    action: str
    entity: str
    details: str


@dataclass(frozen=True)
class AuditData:
    exercise_label: str
    logs: tuple[AuditLog, ...]


class AuditPort(Protocol):
    def load(self, exercise_label: str) -> AuditData: ...
