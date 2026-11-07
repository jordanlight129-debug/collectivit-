"""Règles des dépenses et des reliquats (cahier des charges §3.6 et §3.8).

Si le montant dépensé est inférieur au montant prévu, la différence est
enregistrée comme reliquat : une entrée liée à la dépense d'origine.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.database.connection import transaction
from app.models.depense import Depense, DepenseLigne, ReliquatLigne
from app.repositories import depenses, exercices, reliquats
from app.security import audit
from app.security.audit import Action
from app.security.session import Permission, Session


class DepenseError(Exception):
    """Règle de gestion des dépenses non respectée (message affichable)."""


@dataclass(frozen=True)
class TotauxDepenses:
    prevu: Decimal
    depense: Decimal
    reliquat: Decimal


@dataclass(frozen=True)
class PageDepenses:
    lignes: list[DepenseLigne]
    total: int
    page: TotauxDepenses      # totaux des lignes affichées
    general: TotauxDepenses   # totaux de tout le résultat filtré


def _fmt(amount: int | Decimal) -> str:
    return f"{amount:,.0f}".replace(",", "\u00A0") + " FCFA"


def _d(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _check_montant(value: int | Decimal, label: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float) or not isinstance(value, (int, Decimal)):
        raise DepenseError(f"{label} : entrez un montant entier positif ou nul (en FCFA).")
    amount = Decimal(value)
    if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value():
        raise DepenseError(f"{label} : entrez un montant entier positif ou nul (en FCFA).")
    return amount


def enregistrer_depense(conn: sqlite3.Connection, session: Session, libelle: str,
                        montant_depense: int | Decimal, beneficiaire: str | None = None,
                        montant_prevu: int | Decimal | None = None, date_depense: date | None = None,
                        today: date | None = None) -> Depense:
    """Enregistre une dépense. Sans montant prévu, le prévu est égal au dépensé."""
    session.require(Permission.EXPENSE_CREATE)
    today = today or date.today()
    libelle = " ".join((libelle or "").split())
    if len(libelle) < 2:
        raise DepenseError("Le libellé est obligatoire (2 caractères minimum).")
    if len(libelle) > 150:
        raise DepenseError("Le libellé est trop long (150 caractères maximum).")
    beneficiaire = " ".join((beneficiaire or "").split()) or None
    if beneficiaire and len(beneficiaire) > 100:
        raise DepenseError("Le bénéficiaire est trop long (100 caractères maximum).")
    montant_depense = _check_montant(montant_depense, "Montant dépensé")
    if montant_prevu is None:
        montant_prevu = montant_depense
    else:
        montant_prevu = _check_montant(montant_prevu, "Montant prévu")
    if montant_prevu == 0 and montant_depense == 0:
        raise DepenseError("Au moins un des deux montants doit être supérieur à 0.")
    date_depense = date_depense or today
    if not isinstance(date_depense, date):
        raise DepenseError("La date de la dépense est invalide.")
    if date_depense > today:
        raise DepenseError("La date de la dépense ne peut pas être dans le futur.")

    exercice = exercices.get_for_date(conn, date_depense)
    if exercice is None:
        raise DepenseError("Aucun exercice ne couvre la date de la dépense. Créez d'abord cet exercice.")
    if not exercice.is_open:
        raise DepenseError(f"L'exercice {exercice.libelle} est clôturé : on ne peut plus y ajouter de dépense.")

    reliquat = max(montant_prevu - montant_depense, Decimal(0))
    with transaction(conn):
        depense_id = depenses.create(conn, exercice.id, date_depense, libelle, beneficiaire,
                                     montant_prevu, montant_depense, session.user.id)
        detail = (f"Prévu {_fmt(montant_prevu)} · dépensé {_fmt(montant_depense)} · "
                  f"{beneficiaire or 'sans bénéficiaire'} · {_d(date_depense)} · exercice {exercice.libelle}")
        if reliquat > 0:
            reliquats.create(conn, exercice.id, depense_id, f"Reliquat — {libelle}", reliquat, date_depense)
            detail += f" · reliquat de {_fmt(reliquat)} généré"
        audit.log(conn, session.user, Action.DEPENSE_AJOUT, f"Dépense — {libelle}", detail)
    return depenses.get(conn, depense_id)


def supprimer_depense(conn: sqlite3.Connection, session: Session, depense_id: int) -> None:
    """Administrateur uniquement. Supprime aussi le reliquat lié."""
    session.require(Permission.DELETE)
    depense = depenses.get(conn, depense_id)
    if depense is None:
        raise DepenseError("Dépense introuvable.")
    exercice = exercices.get(conn, depense.exercice_id)
    if not exercice.is_open:
        raise DepenseError(f"L'exercice {exercice.libelle} est clôturé : cette dépense ne peut plus changer.")
    reliquat = reliquats.get_by_depense(conn, depense_id)
    with transaction(conn):
        depenses.delete(conn, depense_id)
        detail = (f"{_fmt(depense.montant_depense)} du {_d(depense.date_depense)} · "
                  f"exercice {exercice.libelle}")
        if reliquat:
            detail += f" · reliquat de {_fmt(reliquat.montant)} supprimé avec elle"
        audit.log(conn, session.user, Action.DEPENSE_SUPPR, f"Dépense — {depense.libelle}", detail)


def lister_depenses(conn: sqlite3.Connection, exercice_id: int, *, search: str | None = None,
                    date_debut: date | None = None, date_fin: date | None = None,
                    avec_reliquat: bool | None = None, limit: int | None = None,
                    offset: int = 0) -> PageDepenses:
    if exercices.get(conn, exercice_id) is None:
        raise DepenseError("Exercice introuvable.")
    search = (search or "").strip() or None
    lignes = depenses.list_(conn, exercice_id, search=search, date_debut=date_debut,
                            date_fin=date_fin, avec_reliquat=avec_reliquat, limit=limit, offset=offset)
    page = TotauxDepenses(
        prevu=sum((l.depense.montant_prevu for l in lignes), Decimal(0)),
        depense=sum((l.depense.montant_depense for l in lignes), Decimal(0)),
        reliquat=sum((l.reliquat.montant for l in lignes if l.reliquat), Decimal(0)),
    )
    general = TotauxDepenses(*depenses.totals(conn, exercice_id, search=search, date_debut=date_debut,
                                              date_fin=date_fin, avec_reliquat=avec_reliquat))
    total = depenses.count(conn, exercice_id, search=search, date_debut=date_debut,
                           date_fin=date_fin, avec_reliquat=avec_reliquat)
    return PageDepenses(lignes, total, page, general)


def resume(conn: sqlite3.Connection, exercice_id: int) -> TotauxDepenses:
    """Prévu, dépensé et reliquats de l'exercice (bilan, tableau de bord)."""
    if exercices.get(conn, exercice_id) is None:
        raise DepenseError("Exercice introuvable.")
    return TotauxDepenses(*depenses.totals(conn, exercice_id))


def list_reliquats(conn: sqlite3.Connection, exercice_id: int) -> tuple[list[ReliquatLigne], int]:
    """Les reliquats de l'exercice (entrées) et leur total."""
    if exercices.get(conn, exercice_id) is None:
        raise DepenseError("Exercice introuvable.")
    return reliquats.list_for_exercice(conn, exercice_id), reliquats.total(conn, exercice_id)