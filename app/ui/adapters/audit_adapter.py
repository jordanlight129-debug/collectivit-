"""Adaptateur du journal d'audit : connecte aux services d'audit."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from app.database.connection import get_connection
from app.repositories import historique
from app.ui.ports_audit import AuditData, AuditLog


class AuditAdapter:
    """Implémente l'interface pour le journal d'audit."""

    def __init__(self) -> None:
        pass

    def load(self, exercise_label: str) -> AuditData:
        """Charge le journal d'audit."""
        conn = get_connection()
        try:
            # Lister les entrées d'audit
            logs = historique.lister(conn, limit=100)
            conn.close()

            # Convertir en AuditLog
            audit_logs = []
            for log in logs:
                # Formater la date
                date_str = log.date_action.strftime("%d/%m/%Y %H:%M") if log.date_action else "—"

                audit_logs.append(AuditLog(
                    id=log.id,
                    date=date_str,
                    user=log.utilisateur_nom if log.utilisateur_nom else "—",
                    action=log.action,
                    entity=log.entite if log.entite else "—",
                    details=log.details if log.details else ""
                ))

            return AuditData(
                exercise_label=exercise_label,
                logs=tuple(audit_logs)
            )
        except Exception as e:
            conn.close()
            print(f"Erreur audit adapter: {e}")
            import traceback
            traceback.print_exc()
            return AuditData(
                exercise_label=exercise_label,
                logs=()
            )
