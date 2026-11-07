"""Accès aux données des dépenses (SQL uniquement)."""
from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from app.models.depense import Depense, DepenseLigne, Reliquat

_FROM = "FROM depenses d LEFT JOIN reliquats r ON r.depense_id = d.id"


def create(conn: sqlite3.Connection, exercice_id: int, date_depense: date, libelle: str,
           beneficiaire: str | None, montant_prevu: Decimal, montant_depense: Decimal,
           cree_par: int | None) -> int:
    cur = conn.execute(
        "INSERT INTO depenses (exercice_id, date_depense, libelle, beneficiaire, "
        "montant_prevu, montant_depense, cree_par) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (exercice_id, date_depense.isoformat(), libelle, beneficiaire, int(montant_prevu),
         int(montant_depense), cree_par),
    )
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, depense_id: int) -> Depense | None:
    row = conn.execute("SELECT * FROM depenses WHERE id = ?", (depense_id,)).fetchone()
    return Depense.from_row(row) if row else None


def delete(conn: sqlite3.Connection, depense_id: int) -> None:
    """Le reliquat lié est supprimé avec elle (ON DELETE CASCADE)."""
    conn.execute("DELETE FROM depenses WHERE id = ?", (depense_id,))


def _where(exercice_id: int, search: str | None, date_debut: date | None,
           date_fin: date | None, avec_reliquat: bool | None):
    clauses, params = ["d.exercice_id = ?"], [exercice_id]
    if search:
        clauses.append("(d.libelle LIKE ? OR d.beneficiaire LIKE ?)")
        params += [f"%{search}%"] * 2
    if date_debut:
        clauses.append("d.date_depense >= ?")
        params.append(date_debut.isoformat())
    if date_fin:
        clauses.append("d.date_depense <= ?")
        params.append(date_fin.isoformat())
    if avec_reliquat is True:
        clauses.append("r.id IS NOT NULL")
    elif avec_reliquat is False:
        clauses.append("r.id IS NULL")
    return " WHERE " + " AND ".join(clauses), params


def list_(conn: sqlite3.Connection, exercice_id: int, *, search: str | None = None,
          date_debut: date | None = None, date_fin: date | None = None,
          avec_reliquat: bool | None = None, limit: int | None = None,
          offset: int = 0) -> list[DepenseLigne]:
    """Les plus récentes d'abord, avec leur reliquat éventuel."""
    where, params = _where(exercice_id, search, date_debut, date_fin, avec_reliquat)
    sql = ("SELECT d.*, r.id AS r_id, r.nom AS r_nom, r.montant AS r_montant, "
           f"r.date_reliquat AS r_date {_FROM}{where} ORDER BY d.date_depense DESC, d.id DESC")
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params += [limit, offset]
    lignes = []
    for row in conn.execute(sql, params).fetchall():
        reliquat = None
        if row["r_id"] is not None:
            reliquat = Reliquat(row["r_id"], row["exercice_id"], row["id"], row["r_nom"],
                                Decimal(str(row["r_montant"])), date.fromisoformat(row["r_date"]))
        lignes.append(DepenseLigne(Depense.from_row(row), reliquat))
    return lignes


def count(conn: sqlite3.Connection, exercice_id: int, *, search: str | None = None,
          date_debut: date | None = None, date_fin: date | None = None,
          avec_reliquat: bool | None = None) -> int:
    where, params = _where(exercice_id, search, date_debut, date_fin, avec_reliquat)
    return conn.execute(f"SELECT COUNT(*) {_FROM}{where}", params).fetchone()[0]


def totals(conn: sqlite3.Connection, exercice_id: int, *, search: str | None = None,
           date_debut: date | None = None, date_fin: date | None = None,
           avec_reliquat: bool | None = None) -> tuple[Decimal, Decimal, Decimal]:
    """(prévu, dépensé, reliquats)."""
    where, params = _where(exercice_id, search, date_debut, date_fin, avec_reliquat)
    row = conn.execute(
        "SELECT COALESCE(SUM(d.montant_prevu), 0), COALESCE(SUM(d.montant_depense), 0), "
        f"COALESCE(SUM(r.montant), 0) {_FROM}{where}",
        params,
    ).fetchone()
    return tuple(Decimal(str(value)) for value in row)