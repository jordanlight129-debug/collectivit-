"""Adaptateur du journal d'audit : connecte AuditPort au journal d'audit de sécurité."""
from __future__ import annotations

import logging
from contextlib import closing
from datetime import datetime

from app.database.connection import get_connection
from app.security import audit
from app.ui.ports_audit import AuditData, AuditLog

logger = logging.getLogger(__name__)

MAX_ENTREES = 200          # entrées les plus récentes affichées


def _formater_date(date_heure: str | None) -> str:
    """« 2026-11-02 10:15:00 » → « 02/11/2026 10:15 »."""
    if not date_heure:
        return "—"
    try:
        return datetime.fromisoformat(date_heure).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return date_heure


class AuditAdapter:
    """Implémente AuditPort : lit le journal d'audit (table journal_audit, en lecture seule)."""

    def load(self, exercise_label: str) -> AuditData:
        try:
            with closing(get_connection()) as conn:
                lignes = audit.list_entries(conn, limit=MAX_ENTREES)
                logs = tuple(AuditLog(
                    id=row["id"],
                    date=_formater_date(row["date_heure"]),
                    user=row["identifiant"] or "—",
                    action=row["action"],
                    entity=row["objet"] or "—",
                    details=row["detail"] or "",
                ) for row in lignes)
            return AuditData(exercise_label=exercise_label, logs=logs)
        except Exception:
            logger.exception("Chargement du journal d'audit impossible")
            return AuditData(exercise_label=exercise_label, logs=())