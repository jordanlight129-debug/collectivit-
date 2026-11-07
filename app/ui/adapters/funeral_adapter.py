"""Adaptateur des cotisations funéraires : connecte FuneralPort aux services."""
from __future__ import annotations

import sqlite3
from datetime import date

from app.database.connection import get_connection
from app.repositories import exercices, membres
from app.security.session import Session
from app.services.deces_service import creer_collecte, list_collectes
from app.services.reglement_service import enregistrer_paiement
from app.services.tableau_funeraire import tableau as tableau_funeraire
from app.ui.ports_funeral import FuneralCellInfo, FuneralData, FuneralMemberInfo, DeathRecord


class FuneralAdapter:
    """Implémente FuneralPort en utilisant les services."""

    def __init__(self) -> None:
        self._session = Session()

    def set_session(self, session: Session) -> None:
        self._session = session

    def create_collection(self, nom_defunt: str, type_deces: str, date_deces: str,
                          membre_defunt_id: int | None = None,
                          membre_endeuille_id: int | None = None,
                          exempter_endeuille: bool = False) -> int:
        conn = get_connection()
        try:
            collection = creer_collecte(
                conn, self._session, nom_defunt, type_deces, date.fromisoformat(date_deces),
                membre_defunt_id=membre_defunt_id,
                membre_endeuille_id=membre_endeuille_id,
                exempter_endeuille=exempter_endeuille,
            )
            return collection.id
        finally:
            conn.close()

    def record_payment(self, exercise_label: str, membre_id: int, montant: int,
                       date_versement: str, mode: str = "global", note: str = "",
                       confirmer_excedent: bool = False) -> int:
        conn = get_connection()
        try:
            exercice = exercices.get_by_libelle(conn, exercise_label)
            if exercice is None:
                raise ValueError(f"Exercice introuvable : {exercise_label}")
            receipt = enregistrer_paiement(
                conn, self._session, membre_id, exercice.id, "funeraire", montant,
                mode=mode, date_versement=date.fromisoformat(date_versement), note=note,
                confirmer_excedent=confirmer_excedent,
            )
            return receipt.numero
        finally:
            conn.close()

    def load(self, exercise_label: str) -> FuneralData:
        conn = get_connection()
        try:
            from app.repositories import exercices
            exercice = exercices.get_by_libelle(conn, exercise_label)

            if not exercice:
                conn.close()
                return self._empty_data(exercise_label)

            exercice_id = exercice.id
            is_open = exercice.statut == "ouvert"

            # Récupérer les collectes de décès
            collectes = list_collectes(conn, exercice_id)
            tableau = tableau_funeraire(conn, exercice_id)

            # Convertir en DeathRecord
            records = []
            for index, c in enumerate(collectes):
                defunt = membres.get(conn, c.membre_defunt_id) if c.membre_defunt_id else None
                records.append(DeathRecord(
                    id=c.id,
                    deceased_name=c.nom_defunt,
                    death_type=c.type_deces,
                    death_date=c.date_deces.strftime("%d/%m/%Y"),
                    member_carnet=defunt.numero_carnet if defunt else None,
                    amount_man=c.montant_homme,
                    amount_woman=c.montant_femme,
                    total_collected=sum(line.releve.cells[index].paid for line in tableau.lignes),
                    total_expected=sum(line.releve.cells[index].due for line in tableau.lignes),
                    exempted=bool(c.exempter_endeuille),
                ))

            members = tuple(FuneralMemberInfo(
                id=line.membre.id,
                carnet=line.membre.numero_carnet,
                name=line.membre.nom,
                cells=tuple(FuneralCellInfo(
                    status=cell.status,
                    due=cell.due,
                    paid=cell.paid,
                    reason=cell.reason,
                ) for cell in line.releve.cells),
                due=line.releve.total_due,
                paid=line.releve.cash_total,
                debt=line.releve.total_debt,
            ) for line in tableau.lignes)

            conn.close()
            return FuneralData(
                exercise_label=exercise_label,
                is_open=is_open,
                records=tuple(records),
                members=members,
                total_members=tableau.total,
                total_due=tableau.general.du,
                total_paid=tableau.general.percu,
                total_debt=tableau.general.dette,
            )
        except Exception as e:
            conn.close()
            print(f"Erreur funeral adapter: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_data(exercise_label)

    def _empty_data(self, exercise_label: str) -> FuneralData:
        return FuneralData(
            exercise_label=exercise_label,
            is_open=True,
            records=()
        )
