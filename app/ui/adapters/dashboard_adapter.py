"""Adaptateur du tableau de bord : connecte DashboardPort aux services."""
from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from app.database.connection import get_connection
from app.repositories import exercices, historique, membres
from app.services.bilan_service import calculer
from app.services.tableau_parallele import list_resumes
from app.services.tableau_funeraire import tableau as tableau_funeraire
from app.services.amende_service import resume as amende_resume
from app.services.depense_service import resume as depense_resume
from app.services.tableau_mensuel import tableau as tableau_mensuel
from app.services.calendrier import exercise_months, start_year_for_date, month_label
from app.ui.ports import (
    DashboardData, RubriqueFigures, AlertInfo,
    MonthFigures, OperationInfo, DebtorInfo,
)
import logging

logger = logging.getLogger(__name__)


def _log_erreur(contexte: str) -> None:
    """Journalise la vraie erreur (à appeler depuis un bloc except)."""
    logger.error("Erreur dans %s", contexte, exc_info=True)


class DashboardAdapter:
    """Implémente DashboardPort en utilisant les services."""

    def __init__(self) -> None:
        pass

    def load(self, exercise_label: str) -> DashboardData:
        conn = get_connection()
        try:
            exercice = exercices.get_by_libelle(conn, exercise_label)
            logger.debug("dashboard load: %r -> %r", exercise_label, exercice)
            if not exercice:
                return self._empty_data(exercise_label)

            is_open = exercice.statut == "ouvert"
            period_start = exercice.date_debut
            period_end = exercice.date_fin

            # Statistiques membres
            active_count = membres.count(conn, statut="actif")
            deceased_count = membres.count(conn, statut="decede")

            # Chiffres par rubrique
            rubriques = self._calculate_rubriques(conn, exercice.id)

            # Dépenses totales
            depense_totals = depense_resume(conn, exercice.id)
            expenses = depense_totals.depense

            # Bilan (calculer ne demande pas de session)
            bilan = calculer(conn, exercice.id)

            # Détails des dettes
            debtors = self._get_debtors(conn, exercice.id)

            # Alertes
            alerts = self._get_alerts(exercice, bilan)

            # Données mensuelles pour le graphique
            monthly = self._get_monthly_figures(conn, exercice.id, period_start, period_end)

            # Dernières opérations
            operations = self._get_recent_operations(conn, exercice.id)

            return DashboardData(
                exercise_label=exercise_label,
                is_open=is_open,
                period_start=period_start,
                period_end=period_end,
                active_members=active_count,
                deceased_members=deceased_count,
                rubriques=rubriques,
                expenses=expenses,
                debts_total=bilan.total_dettes,
                debtor_members=len(debtors),
                payments=(),  # À implémenter avec versements récents
                alerts=alerts,
                monthly=monthly,
                operations=operations,
                debtors=debtors,
            )
        except Exception:
            _log_erreur("load()")
            return self._empty_data(exercise_label)
        finally:
            conn.close()

    def _empty_data(self, exercise_label: str) -> DashboardData:
        return DashboardData(
            exercise_label=exercise_label,
            is_open=True,
            period_start=date.today(),
            period_end=date.today(),
            active_members=0,
            deceased_members=0,
            rubriques=(),
            expenses=0,
            debts_total=0,
            debtor_members=0,
            payments=(),
            alerts=(),
            monthly=(),
            operations=(),
            debtors=(),
        )

    def _calculate_rubriques(self, conn: sqlite3.Connection, exercice_id: int) -> tuple[RubriqueFigures, ...]:
        """Calcule les chiffres par rubrique."""
        mensuelle_du, mensuelle_percu = self._get_mensuelle_totals(conn, exercice_id)
        funeraire_du, funeraire_percu = self._get_funeraire_totals(conn, exercice_id)
        parallele_du, parallele_percu = self._get_parallele_totals(conn, exercice_id)
        reliquats_percu = self._get_reliquats_total(conn, exercice_id)

        amende_totals = amende_resume(conn, exercice_id)
        amende_du = amende_totals.attendu
        amende_percu = amende_totals.collecte

        return (
            RubriqueFigures("mensuelle", "Cotisations mensuelles", mensuelle_du, mensuelle_percu),
            RubriqueFigures("funeraire", "Cotisations funéraires", funeraire_du, funeraire_percu),
            RubriqueFigures("parallele", "Cotisations parallèles", parallele_du, parallele_percu),
            RubriqueFigures("reliquats", "Reliquats", None, reliquats_percu),
            RubriqueFigures("amendes", "Amendes", amende_du, amende_percu),
        )

    def _get_mensuelle_totals(self, conn: sqlite3.Connection, exercice_id: int) -> tuple[int, int]:
        """Calcule le dû et le perçu pour les cotisations mensuelles."""
        try:
            page = tableau_mensuel(conn, exercice_id)
            return page.general.du, page.general.percu
        except Exception:
            _log_erreur("_get_mensuelle_totals")
            return 0, 0

    def _get_funeraire_totals(self, conn: sqlite3.Connection, exercice_id: int) -> tuple[int, int]:
        """Calcule le dû et le perçu pour les cotisations funéraires (tous les membres)."""
        try:
            page = tableau_funeraire(conn, exercice_id)
            return page.general.du, page.general.percu
        except Exception:
            _log_erreur("_get_funeraire_totals")
            return 0, 0

    def _get_parallele_totals(self, conn: sqlite3.Connection, exercice_id: int) -> tuple[int, int]:
        """Calcule le dû et le perçu pour les cotisations parallèles."""
        try:
            resumes = list_resumes(conn, exercice_id)
            du = sum(totals.du for _, totals in resumes)
            percu = sum(totals.percu for _, totals in resumes)
            return du, percu
        except Exception:
            _log_erreur("_get_parallele_totals")
            return 0, 0

    def _get_reliquats_total(self, conn: sqlite3.Connection, exercice_id: int) -> Decimal:
        """Calcule le total des reliquats."""
        try:
            from app.repositories import reliquats
            return reliquats.total(conn, exercice_id)
        except Exception:
            _log_erreur("_get_reliquats_total")
            return Decimal(0)

    def _get_debtors(self, conn: sqlite3.Connection, exercice_id: int) -> tuple[DebtorInfo, ...]:
        """Récupère la liste des membres avec des dettes."""
        try:
            page = tableau_mensuel(conn, exercice_id)
            debtors = []
            for ligne in page.lignes:
                if ligne.releve.total_debt > 0:
                    membre = ligne.membre
                    debtors.append(DebtorInfo(
                        membre.nom,
                        f"Carnet {membre.numero_carnet}",
                        ligne.releve.total_debt,
                    ))
            return tuple(debtors)
        except Exception:
            _log_erreur("_get_debtors")
            return ()

    def _get_alerts(self, exercice, bilan) -> tuple[AlertInfo, ...]:
        """Génère les alertes basées sur l'état de l'exercice."""
        alerts = []

        if exercice.statut == "ouvert":
            days_left = (exercice.date_fin - date.today()).days
            if days_left <= 30:
                if days_left < 0:
                    message = (
                        f"L’exercice {exercice.libelle} a dépassé sa date de fin depuis "
                        f"{abs(days_left)} jour{'s' if days_left < -1 else ''} et reste ouvert. "
                        "Veuillez procéder à sa clôture."
                    )
                elif days_left == 0:
                    message = (
                        f"L’exercice {exercice.libelle} prend fin aujourd’hui. "
                        "Veuillez procéder à sa clôture."
                    )
                else:
                    delai = "demain" if days_left == 1 else f"dans {days_left} jours"
                    message = (
                        f"L’exercice {exercice.libelle} prend fin {delai}. "
                        "Préparez sa clôture."
                    )
                alerts.append(AlertInfo(
                    "warning",
                    message,
                ))

        if bilan.total_dettes > 0:
            alerts.append(AlertInfo(
              "danger",
              "Des dettes restent à recouvrer.",
        ))

        return tuple(alerts)

    def _get_monthly_figures(self, conn: sqlite3.Connection, exercice_id: int,
                             start: date, end: date) -> tuple[MonthFigures, ...]:
        """Calcule les entrées et dépenses par mois."""
        months = exercise_months(start_year_for_date(start))
        totals = {(year, month): [0, 0] for year, month in months}
        for operation in historique.list_(conn, exercice_id=exercice_id):
            monthly_totals = totals.get((operation.date_operation.year, operation.date_operation.month))
            if monthly_totals is None:
                continue
            monthly_totals[0 if operation.sens == "entree" else 1] += operation.montant

        return tuple(
            MonthFigures(month_label(month), *totals[(year, month)])
            for year, month in months
        )

    def _get_recent_operations(self, conn: sqlite3.Connection, exercice_id: int) -> tuple[OperationInfo, ...]:
        """Récupère les dernières opérations."""
        labels = {
            "mensuelle": "Mensuelle",
            "funeraire": "Funéraire",
            "parallele": "Parallèle",
            "amende": "Amende",
            "reliquat": "Reliquat",
            "depense": "Dépense",
        }
        operations = historique.list_(conn, exercice_id=exercice_id, limit=5)
        return tuple(
            OperationInfo(
                on=operation.date_operation,
                label=(f"{operation.membre_nom} — {operation.libelle}"
                       if operation.membre_nom else operation.libelle),
                rubrique=labels.get(operation.rubrique, operation.rubrique),
                amount=operation.montant if operation.sens == "entree" else -operation.montant,
                status=("reliquat" if operation.source == "reliquat"
                        else "enregistree" if operation.source == "depense" else "paye"),
            )
            for operation in operations
        )
