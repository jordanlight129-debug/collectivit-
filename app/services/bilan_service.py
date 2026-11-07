"""Bilan financier (cahier des charges §3.9).

Entrées = cotisation mensuelle + funéraire + parallèle + reliquats + amendes.
Bilan (résultat de l'année) = entrées − dépenses.
Solde cumulé = solde d'ouverture (reporté) + résultat de l'année.

« Perçu » = argent réellement encaissé dans l'exercice, arriérés remboursés compris.
Les dettes et avances reportées de l'exercice précédent sont des lignes à part : le
manque à gagner d'une rubrique = dû + dette reportée − perçu − avance reportée.
Pour chaque rubrique et pour le global : excédent en vert, dette en rouge,
jamais de chiffre négatif affiché (voir affichage.py).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.models.exercice import Exercice
from app.models.versement import FUNERAIRE, MENSUELLE, PARALLELE
from app.repositories import exercices, versements
from app.repositories import reports as reports_repo
from app.security.session import Permission, Session
from app.services import (
    affichage, amende_service, depense_service, tableau_funeraire, tableau_mensuel,
    tableau_parallele,
)
from app.services.affichage import Situation
from app.services.tableau_funeraire import TableauFuneraireError
from app.services.tableau_mensuel import TableauError

RUBRIQUES = ("mensuelle", "funeraire", "parallele", "reliquats", "amendes")


class BilanError(Exception):
    """Données manquantes pour établir le bilan (message affichable)."""


@dataclass(frozen=True)
class LigneBilan:
    rubrique: str
    libelle: str
    du: Optional[int]          # None : pas de « dû » (reliquats)
    percu: int | Decimal    # argent encaissé dans l'exercice
    dettes: int = 0         # tout ce que les membres doivent encore (exercice + dettes reportées)
    avances: int = 0        # excédents des membres (y compris avances reportées inutilisées)
    dette_reportee: int = 0
    avance_reportee: int = 0

    @property
    def a_percevoir(self) -> Optional[int]:
        """Dû de l'année + dette reportée."""
        return None if self.du is None else self.du + self.dette_reportee

    @property
    def manque(self) -> Optional[int]:
        """Dû + dette reportée − perçu − avance reportée (négatif si excédent : pour les calculs)."""
        if self.du is None:
            return None
        return self.du + self.dette_reportee - self.percu - self.avance_reportee

    @property
    def situation(self) -> Optional[Situation]:
        """Excédent (vert) ou dette (rouge) de la rubrique. None pour les reliquats."""
        manque = self.manque
        return None if manque is None else affichage.depuis_ecart(-manque)


@dataclass(frozen=True)
class Bilan:
    exercice: Exercice
    lignes: tuple[LigneBilan, ...]      # les 5 rubriques d'entrées, dans l'ordre du cahier
    depenses: Decimal                   # total dépensé
    depenses_prevues: Decimal
    solde_ouverture: int = 0            # solde reporté de l'exercice précédent (signé, pour les calculs)

    def ligne(self, rubrique: str) -> LigneBilan:
        return next(l for l in self.lignes if l.rubrique == rubrique)

    @property
    def total_entrees(self) -> int | Decimal:
        return sum(l.percu for l in self.lignes)

    @property
    def total_du(self) -> int:
        return sum(l.du for l in self.lignes if l.du is not None)

    @property
    def total_dette_reportee(self) -> int:
        return sum(l.dette_reportee for l in self.lignes if l.du is not None)

    @property
    def total_avance_reportee(self) -> int:
        return sum(l.avance_reportee for l in self.lignes if l.du is not None)

    @property
    def percu_hors_reliquats(self) -> int:
        """Perçu des rubriques qui ont un dû (cotisations et amendes)."""
        return sum(l.percu for l in self.lignes if l.du is not None)

    @property
    def total_manque(self) -> int:
        return sum(l.manque for l in self.lignes if l.manque is not None)

    @property
    def total_dettes(self) -> int:
        return sum(l.dettes for l in self.lignes)

    @property
    def total_avances(self) -> int:
        return sum(l.avances for l in self.lignes)

    @property
    def solde(self) -> Decimal:
        """Résultat de l'année : entrées − dépenses (négatif possible, pour les calculs)."""
        return self.total_entrees - self.depenses

    @property
    def solde_cumule(self) -> Decimal:
        """Solde d'ouverture + résultat de l'année (c'est lui qui est reporté à la clôture)."""
        return self.solde_ouverture + self.solde

    @property
    def situation_globale(self) -> Situation:
        """Excédent ou dette de toutes les rubriques ayant un dû (reliquats exclus)."""
        return affichage.depuis_ecart(-self.total_manque)

    @property
    def situation_ouverture(self) -> Situation:
        """Solde d'ouverture : « Dette » en rouge ou « Excédent » en vert."""
        return affichage.depuis_ecart(self.solde_ouverture)

    @property
    def situation_solde(self) -> Situation:
        """Résultat de l'année (entrées − dépenses)."""
        return affichage.depuis_ecart(self.solde)

    @property
    def situation_cumulee(self) -> Situation:
        return affichage.depuis_ecart(self.solde_cumule)


