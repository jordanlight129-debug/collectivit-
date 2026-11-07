"""Contrat de la page Sauvegardes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BackupInfo:
    """Informations sur une sauvegarde."""
    filename: str
    date: str
    size: str
    kind: str = "manuelle"
    status: str = "Vérifiée"


@dataclass(frozen=True)
class BackupsData:
    exercise_label: str
    backups: tuple[BackupInfo, ...]
    database_size: str = "—"


class BackupsPort(Protocol):
    def load(self, exercise_label: str) -> BackupsData: ...
    def create_backup(self) -> str: ...
    def restore_backup(self, filename: str) -> str: ...
