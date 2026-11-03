"""Adaptateur des paramètres : connecte aux services de paramètres."""
from __future__ import annotations

import sqlite3

from app.database.connection import get_connection
from app.repositories import parametres
from app.ui.ports_settings import SettingsData, Parameter


class SettingsAdapter:
    """Implémente l'interface pour les paramètres."""

    def __init__(self) -> None:
        pass

    def load(self, exercise_label: str) -> SettingsData:
        """Charge les paramètres."""
        conn = get_connection()
        try:
            # Lister les paramètres
            params = conn.execute("SELECT cle, valeur FROM parametres").fetchall()
            conn.close()

            # Paramètres par défaut avec descriptions
            default_params = {
                "association_name": "Nom de l'association",
                "brand_initials": "Initiales de la marque",
                "default_tarif_homme": "Tarif mensuel par défaut (hommes)",
                "default_tarif_femme": "Tarif mensuel par défaut (femmes)",
            }

            parameters = []
            for row in params:
                key = row["cle"]
                value = row["valeur"]
                description = default_params.get(key, "")
                parameters.append(Parameter(key=key, value=value, description=description))

            return SettingsData(
                exercise_label=exercise_label,
                parameters=tuple(parameters)
            )
        except Exception as e:
            conn.close()
            print(f"Erreur settings adapter: {e}")
            import traceback
            traceback.print_exc()
            return SettingsData(
                exercise_label=exercise_label,
                parameters=()
            )

    def get_parameter(self, key: str, default: str = "") -> str:
        """Récupère un paramètre."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT valeur FROM parametres WHERE cle = ?", (key,)).fetchone()
            conn.close()
            return row[0] if row else default
        except Exception:
            conn.close()
            return default

    def set_parameter(self, key: str, value: str) -> None:
        """Définit un paramètre."""
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO parametres (cle, valeur) VALUES (?, ?) "
                "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
                (key, value)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            conn.close()
            raise Exception(f"Erreur lors de la sauvegarde du paramètre: {e}")
