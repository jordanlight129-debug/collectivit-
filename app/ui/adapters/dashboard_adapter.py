"""Adaptateur du tableau de bord : connecte DashboardPort aux services."""
from __future__ import annotations

import sqlite3
from datetime import date

from app.database.connection import get_connection
from app.repositories import exercices, membres, deces, cotisations_paralleles, amendes, depenses
from app.services.bilan_service import calculer
from app.services.versement_service import releve_mensuel
from app.services.deces_service import releve_funeraire
from app.services.tableau_parallele import list_resumes
from app.services.amende_service import resume as amende_resume
from app.services.depense_service import resume as depense_resume
from app.services.tableau_mensuel import tableau as tableau_mensuel
from app.services.calendrier import exercise_months
from app.ui.ports import (
    DashboardData, DashboardPort, RubriqueFigures, PaymentInfo, AlertInfo,
    MonthFigures, OperationInfo, DebtorInfo
)


class DashboardAdapter:
    """Implémente DashboardPort en utilisant les services."""

    def __init__(self) -> None:
        pass

    def load(self, exercise_label: str) -> DashboardData:
        conn = get_connection()
        try:
            exercice = exercices.get_by_libelle(conn, exercise_label)
            if not exercice:
                conn.close()
                return self._empty_data(exercise_label)
            
            is_open = exercice.statut == "ouvert"
            period_start = exercice.date_debut
            period_end = exercice.date_fin

            # Statistiques membres
            active_count = membres.count(conn, statut="actif")
            deceased_count = membres.count(conn, statut="decede")

            # Calculer les rubriques
            rubriques = self._calculate_rubriques(conn, exercice.id)

            # Dépenses totales
            depense_totals = depense_resume(conn, exercice.id)
            expenses = depense_totals.depense

            # Bilan - utiliser calculer au lieu de consulter (pas besoin de session)
            from app.services.bilan_service import calculer
            bilan = calculer(conn, exercice.id)

            # Détails des dettes
            debtors = self._get_debtors(conn, exercice_id)

            # Alertes
            alerts = self._get_alerts(exercice, bilan)

            # Données mensuelles pour le graphique
            monthly = self._get_monthly_figures(conn, exercice.id, period_start, period_end)

            # Dernières opérations
            operations = self._get_recent_operations(conn, exercice.id)
            
            conn.close()
            
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
        except Exception as e:
            conn.close()
            print(f"Erreur dashboard adapter: {e}")
            return self._empty_data(exercise_label)

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
        # Cotisations mensuelles
        mensuelle_du, mensuelle_percu = self._get_mensuelle_totals(conn, exercice_id)
        
        # Cotisations funéraires
        funeraire_du, funeraire_percu = self._get_funeraire_totals(conn, exercice_id)
        
        # Cotisations parallèles
        parallele_du, parallele_percu = self._get_parallele_totals(conn, exercice_id)
        
        # Reliquats
        reliquats_percu = self._get_reliquats_total(conn, exercice_id)
        
        # Amendes
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
            du = page.general.du
            percu = page.general.percu
            return du, percu
        except Exception:
            return 0, 0

    def _get_funeraire_totals(self, conn: sqlite3.Connection, exercice_id: int) -> tuple[int, int]:
        """Calcule le dû et le perçu pour les cotisations funéraires."""
        try:
            releve = releve_funeraire(conn, exercice_id)
            du = sum(c.du for c in releve.collectes)
            percu = sum(c.perçu for c in releve.collectes)
            return du, percu
        except Exception:
            return 0, 0

    def _get_parallele_totals(self, conn: sqlite3.Connection, exercice_id: int) -> tuple[int, int]:
        """Calcule le dû et le perçu pour les cotisations parallèles."""
        try:
            resumes = list_resumes(conn, exercice_id)
            du = sum(totals.du for _, totals in resumes)
            percu = sum(totals.percu for _, totals in resumes)
            return du, percu
        except Exception:
            return 0, 0

    def _get_reliquats_total(self, conn: sqlite3.Connection, exercice_id: int) -> int:
        """Calcule le total des reliquats."""
        try:
            from app.repositories import reliquats
            return reliquats.total(conn, exercice_id)
        except Exception:
            return 0

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
                        ligne.releve.total_debt
                    ))
            return tuple(debtors)
        except Exception:
            return ()

    def _get_alerts(self, exercice, bilan) -> tuple[AlertInfo, ...]:
        """Génère les alertes basées sur l'état de l'exercice."""
        alerts = []

        if exercice.statut == "ouvert":
            # Vérifier si l'exercice est proche de la fin
            from datetime import datetime
            days_left = (exercice.date_fin - date.today()).days
            if days_left <= 30:
                alerts.append(AlertInfo(
                    "warning",
                    f"L'exercice {exercice.libelle} se termine dans {days_left} jours."
                ))

        if bilan.total_dettes > 0:
            alerts.append(AlertInfo(
                "danger",
                f"{bilan.nb_debiteurs} membres ont des dettes de cotisation à recouvrer."
            ))
        
        return tuple(alerts)

    def _get_monthly_figures(self, conn: sqlite3.Connection, exercice_id: int,
                           start: date, end: date) -> tuple[MonthFigures, ...]:
        """Calcule les entrées et dépenses par mois."""
        # exercise_months prend un start_year, pas des dates
        # On utilise l'année de début de l'exercice
        from app.services.calendrier import start_year_for_date
        start_year = start_year_for_date(start)
        months = exercise_months(start_year)
        figures = []

        for year, month in months:
            # Entrées du mois
            entrees = 0  # À implémenter avec versements du mois
            # Dépenses du mois
            depenses = 0  # À implémenter avec dépenses du mois

            from app.services.calendrier import month_label
            figures.append(MonthFigures(
                month_label(month),
                entrees,
                depenses
            ))

        return tuple(figures)

    def _get_recent_operations(self, conn: sqlite3.Connection, exercice_id: int) -> tuple[OperationInfo, ...]:
        """Récupère les dernières opérations."""
        # À implémenter avec la table des versements/dépenses
        return ()
