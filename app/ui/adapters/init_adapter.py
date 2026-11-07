"""Initialisation de l'application : création du premier administrateur et de l'exercice courant."""
from __future__ import annotations

import sqlite3
from datetime import date

from app.database.connection import get_connection, transaction
from app.repositories import utilisateurs, exercices, parametres
from app.security.session import Role
from app.security.passwords import hash_password
from app.security.audit import Action
from app.security import audit
from app.services.auth_service import has_admin, create_first_admin, AuthError
from app.services.exercice_service import create_exercice, set_funeral_tarifs


def ensure_first_admin() -> bool:
    """Vérifie si un administrateur existe.

    Returns:
        True si un admin existe, False sinon.
    """
    conn = get_connection()
    try:
        has = has_admin(conn)
        conn.close()
        return has
    except Exception:
        conn.close()
        return False


def ensure_current_exercise() -> bool:
    """Crée l'exercice courant s'il n'existe pas.

    Returns:
        True si un exercice a été créé, False si un exercice existait déjà.
    """
    from app.security.session import Session, CurrentUser

    conn = get_connection()
    try:
        # Vérifier si un exercice existe déjà
        existing = conn.execute(
            "SELECT id FROM exercices ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if existing:
            conn.close()
            return False

        # Créer l'exercice 2025-2026 (septembre à août)
        today = date.today()
        year = today.year
        if today.month < 9:
            year -= 1

        # Créer une session temporaire pour l'initialisation
        session = Session()
        session.login(CurrentUser(1, "admin", "Administrateur", Role.ADMINISTRATEUR))

        with transaction(conn):
            exercice = create_exercice(
                conn,
                session,
                year,
                5000,  # tarif_homme
                3000   # tarif_femme
            )

            # Définir les tarifs funéraires par défaut
            set_funeral_tarifs(conn, session, exercice.id, 10000, 8000)

        conn.close()
        return True
    except Exception as e:
        print(f"Erreur création exercice: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return False


def initialize_application() -> None:
    """Initialise l'application complète (admin + exercice)."""
    ensure_first_admin()
    ensure_current_exercise()
