"""Adaptateur des sauvegardes : connecte aux services de backup."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.config import DB_PATH
from app.database.connection import get_connection
from app.security.session import Permission, Session
from app.services.backup_service import (
    BackupError, lister, restaurer, sauvegarder_manuelle, verifier_fichier,
)
from app.ui.ports_backups import BackupsData, BackupInfo


class BackupsAdapter:
    """Implémente l'interface pour les sauvegardes."""

    def __init__(self) -> None:
        self._session = Session()

    def set_session(self, session: Session) -> None:
        self._session = session

    def load(self, exercise_label: str) -> BackupsData:
        """Charge la liste des sauvegardes disponibles."""
        backup_infos = []
        for backup in lister():
            valid, _message = verifier_fichier(backup.path)
            kind = {
                "manuelle": "Manuelle",
                "automatique": "Automatique",
                "securite": "Sécurité",
            }.get(backup.kind, backup.kind.capitalize())
            size = self._format_size(backup.size)
            backup_infos.append(BackupInfo(
                filename=backup.name,
                date=backup.created.strftime("%d/%m/%Y %H:%M"),
                size=size,
                kind=kind,
                status="Vérifiée" if valid else "Invalide",
            ))
        database_size = self._format_size(DB_PATH.stat().st_size) if DB_PATH.exists() else "—"
        return BackupsData(exercise_label, tuple(backup_infos), database_size)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} o"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} Ko"
        return f"{size_bytes / (1024 * 1024):.1f} Mo"

    def create_backup(self) -> str:
        """Crée une sauvegarde manuelle."""
        self._session.require(Permission.BACKUP_MANAGE)
        conn = get_connection()
        try:
            path = sauvegarder_manuelle(conn, self._session)
            return path.name
        finally:
            conn.close()

    def restore_backup(self, filename: str) -> str:
        self._session.require(Permission.BACKUP_MANAGE)
        backup = next((item for item in lister() if item.name == Path(filename).name), None)
        if backup is None or backup.name != filename:
            raise BackupError("Cette sauvegarde n’existe plus. Recharge la liste et réessaie.")
        security_copy = restaurer(self._session, backup.path)
        detail = f"Sauvegarde {backup.name} restaurée."
        if security_copy is not None:
            detail += f" Copie de sécurité créée : {security_copy.name}."
        return detail
