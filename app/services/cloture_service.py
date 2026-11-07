"""Clôture d'exercice (cahier des charges §3.2).

À la clôture, les soldes, dettes et avances sont reportés automatiquement
sur l'exercice suivant. Opération irréversible, réservée à l'administrateur :
aperçu, confirmation explicite, puis tout se fait dans une seule transaction.
Chaque dette reportée garde son exercice d'origine (« arriérés de 2025-2026 »).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from app.database.connection import transaction
from app.models.exercice import Exercice
from app.models.membre import Membre
from app.repositories import exercices, membres, reports, versements
from app.security import audit
from app.security.audit import Action
from app.security.session import Permission, Session
from app.services import (
    amende_service, bilan_service, calendrier, parallele_service, tableau_funeraire,
    tableau_mensuel, tableau_parallele,
)
from app.services.bilan_service import BilanError
from app.services.tableau_funeraire import TableauFuneraireError
from app.services.tableau_mensuel import TableauError

CONFIRMATION = "CLÔTURER"
DETTE, AVANCE, SOLDE = "dette", "avance", "solde"
_RUBRIQUE_ORDRE = {"mensuelle": 0, "funeraire": 1, "parallele": 2, "amende": 3}


class ClotureError(Exception):
    """Clôture impossible ou refusée (message affichable)."""


@dataclass(frozen=True)
class LigneReport:
    membre: Membre
    type: str                 # DETTE | AVANCE
    rubrique: str
    montant: int


@dataclass(frozen=True)
class Apercu:
    exercice: Exercice
    suivant_libelle: str
    suivant_existe: bool
    solde: int                          # solde cumulé (ouverture + résultat), peut être négatif
    lignes: tuple[LigneReport, ...]     # dettes et avances par membre et par rubrique
    blocage: str | None                 # raison pour laquelle on ne peut pas clôturer maintenant

    def total(self, type_: str, rubrique: str | None = None) -> int:
        return sum(l.montant for l in self.lignes
                   if l.type == type_ and (rubrique is None or l.rubrique == rubrique))

    @property
    def total_dettes(self) -> int:
        return self.total(DETTE)

    @property
    def total_avances(self) -> int:
        return self.total(AVANCE)

    @property
    def membres_en_dette(self) -> int:
        return len({l.membre.id for l in self.lignes if l.type == DETTE})

    @property
    def membres_en_avance(self) -> int:
        return len({l.membre.id for l in self.lignes if l.type == AVANCE})


@dataclass(frozen=True)
class ResultatCloture:
    exercice: Exercice          # l'exercice clôturé
    suivant: Exercice           # l'exercice qui reçoit les reports
    solde: int
    total_dettes: int
    total_avances: int
    lignes_reportees: int       # nombre de lignes de report enregistrées


def _fmt(amount: int) -> str:
    return f"{amount:,}".replace(",", "\u00A0") + " FCFA"


def _d(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _blocage(conn: sqlite3.Connection, exercice: Exercice, suivant: Exercice | None,
             today: date) -> str | None:
    if not exercice.is_open:
        return f"L'exercice {exercice.libelle} est déjà clôturé."
    if today <= exercice.date_fin:
        return (f"L'exercice {exercice.libelle} ne se termine que le {_d(exercice.date_fin)} : "
                "il ne peut pas être clôturé avant.")
    ancien = exercices.first_open_before(conn, exercice.date_debut)
    if ancien is not None:
        return f"Clôturez d'abord l'exercice {ancien.libelle}."
    if suivant is not None and not suivant.is_open:
        return (f"L'exercice suivant {suivant.libelle} est déjà clôturé : "
                "impossible d'y reporter les soldes.")
    return None


def _restes_plus_ancien_d_abord(dettes: list[tuple[int, int]], paye: int) -> list[tuple[int, int]]:
    """dettes : [(exercice d'origine, montant)] du plus ancien au plus récent.
    Répartit `paye` sur les dettes, la plus ancienne d'abord, et retourne ce qui reste."""
    restes = []
    for origine, montant in dettes:
        part = min(paye, montant)
        paye -= part
        if montant > part:
            restes.append((origine, montant - part))
    return restes


def _reports(conn: sqlite3.Connection, exercice: Exercice) -> tuple[int, dict]:
    """(solde cumulé, {(membre_id, type, rubrique, exercice d'origine): montant}) à reporter.

    - dette de l'exercice : origine = cet exercice ;
    - arriérés restants (reports reçus − remboursements) : origine conservée ;
    - mensuelle : les versements ont réglé la plus ancienne dette d'abord ;
    - funéraire, parallèle, amendes : seuls les paiements d'arriérés explicites réduisent les arriérés ;
    - solde : d'ouverture + résultat de l'année.
    """
    cumul: dict[tuple[int, str, str, int], int] = {}

    def add(membre_id: int, type_: str, rubrique: str, montant: int, origine: int) -> None:
        if montant > 0:
            key = (membre_id, type_, rubrique, origine)
            cumul[key] = cumul.get(key, 0) + montant

    try:
        recus = {r: reports.by_member_and_origin(conn, exercice.id, "dette", r) for r in _RUBRIQUE_ORDRE}
        payes = {r: versements.arrears_paid(conn, exercice.id, r) for r in ("funeraire", "parallele", "amende")}

        for l in tableau_mensuel.tableau(conn, exercice.id).lignes:
            mid = l.membre.id
            add(mid, DETTE, "mensuelle", l.releve.debt, exercice.id)
            add(mid, AVANCE, "mensuelle", l.releve.advance, exercice.id)
            for origine, reste in _restes_plus_ancien_d_abord(
                    recus["mensuelle"].get(mid, []), l.releve.carried_debt_paid):
                add(mid, DETTE, "mensuelle", reste, origine)
        for l in tableau_funeraire.tableau(conn, exercice.id).lignes:
            add(l.membre.id, DETTE, "funeraire", l.releve.debt, exercice.id)
            add(l.membre.id, AVANCE, "funeraire", l.releve.advance, exercice.id)
        for cotisation in parallele_service.list_cotisations(conn, exercice.id):
            for l in tableau_parallele.tableau(conn, cotisation.id).lignes:
                add(l.membre.id, DETTE, "parallele", l.releve.debt, exercice.id)
                add(l.membre.id, AVANCE, "parallele", l.releve.advance, exercice.id)
        for l in amende_service.lister(conn, exercice.id).lignes:
            add(l.amende.membre_id, DETTE, "amende", l.amende.manque_a_gagner, exercice.id)
        for rubrique in ("funeraire", "parallele", "amende"):
            for mid, items in recus[rubrique].items():
                for origine, montant in items:
                    add(mid, DETTE, rubrique, montant - payes[rubrique].get((mid, origine), 0), origine)
        for rubrique in ("parallele", "amende"):
            for mid, montant in reports.by_member(conn, exercice.id, "avance", rubrique).items():
                add(mid, AVANCE, rubrique, montant, exercice.id)
        solde = bilan_service.calculer(conn, exercice.id).solde_cumule
    except (TableauError, TableauFuneraireError, BilanError) as exc:
        raise ClotureError(str(exc)) from None
    return int(solde), cumul


def apercu(conn: sqlite3.Connection, session: Session, exercice_id: int,
           today: date | None = None) -> Apercu:
    """Ce qui sera reporté, et ce qui empêche éventuellement de clôturer."""
    session.require(Permission.EXERCISE_CLOSE)
    today = today or date.today()
    exercice = exercices.get(conn, exercice_id)
    if exercice is None:
        raise ClotureError("Exercice introuvable.")
    suivant_libelle = calendrier.libelle(exercice.start_year + 1)
    suivant = exercices.get_by_libelle(conn, suivant_libelle)

    solde, cumul = _reports(conn, exercice)
    agrege: dict[tuple[int, str, str], int] = {}
    for (mid, type_, rubrique, _origine), montant in cumul.items():
        key = (mid, type_, rubrique)
        agrege[key] = agrege.get(key, 0) + montant
    par_id = {m.id: m for m in membres.list_(conn)}
    lignes = sorted(
        (LigneReport(par_id[mid], type_, rubrique, montant)
         for (mid, type_, rubrique), montant in agrege.items()),
        key=lambda l: (l.membre.numero_carnet, _RUBRIQUE_ORDRE[l.rubrique], l.type),
    )
    return Apercu(exercice, suivant_libelle, suivant is not None, solde, tuple(lignes),
                  _blocage(conn, exercice, suivant, today))


def cloturer(conn: sqlite3.Connection, session: Session, exercice_id: int, confirmation: str,
             today: date | None = None) -> ResultatCloture:
    """Clôture l'exercice et reporte soldes, dettes et avances. Irréversible."""
    session.require(Permission.EXERCISE_CLOSE)
    today = today or date.today()
    exercice = exercices.get(conn, exercice_id)
    if exercice is None:
        raise ClotureError("Exercice introuvable.")
    suivant_libelle = calendrier.libelle(exercice.start_year + 1)
    suivant = exercices.get_by_libelle(conn, suivant_libelle)

    blocage = _blocage(conn, exercice, suivant, today)
    if blocage:
        raise ClotureError(blocage)
    if (confirmation or "").strip().upper() != CONFIRMATION:
        raise ClotureError(f"Saisissez « {CONFIRMATION} » pour confirmer la clôture.")

    solde, cumul = _reports(conn, exercice)
    total_dettes = sum(m for (_, t, _, _), m in cumul.items() if t == DETTE)
    total_avances = sum(m for (_, t, _, _), m in cumul.items() if t == AVANCE)

    with transaction(conn):
        creation = suivant is None
        if creation:
            debut, fin = calendrier.bounds(exercice.start_year + 1)
            suivant_id = exercices.create(conn, suivant_libelle, debut, fin)
            for sexe, montant in exercices.get_tarifs(conn, exercice.id).items():
                exercices.upsert_tarif(conn, suivant_id, sexe, montant)
            for sexe, montant in exercices.get_funeral_tarifs(conn, exercice.id).items():
                exercices.upsert_funeral_tarif(conn, suivant_id, sexe, montant)
        else:
            suivant_id = suivant.id

        for (membre_id, type_, rubrique, origine), montant in sorted(cumul.items()):
            reports.add(conn, exercice.id, suivant_id, membre_id, type_, rubrique, montant,
                        exercice_origine_id=origine)
        reports.add(conn, exercice.id, suivant_id, None, SOLDE, None, solde)
        exercices.close(conn, exercice.id, today)

        detail = (f"Reports vers {suivant_libelle} : dettes {_fmt(total_dettes)} · "
                  f"avances {_fmt(total_avances)} · solde {_fmt(solde)}")
        if creation:
            detail += " · exercice suivant créé avec les mêmes montants"
        audit.log(conn, session.user, Action.CLOTURE, f"Exercice {exercice.libelle}", detail)

    return ResultatCloture(
        exercice=exercices.get(conn, exercice.id),
        suivant=exercices.get(conn, suivant_id),
        solde=solde, total_dettes=total_dettes, total_avances=total_avances,
        lignes_reportees=len(cumul) + 1,
    )