"""Adaptateur des sauvegardes : connecte aux services de backup."""
from __future__ import annotations

import sqlite3
from datetime import datetime
import os

from app.database.connection import get_connection
from app.services.backup_service import sauvegarder_manuelle, lister
from app.ui.ports_backups import BackupsData, BackupInfo


class BackupsAdapter:
    """Implémente l'interface pour les sauvegardes."""

    def __init__(self) -> None:
        pass

    def load(self, exercise_label: str) -> BackupsData:
        """Charge la liste des sauvegardes disponibles."""
        conn = get_connection()
        try:
            # Lister les sauvegardes
            backups_list = lister(conn)
            conn.close()

            # Convertir en BackupInfo
            backup_infos = []
            for backup in backups_list:
                # Obtenir la taille du fichier
                size_str = "—"
                if os.path.exists(backup):
                    size_bytes = os.path.getsize(backup)
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} o"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f} Ko"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024):.1f} Mo"

                # Extraire la date du nom de fichier
                filename = os.path.basename(backup)
                date_str = filename.replace("solidarite_etoile_", "").replace(".db", "").replace("_", " ")

                backup_infos.append(BackupInfo(
                    filename=filename,
                    date=date_str,
                    size=size_str
                ))

            return BackupsData(
                exercise_label=exercise_label,
                backups=tuple(backup_infos)
            )
        except Exception as e:
            conn.close()
            print(f"Erreur backups adapter: {e}")
            import traceback
            traceback.print_exc()
            return BackupsData(
                exercise_label=exercise_label,
                backups=()
            )

    def create_backup(self) -> str:
        """Crée une sauvegarde manuelle."""
        conn = get_connection()
        try:
            sauvegarder_manuelle(conn)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.close()
            return f"Sauvegarde créée le {timestamp}"
        except Exception as e:
            conn.close()
            raise Exception(f"Erreur lors de la sauvegarde: {e}")