def calculer(conn: sqlite3.Connection, exercice_id: int) -> Bilan:
    """Calcul complet, sans contrôle de droit (utilisé aussi par la clôture et le tableau de bord)."""
    exercice = exercices.get(conn, exercice_id)
    if exercice is None:
        raise BilanError("Exercice introuvable.")
    try:
        mensuel = tableau_mensuel.tableau(conn, exercice_id).general
        funeraire = tableau_funeraire.tableau(conn, exercice_id).general
    except (TableauError, TableauFuneraireError) as exc:
        raise BilanError(str(exc)) from None

    parallele_du = parallele_dettes = parallele_avances = 0
    for _, totaux in tableau_parallele.list_resumes(conn, exercice_id):
        parallele_du += totaux.du
        parallele_dettes += totaux.dette
        parallele_avances += totaux.avance

    # « perçu » = tout l'argent encaissé dans l'exercice, arriérés remboursés compris
    percu = {
        rubrique: sum(versements.totals_by_member(conn, exercice_id, rubrique).values())
        for rubrique in (MENSUELLE, FUNERAIRE, PARALLELE)
    }
    amendes = amende_service.resume(conn, exercice_id)
    depenses = depense_service.resume(conn, exercice_id)

    dette_par = reports_repo.total(conn, exercice_id, "dette", "parallele")
    avance_par = reports_repo.total(conn, exercice_id, "avance", "parallele")
    dette_am = reports_repo.total(conn, exercice_id, "dette", "amende")
    avance_am = reports_repo.total(conn, exercice_id, "avance", "amende")
    payes_par = versements.total_arrears_paid(conn, exercice_id, "parallele")
    payes_am = versements.total_arrears_paid(conn, exercice_id, "amende")

    lignes = (
        LigneBilan("mensuelle", "Cotisations mensuelles", mensuel.du, percu[MENSUELLE],
                   mensuel.dette, mensuel.avance, mensuel.dette_reportee, mensuel.avance_reportee),
        LigneBilan("funeraire", "Cotisations funéraires", funeraire.du, percu[FUNERAIRE],
                   funeraire.dette, funeraire.avance, funeraire.dette_reportee, funeraire.avance_reportee),
        LigneBilan("parallele", "Cotisations parallèles", parallele_du, percu[PARALLELE],
                   parallele_dettes + dette_par - payes_par, parallele_avances + avance_par,
                   dette_par, avance_par),
        LigneBilan("reliquats", "Reliquats", None, depenses.reliquat),
        LigneBilan("amendes", "Amendes", amendes.attendu, amendes.collecte + payes_am,
                   amendes.manque + dette_am - payes_am, avance_am, dette_am, avance_am),
    )
    return Bilan(exercice, lignes, depenses.depense, depenses.prevu,
                 reports_repo.solde_ouverture(conn, exercice_id))


def consulter(conn: sqlite3.Connection, session: Session, exercice_id: int) -> Bilan:
    """Bilan consultable par l'administrateur uniquement."""
    session.require(Permission.BALANCE_VIEW)
    return calculer(conn, exercice_id)