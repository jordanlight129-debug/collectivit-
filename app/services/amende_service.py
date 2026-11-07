"""Règles des amendes (cahier des charges §3.7)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from app.database.connection import transaction
from app.models.amende import STATUTS, Amende, AmendeLigne
from app.repositories import amendes, encaissements_amendes, exercices, membres
from app.security import audit
from app.security.audit import Action
from app.security.session import Permission, Session
from app.services import carnet_service


class AmendeError(Exception):
    """Règle de gestion des amendes non respectée (message affichable)."""


@dataclass(frozen=True)
class TotauxAmendes:
    attendu: int
    collecte: int
    manque: int          # manque à gagner = part non encaissée


@dataclass(frozen=True)
class PageAmendes:
    lignes: list[AmendeLigne]
    total: int
    page: TotauxAmendes      # totaux des lignes affichées
    general: TotauxAmendes   # totaux de tout le résultat filtré


def _fmt(amount: int) -> str:
    return f"{amount:,}".replace(",", "\u00A0") + " FCFA"


def _d(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def creer_amende(conn: sqlite3.Connection, session: Session, membre_id: int, nom: str,
                 libelle: str, montant_attendu: int, date_amende: date | None = None,
                 montant_collecte: int = 0, today: date | None = None) -> Amende:
    session.require(Permission.FINE_CREATE)
    today = today or date.today()
    nom = " ".join((nom or "").split())
    if len(nom) < 2:
        raise AmendeError("Le nom de l'amende est obligatoire (2 caractères minimum).")
    if len(nom) > 100:
        raise AmendeError("Le nom de l'amende est trop long (100 caractères maximum).")
    libelle = " ".join((libelle or "").split()) or nom
    if len(libelle) > 200:
        raise AmendeError("Le libellé est trop long (200 caractères maximum).")
    if not _is_int(montant_attendu) or montant_attendu <= 0:
        raise AmendeError("Le montant de l'amende doit être un entier positif (en FCFA).")
    if not _is_int(montant_collecte) or montant_collecte < 0:
        raise AmendeError("Le montant déjà collecté doit être un entier positif ou nul.")
    if montant_collecte > montant_attendu:
        raise AmendeError("Le montant collecté ne peut pas dépasser le montant de l'amende.")

    membre = membres.get(conn, membre_id)
    if membre is None:
        raise AmendeError("Membre introuvable.")
    date_amende = date_amende or today
    if not isinstance(date_amende, date):
        raise AmendeError("La date de l'amende est invalide.")
    if date_amende > today:
        raise AmendeError("La date de l'amende ne peut pas être dans le futur.")
    if date_amende < membre.date_adhesion:
        raise AmendeError(f"La date de l'amende ne peut pas précéder l'adhésion ({_d(membre.date_adhesion)}).")
    if membre.date_deces and date_amende > membre.date_deces:
        raise AmendeError(f"{membre.nom} est décédé le {_d(membre.date_deces)} : on ne peut plus l'amender.")

    exercice = exercices.get_for_date(conn, date_amende)
    if exercice is None:
        raise AmendeError("Aucun exercice ne couvre la date de l'amende. Créez d'abord cet exercice.")
    if not exercice.is_open:
        raise AmendeError(f"L'exercice {exercice.libelle} est clôturé : on ne peut plus y ajouter d'amende.")

    with transaction(conn):
        amende_id = amendes.create(conn, exercice.id, membre.id, nom, libelle, date_amende,
                                   montant_attendu, montant_collecte, session.user.id)
        if montant_collecte > 0:
            encaissements_amendes.add(conn, amende_id, montant_collecte, date_amende, session.user.id)
        audit.log(conn, session.user, Action.AMENDE_AJOUT, carnet_service.format_carnet_label(membre.numero_carnet),
                  f"{nom} · {_fmt(montant_attendu)} · déjà collecté {_fmt(montant_collecte)} · "
                  f"{_d(date_amende)} · exercice {exercice.libelle}")
    return amendes.get(conn, amende_id)


def collecter(conn: sqlite3.Connection, session: Session, amende_id: int, montant: int,
              date_encaissement: date | None = None, today: date | None = None) -> Amende:
    """Encaisse tout ou partie d'une amende (champ de collecte). Chaque encaissement est historisé."""
    session.require(Permission.FINE_CREATE)
    today = today or date.today()
    amende = amendes.get(conn, amende_id)
    if amende is None:
        raise AmendeError("Amende introuvable.")
    exercice = exercices.get(conn, amende.exercice_id)
    if not exercice.is_open:
        raise AmendeError(f"L'exercice {exercice.libelle} est clôturé : cette amende ne peut plus changer.")
    date_encaissement = date_encaissement or today
    if not isinstance(date_encaissement, date):
        raise AmendeError("La date de l'encaissement est invalide.")
    if date_encaissement > today:
        raise AmendeError("La date de l'encaissement ne peut pas être dans le futur.")
    if date_encaissement < amende.date_amende:
        raise AmendeError(f"La date de l'encaissement ne peut pas précéder celle de l'amende ({_d(amende.date_amende)}).")
    if not _is_int(montant) or montant <= 0:
        raise AmendeError("Le montant encaissé doit être un entier positif (en FCFA).")
    reste = amende.manque_a_gagner
    if reste == 0:
        raise AmendeError("Cette amende est déjà entièrement encaissée.")
    if montant > reste:
        raise AmendeError(f"Le montant dépasse le reste à encaisser ({_fmt(reste)}).")

    membre = membres.get(conn, amende.membre_id)
    with transaction(conn):
        amendes.add_collecte(conn, amende_id, montant)
        encaissements_amendes.add(conn, amende_id, montant, date_encaissement, session.user.id)
        audit.log(conn, session.user, Action.AMENDE_COLLECTE, carnet_service.format_carnet_label(membre.numero_carnet),
                  f"{_fmt(montant)} sur « {amende.nom} » · {_d(date_encaissement)} · "
                  f"reste {_fmt(reste - montant)}")
    return amendes.get(conn, amende_id)


def get_amende(conn: sqlite3.Connection, amende_id: int) -> Amende | None:
    return amendes.get(conn, amende_id)


def lister(conn: sqlite3.Connection, exercice_id: int, *, search: str | None = None,
           statut: str | None = None, membre_id: int | None = None,
           limit: int | None = None, offset: int = 0) -> PageAmendes:
    if exercices.get(conn, exercice_id) is None:
        raise AmendeError("Exercice introuvable.")
    if statut is not None and statut not in STATUTS:
        raise AmendeError("Statut inconnu.")
    search = (search or "").strip() or None
    lignes = amendes.list_(conn, exercice_id, search=search, statut=statut,
                           membre_id=membre_id, limit=limit, offset=offset)
    page = TotauxAmendes(
        attendu=sum(l.amende.montant_attendu for l in lignes),
        collecte=sum(l.amende.montant_collecte for l in lignes),
        manque=sum(l.amende.manque_a_gagner for l in lignes),
    )
    general = TotauxAmendes(*amendes.totals(conn, exercice_id, search=search, statut=statut,
                                            membre_id=membre_id))
    total = amendes.count(conn, exercice_id, search=search, statut=statut, membre_id=membre_id)
    return PageAmendes(lignes, total, page, general)


def resume(conn: sqlite3.Connection, exercice_id: int) -> TotauxAmendes:
    """Attendu, collecté et manque à gagner de l'exercice (bilan, tableau de bord)."""
    if exercices.get(conn, exercice_id) is None:
        raise AmendeError("Exercice introuvable.")
    return TotauxAmendes(*amendes.totals(conn, exercice_id))