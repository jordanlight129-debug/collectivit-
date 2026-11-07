"""Adaptateur des cotisations parallèles : connecte ParallelPort aux services."""
from __future__ import annotations

import sqlite3
from datetime import date

from app.database.connection import get_connection
from app.repositories import exercices, cotisations_paralleles
from app.security.session import Session
from app.services.parallele_service import creer_cotisation
from app.services.reglement_service import enregistrer_paiement
from app.services.tableau_parallele import tableau as tableau_parallele
from app.ui.ports_parallel import ParallelData, ParallelMemberInfo, ParallelSubscription


class ParallelAdapter:
    """Implémente ParallelPort en utilisant les services."""

    def __init__(self) -> None:
        self._session = Session()

    def set_session(self, session: Session) -> None:
        self._session = session

    def add_subscription(self, nom: str, date_debut: str, date_fin: str,
                         montant_homme: int, montant_femme: int) -> int:
        conn = get_connection()
        try:
            subscription = creer_cotisation(
                conn, self._session, nom, date.fromisoformat(date_debut),
                date.fromisoformat(date_fin), montant_homme, montant_femme,
            )
            return subscription.id
        finally:
            conn.close()

    def record_payment(self, exercise_label: str, membre_id: int, cotisation_id: int,
                       montant: int, date_versement: str, mode: str = "global", note: str = "",
                       confirmer_excedent: bool = False) -> int:
        conn = get_connection()
        try:
            exercice = exercices.get_by_libelle(conn, exercise_label)
            if exercice is None:
                raise ValueError(f"Exercice introuvable : {exercise_label}")
            receipt = enregistrer_paiement(
                conn, self._session, membre_id, exercice.id, "parallele", montant,
                mode=mode, cotisation_id=cotisation_id,
                date_versement=date.fromisoformat(date_versement), note=note,
                confirmer_excedent=confirmer_excedent,
            )
            return receipt.numero
        finally:
            conn.close()

    def load(self, exercise_label: str) -> ParallelData:
        conn = get_connection()
        try:
            from app.repositories import exercices
            exercice = exercices.get_by_libelle(conn, exercise_label)

            if not exercice:
                conn.close()
                return self._empty_data(exercise_label)

            exercice_id = exercice.id
            is_open = exercice.statut == "ouvert"

            # Récupérer les cotisations parallèles avec leurs lignes de cotisation métier
            subs = cotisations_paralleles.list_for_exercice(conn, exercice_id)

            subscriptions = []
            for s in subs:
                tableau = tableau_parallele(conn, s.id)
                members = tuple(ParallelMemberInfo(
                    id=line.membre.id,
                    carnet=line.membre.numero_carnet,
                    name=line.membre.nom,
                    sex=line.membre.sexe.value,
                    expected=line.releve.due,
                    collected=line.releve.paid,
                    debt=line.releve.debt,
                    status=line.releve.status,
                ) for line in tableau.lignes)
                subscriptions.append(ParallelSubscription(
                    id=s.id,
                    name=s.nom,
                    start_date=s.date_debut.strftime("%d/%m/%Y"),
                    end_date=s.date_fin.strftime("%d/%m/%Y"),
                    amount_man=s.montant_homme,
                    amount_woman=s.montant_femme,
                    total_expected=tableau.general.du,
                    total_collected=tableau.general.percu,
                    members=members,
                ))

            conn.close()
            return ParallelData(
                exercise_label=exercise_label,
                is_open=is_open,
                subscriptions=tuple(subscriptions)
            )
        except Exception as e:
            conn.close()
            print(f"Erreur parallel adapter: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_data(exercise_label)

    def _empty_data(self, exercise_label: str) -> ParallelData:
        return ParallelData(
            exercise_label=exercise_label,
            is_open=True,
            subscriptions=()
        )
