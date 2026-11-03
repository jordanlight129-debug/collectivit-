"""Adaptateur des cotisations mensuelles : connecte MonthlyPort aux services."""
from __future__ import annotations

import sqlite3
from datetime import date

from app.database.connection import get_connection
from app.repositories import exercices
from app.services.tableau_mensuel import tableau as tableau_mensuel
from app.ui.ports_monthly import MonthlyData, MonthlyMember, MonthlyCell


class MonthlyAdapter:
    """Implémente MonthlyPort en utilisant les services."""

    def __init__(self) -> None:
        pass

    def load(self, exercise_label: str) -> MonthlyData:
        conn = get_connection()
        try:
            exercice = conn.execute(
                "SELECT id, libelle, statut FROM exercices WHERE libelle = ?",
                (exercise_label,)
            ).fetchone()
            
            if not exercice:
                conn.close()
                return self._empty_data(exercise_label)
            
            exercice_id = exercice["id"]
            is_open = exercice["statut"] == "ouvert"
            
            # Récupérer les tarifs
            tarif_row = conn.execute(
                "SELECT sexe, montant FROM tarifs_mensuels WHERE exercice_id = ?",
                (exercice_id,)
            ).fetchall()
            
            tariff_man = 5000
            tariff_woman = 3000
            for row in tarif_row:
                if row["sexe"] == "M":
                    tariff_man = row["montant"]
                else:
                    tariff_woman = row["montant"]
            
            # Récupérer le tableau mensuel
            page = tableau_mensuel(conn, exercice_id)
            
            # Convertir en MonthlyMember
            members = []
            for ligne in page.lignes:
                cells = self._build_cells(ligne)
                members.append(MonthlyMember(
                    carnet=f"Carnet {ligne.numero_carnet}",
                    name=ligne.nom,
                    sexe=ligne.sexe,
                    joined="01/09/2025",  # À récupérer depuis membre
                    cells=cells,
                    total_due=ligne.du,
                    total_paid=ligne.perçu,
                    total_debt=ligne.dette,
                    advance=ligne.avance,
                    carried_debt=ligne.report_dette,
                    carried_advance=ligne.report_avance,
                ))
            
            conn.close()
            return MonthlyData(
                exercise_label=exercise_label,
                is_open=is_open,
                tariff_man=tariff_man,
                tariff_woman=tariff_woman,
                members=tuple(members)
            )
        except Exception as e:
            conn.close()
            print(f"Erreur monthly adapter: {e}")
            return self._empty_data(exercise_label)

    def _empty_data(self, exercise_label: str) -> MonthlyData:
        return MonthlyData(
            exercise_label=exercise_label,
            is_open=True,
            tariff_man=5000,
            tariff_woman=3000,
            members=()
        )

    def _build_cells(self, ligne) -> tuple[MonthlyCell, ...]:
        """Construit les cellules mensuelles à partir de la ligne du tableau."""
        from app.ui.ports_monthly import MonthlyCell
        from app.services.regles import month_label
        
        cells = []
        for cell in ligne.releve.cells:
            cells.append(MonthlyCell(
                month=month_label(cell.month),
                status=cell.status,
                due=cell.due,
                paid=cell.paid,
                debt=cell.debt
            ))
        return tuple(cells)
