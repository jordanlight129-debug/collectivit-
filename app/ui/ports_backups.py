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


@dataclass(frozen=True)
class BackupsData:
    exercise_label: str
    backups: tuple[BackupInfo, ...]


class BackupsPort(Protocol):
    def load(self, exercise_label: str) -> BackupsData: ...
    def create_backup(self) -> str: ...
