"""Accès aux données des reliquats (SQL uniquement)."""
from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from app.models.depense import Reliquat, ReliquatLigne


def create(conn: sqlite3.Connection, exercice_id: int, depense_id: int, nom: str,
           montant: Decimal, date_reliquat: date) -> int:
    cur = conn.execute(
        "INSERT INTO reliquats (exercice_id, depense_id, nom, montant, date_reliquat) "
        "VALUES (?, ?, ?, ?, ?)",
        (exercice_id, depense_id, nom, int(montant), date_reliquat.isoformat()),
    )
    return int(cur.lastrowid)


def get_by_depense(conn: sqlite3.Connection, depense_id: int) -> Reliquat | None:
    row = conn.execute("SELECT * FROM reliquats WHERE depense_id = ?", (depense_id,)).fetchone()
    return Reliquat.from_row(row) if row else None


def list_for_exercice(conn: sqlite3.Connection, exercice_id: int) -> list[ReliquatLigne]:
    """Les plus récents d'abord, avec le libellé de la dépense d'origine."""
    rows = conn.execute(
        "SELECT r.*, d.libelle AS depense_libelle FROM reliquats r "
        "JOIN depenses d ON d.id = r.depense_id WHERE r.exercice_id = ? "
        "ORDER BY r.date_reliquat DESC, r.id DESC",
        (exercice_id,),
    ).fetchall()
    return [ReliquatLigne(Reliquat.from_row(r), r["depense_libelle"]) for r in rows]


def total(conn: sqlite3.Connection, exercice_id: int) -> Decimal:
    row = conn.execute(
        "SELECT COALESCE(SUM(montant), 0) FROM reliquats WHERE exercice_id = ?", (exercice_id,)
    ).fetchone()
    return Decimal(str(row[0]))