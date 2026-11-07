"""Normalise les numéros de carnet vers le format de référence 4 chiffres.

Usage:
    python scripts/normaliser_carnets.py --db data/app.db --dry-run
    python scripts/normaliser_carnets.py --db data/app.db --apply

- Sauvegarde automatique avant écriture
- Mode simulation par défaut
- Rapport détaillé des conflits et des valeurs réécrites
"""
from __future__ import annotations

import argparse
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sqlite3
import sys

from app.services.carnet_service import CarnetError, valider_carnet


def backup_db(db_path: Path) -> Path:
    backup = db_path.with_name(f"{db_path.stem}-{datetime.now():%Y%m%d-%H%M%S}.bak.db")
    shutil.copy2(db_path, backup)
    return backup


def scan_carnets(conn: sqlite3.Connection) -> tuple[list[tuple[int, str, str]], list[tuple[str, list[int]]]]:
    rows = conn.execute("SELECT id, numero_carnet FROM membres ORDER BY id").fetchall()
    corrections: list[tuple[int, str, str]] = []
    conflicts: dict[str, list[int]] = defaultdict(list)

    for membre_id, numero in rows:
        try:
            normalise = valider_carnet(numero)
        except CarnetError:
            corrections.append((membre_id, numero, "INVALID"))
            continue

        if normalise != numero:
            corrections.append((membre_id, numero, normalise))
        conflicts[normalise].append(membre_id)

    invalid_conflicts = [(value, ids) for value, ids in conflicts.items() if len(ids) > 1]
    return corrections, invalid_conflicts


def main() -> int:
    parser = argparse.ArgumentParser(description="Normaliser les numéros de carnet vers 4 chiffres.")
    parser.add_argument("--db", type=Path, default=Path("data/app.db"), help="Base SQLite à vérifier.")
    parser.add_argument("--apply", action="store_true", help="Applique la correction; sans ce drapeau, le script est en mode simulation.")
    args = parser.parse_args()

    db_path = args.db
    if not db_path.exists():
        print(f"Base introuvable : {db_path}", file=sys.stderr)
        return 2

    with sqlite3.connect(db_path) as conn:
        corrections, conflicts = scan_carnets(conn)

        print(f"Base : {db_path}")
        print(f"Nombre de lignes examinées : {len(corrections) + sum(len(v) for _, v in [])}")
        print(f"Corrections détectées : {len([c for c in corrections if c[2] != 'INVALID'])}")
        print(f"Valeurs invalides : {len([c for c in corrections if c[2] == 'INVALID'])}")
        print(f"Conflits détectés : {len(conflicts)}")

        if corrections:
            print("\nDétail :")
            for membre_id, old, new in corrections:
                if new == "INVALID":
                    print(f"- membre {membre_id}: invalide -> {old!r}")
                else:
                    print(f"- membre {membre_id}: {old!r} -> {new!r}")

        if conflicts:
            print("\nConflits (numéro après normalisation présent plusieurs fois) :")
            for value, ids in conflicts:
                print(f"- {value}: membres {ids}")

        if not args.apply:
            print("\nMode simulation : aucune écriture effectuée.")
            return 0

        backup_file = backup_db(db_path)
        print(f"\nSauvegarde créée : {backup_file}")

        updates = []
        for membre_id, old, new in corrections:
            if new == "INVALID":
                continue
            updates.append((new, membre_id))

        if updates:
            conn.executemany("UPDATE membres SET numero_carnet = ? WHERE id = ?", updates)
            conn.commit()
            print(f"{len(updates)} enregistrements normalisés.")
        else:
            print("Aucune correction à appliquer.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
