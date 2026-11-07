"""Configuration globale de l'application (chemins, constantes techniques).

Ne contient AUCUNE règle comptable : celles-ci vivent dans app/services
et sont paramétrables en base (montants selon le sexe, types de décès…).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_NAME = " Collectivitée LANTCHIBLE"
ASSOCIATION_NAME = "Collectivitée LANTCHIBLE"
BRAND_INITIALS = "CL"
APP_VERSION = "1.0.0"
CURRENCY = "FCFA"

# L'exercice comptable va de septembre à août (cahier des charges).
FISCAL_YEAR_START_MONTH = 9


def _is_frozen() -> bool:
    """True lorsque l'application est empaquetée (PyInstaller, .exe)."""
    return getattr(sys, "frozen", False)


def _base_dir() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _data_root() -> Path:
    """Dossier des données : projet en dev, %LOCALAPPDATA% une fois empaqueté."""
    if _is_frozen():
        local_appdata = os.environ.get("LOCALAPPDATA")
        root = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        return root / "SolidariteEtoile"
    return _base_dir()


BASE_DIR = _base_dir()
DATA_DIR = _data_root() / "data"
BACKUP_DIR = _data_root() / "backups"
EXPORT_DIR = _data_root() / "exports"
DB_PATH = DATA_DIR / "association.db"


def ensure_directories() -> None:
    """Crée les dossiers nécessaires au premier lancement."""
    for folder in (DATA_DIR, BACKUP_DIR, EXPORT_DIR):
        folder.mkdir(parents=True, exist_ok=True)

    if _is_frozen():
        legacy_db = BASE_DIR / "data" / "association.db"
        if legacy_db.is_file() and not DB_PATH.exists():
            with legacy_db.open("rb") as source:
                try:
                    with DB_PATH.open("xb") as destination:
                        shutil.copyfileobj(source, destination)
                except FileExistsError:
                    pass