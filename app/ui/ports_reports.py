"""Contrat de la page Rapports et exports."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ReportsData:
    exercise_label: str
    is_open: bool


class ReportsPort(Protocol):
    def load(self, exercise_label: str) -> ReportsData: ...
    def export_report(self, exercise_label: str, report_key: str, file_format: str) -> Path: ...