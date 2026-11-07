"""Adaptateur des amendes : connecte FinesPort aux services."""
from __future__ import annotations

import sqlite3
from datetime import date

from app.database.connection import get_connection
from app.repositories import exercices, amendes, membres
from app.security.session import Session
from app.services.amende_service import collecter, creer_amende
from app.ui.ports_fines import FinesData, FineRecord


class FinesAdapter:
    """Implémente FinesPort en utilisant les services."""

    def __init__(self) -> None:
        self._session = Session()

    def set_session(self, session: Session) -> None:
        self._session = session

    def add_fine(self, membre_id: int, nom: str, libelle: str,
                 montant_attendu: int, date_amende: str) -> int:
        conn = get_connection()
        try:
            fine = creer_amende(
                conn, self._session, membre_id, nom, libelle, montant_attendu,
                date.fromisoformat(date_amende),
            )
            return fine.id
        finally:
            conn.close()

    def collect_fine(self, amende_id: int, montant: int, date_encaissement: str) -> None:
        conn = get_connection()
        try:
            collecter(conn, self._session, amende_id, montant,
                      date.fromisoformat(date_encaissement))
        finally:
            conn.close()

    def load(self, exercise_label: str) -> FinesData:
        conn = get_connection()
        try:
            from app.repositories import exercices
            exercice = exercices.get_by_libelle(conn, exercise_label)

            if not exercice:
                conn.close()
                return self._empty_data(exercise_label)

            exercice_id = exercice.id
            is_open = exercice.statut == "ouvert"

            # Récupérer les amendes
            fines = amendes.list_(conn, exercice_id)

            records = [FineRecord(
                id=line.amende.id,
                member_carnet=line.numero_carnet,
                member_name=line.membre_nom,
                label=line.amende.libelle,
                date=line.amende.date_amende.strftime("%d/%m/%Y"),
                amount_expected=line.amende.montant_attendu,
                amount_collected=line.amende.montant_collecte,
                remaining=line.amende.manque_a_gagner,
            ) for line in fines]

            conn.close()
            return FinesData(
                exercise_label=exercise_label,
                is_open=is_open,
                records=tuple(records),
                total_expected=sum(record.amount_expected for record in records),
                total_collected=sum(record.amount_collected for record in records),
            )
        except Exception as e:
            conn.close()
            print(f"Erreur fines adapter: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_data(exercise_label)

    def _empty_data(self, exercise_label: str) -> FinesData:
        return FinesData(
            exercise_label=exercise_label,
            is_open=True,
            records=()
        )
