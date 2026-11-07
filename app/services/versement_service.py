"""Règles des versements et relevé mensuel d'un membre (cahier des charges §3.3)."""
from __future__ import annotations

import sqlite3
from datetime import date

from app.database.connection import transaction
from app.models.exercice import Exercice
from app.models.versement import (
    FUNERAIRE, MENSUELLE, PARALLELE, RUBRIQUE_LABELS, RUBRIQUES_SAISISSABLES, Versement,
)
from app.repositories import cotisations_paralleles, exercices, membres, reports, versements
from app.security import audit
from app.security.audit import Action
from app.security.session import Permission, Session
from app.services import carnet_service, cotisation_mensuelle
from app.services.regles import concerned_by_parallel


class VersementError(Exception):
    """Règle de gestion des versements non respectée (message affichable)."""


def _fmt(amount: int) -> str:
    return f"{amount:,}".replace(",", "\u00A0") + " FCFA"


def _d(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _clean_montant(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise VersementError("Le montant doit être un entier positif (en FCFA).")
    return value


def _clean_note(value: str | None) -> str | None:
    note = " ".join((value or "").split())
    if len(note) > 200:
        raise VersementError("La note est trop longue (200 caractères maximum).")
    return note or None


def _open_exercice(conn: sqlite3.Connection, exercice_id: int) -> Exercice:
    exercice = exercices.get(conn, exercice_id)
    if exercice is None:
        raise VersementError("Exercice introuvable.")
    if not exercice.is_open:
        raise VersementError(f"L'exercice {exercice.libelle} est clôturé : ses versements ne peuvent plus changer.")
    return exercice


def _clean_date(value: date | None, adhesion: date, today: date) -> date:
    value = value or today
    if not isinstance(value, date):
        raise VersementError("La date du versement est invalide.")
    if value > today:
        raise VersementError("La date du versement ne peut pas être dans le futur.")
    if value < adhesion:
        raise VersementError(f"La date du versement ne peut pas précéder l'adhésion ({_d(adhesion)}).")
    return value


def enregistrer(conn: sqlite3.Connection, session: Session, membre_id: int, exercice_id: int,
                rubrique: str, montant: int, date_versement: date | None = None,
                note: str | None = None, today: date | None = None,
                cotisation_id: int | None = None) -> Versement:
    session.require(Permission.PAYMENT_CREATE)
    today = today or date.today()
    montant = _clean_montant(montant)
    if rubrique not in RUBRIQUES_SAISISSABLES:
        raise VersementError("Rubrique de versement invalide.")

    cotisation = None
    if rubrique == PARALLELE:
        if cotisation_id is None:
            raise VersementError("Choisissez la cotisation parallèle.")
        cotisation = cotisations_paralleles.get(conn, cotisation_id)
        if cotisation is None:
            raise VersementError("Cotisation parallèle introuvable.")
        if cotisation.exercice_id != exercice_id:
            raise VersementError("Cette cotisation parallèle n'appartient pas à l'exercice choisi.")
    elif cotisation_id is not None:
        raise VersementError("Une cotisation parallèle ne se choisit que pour la rubrique « parallèle ».")

    exercice = _open_exercice(conn, exercice_id)
    membre = membres.get(conn, membre_id)
    if membre is None:
        raise VersementError("Membre introuvable.")
    if cotisation is not None and not concerned_by_parallel(
            membre.date_adhesion, membre.date_deces, cotisation.date_debut, cotisation.date_fin):
        raise VersementError(f"{membre.nom} n'est pas concerné par la cotisation « {cotisation.nom} ».")
    date_versement = _clean_date(date_versement, membre.date_adhesion, today)
    note = _clean_note(note)

    libelle = RUBRIQUE_LABELS[rubrique]
    if cotisation is not None:
        libelle += f" « {cotisation.nom} »"
    with transaction(conn):
        versement_id = versements.add(conn, membre.id, exercice.id, rubrique, date_versement,
                                      montant, note, session.user.id,
                                      cotisation.id if cotisation else None)
        audit.log(conn, session.user, Action.VERSEMENT_AJOUT, carnet_service.format_carnet_label(membre.numero_carnet),
                  f"{_fmt(montant)} · {libelle} · {_d(date_versement)} · exercice {exercice.libelle}")
    return versements.get(conn, versement_id)


def modifier(conn: sqlite3.Connection, session: Session, versement_id: int, montant: int,
             date_versement: date, note: str | None = None, today: date | None = None) -> Versement:
    """Administrateur uniquement."""
    session.require(Permission.PAYMENT_EDIT)
    today = today or date.today()
    ancien = versements.get(conn, versement_id)
    if ancien is None:
        raise VersementError("Versement introuvable.")
    if ancien.nature == "arriere":
        raise VersementError("Un règlement d'arriérés ne se modifie pas : "
                             "l'administrateur peut le supprimer, puis il se saisit de nouveau.")
    exercice = _open_exercice(conn, ancien.exercice_id)
    membre = membres.get(conn, ancien.membre_id)
    montant = _clean_montant(montant)
    date_versement = _clean_date(date_versement, membre.date_adhesion, today)
    note = _clean_note(note)

    with transaction(conn):
        versements.update(conn, versement_id, montant, date_versement, note)
        audit.log(conn, session.user, Action.VERSEMENT_MODIF, carnet_service.format_carnet_label(membre.numero_carnet),
                  f"{_fmt(ancien.montant)} du {_d(ancien.date_versement)} → "
                  f"{_fmt(montant)} du {_d(date_versement)} · exercice {exercice.libelle}")
    return versements.get(conn, versement_id)


def supprimer(conn: sqlite3.Connection, session: Session, versement_id: int) -> None:
    """Administrateur uniquement."""
    session.require(Permission.DELETE)
    versement = versements.get(conn, versement_id)
    if versement is None:
        raise VersementError("Versement introuvable.")
    exercice = _open_exercice(conn, versement.exercice_id)
    membre = membres.get(conn, versement.membre_id)
    with transaction(conn):
        versements.delete(conn, versement_id)
        audit.log(conn, session.user, Action.VERSEMENT_SUPPR, carnet_service.format_carnet_label(membre.numero_carnet),
                  f"{_fmt(versement.montant)} du {_d(versement.date_versement)} · "
                  f"{RUBRIQUE_LABELS[versement.rubrique]} · exercice {exercice.libelle}")


def list_versements(conn: sqlite3.Connection, membre_id: int, *, exercice_id: int | None = None,
                    rubrique: str | None = None) -> list[Versement]:
    return versements.list_for_member(conn, membre_id, exercice_id=exercice_id, rubrique=rubrique)


def releve_mensuel(conn: sqlite3.Connection, membre_id: int,
                   exercice_id: int) -> cotisation_mensuelle.MonthlyStatement:
    """Les 12 cases, le dû, la dette et l'avance d'un membre pour un exercice,
    avec ses dettes et avances reportées (la plus ancienne dette d'abord)."""
    exercice = exercices.get(conn, exercice_id)
    if exercice is None:
        raise VersementError("Exercice introuvable.")
    membre = membres.get(conn, membre_id)
    if membre is None:
        raise VersementError("Membre introuvable.")
    tarif = exercices.get_tarifs(conn, exercice_id).get(membre.sexe)
    if tarif is None:
        raise VersementError(f"Aucun montant mensuel défini pour {membre.sexe.label.lower()}s en {exercice.libelle}.")
    total = versements.total_paid(conn, membre_id, exercice_id, MENSUELLE)
    dette = reports.member_amount(conn, exercice_id, membre_id, "dette", "mensuelle")
    avance = reports.member_amount(conn, exercice_id, membre_id, "avance", "mensuelle")
    return cotisation_mensuelle.monthly_statement(
        membre.date_adhesion, membre.date_deces, exercice.months, tarif, total, dette, avance)