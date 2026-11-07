"""Règles de gestion des membres (cahier des charges §3.1)."""
from __future__ import annotations

import sqlite3
from datetime import date

from app.database.connection import transaction
from app.models.membre import ACTIF, Membre
from app.models.sexe import Sexe
from app.repositories import membres
from app.security import audit
from app.security.audit import Action
from app.security.session import Permission, Session
from app.services import carnet_service


class MembreError(Exception):
    """Règle de gestion des membres non respectée (message affichable)."""


def _d(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _clean_nom(value: str) -> str:
    nom = " ".join((value or "").split())
    if len(nom) < 2:
        raise MembreError("Le nom complet est obligatoire (2 caractères minimum).")
    if len(nom) > 100:
        raise MembreError("Le nom complet est trop long (100 caractères maximum).")
    return nom


def _clean_sexe(value: Sexe | str) -> Sexe:
    try:
        return value if isinstance(value, Sexe) else Sexe(value)
    except ValueError:
        raise MembreError("Choisissez le sexe du membre.") from None


def _clean_adhesion(value: date | None, today: date) -> date:
    """Par défaut : aujourd'hui (date d'enregistrement). Une date passée est admise
    pour la reprise des membres existants ; une date future ne l'est pas : tant que
    la personne n'a pas adhéré, elle n'est pas membre."""
    if value is None:
        return today
    if not isinstance(value, date):
        raise MembreError("La date d'adhésion est invalide.")
    if value > today:
        raise MembreError("La date d'adhésion ne peut pas être dans le futur.")
    return value


def _resume(nom: str, sexe: Sexe, adhesion: date) -> str:
    return f"{nom} · {sexe.label} · adhésion {_d(adhesion)}"


def get_membre(conn: sqlite3.Connection, membre_id: int) -> Membre | None:
    return membres.get(conn, membre_id)


def get_by_carnet(conn: sqlite3.Connection, numero_carnet: str) -> Membre | None:
    return membres.get_by_carnet(conn, carnet_service.valider_carnet(numero_carnet))


def list_membres(conn: sqlite3.Connection, *, search: str | None = None,
                 statut: str | None = None, sexe: Sexe | None = None,
                 sort: str = "carnet", descending: bool = False,
                 limit: int | None = None, offset: int = 0) -> tuple[list[Membre], int]:
    """Retourne (membres de la page, total des résultats)."""
    search = (search or "").strip() or None
    rows = membres.list_(conn, search=search, statut=statut, sexe=sexe, sort=sort,
                         descending=descending, limit=limit, offset=offset)
    return rows, membres.count(conn, search=search, statut=statut, sexe=sexe)


def create_membre(conn: sqlite3.Connection, session: Session, nom: str, sexe: Sexe | str,
                  date_adhesion: date | None = None, today: date | None = None) -> Membre:
    """Crée un membre. Le numéro de carnet est attribué par le système."""
    session.require(Permission.MEMBER_CREATE)
    today = today or date.today()
    nom = _clean_nom(nom)
    sexe = _clean_sexe(sexe)
    adhesion = _clean_adhesion(date_adhesion, today)

    try:
        with transaction(conn):
            carnet = carnet_service.allocate(conn)
            membre_id = membres.create(conn, carnet, nom, sexe, adhesion)
            audit.log(conn, session.user, Action.MEMBRE_AJOUT, carnet_service.format_carnet_label(carnet),
                      _resume(nom, sexe, adhesion))
    except sqlite3.IntegrityError:
        raise MembreError("Impossible d'attribuer un numéro de carnet. Réessayez.") from None
    return membres.get(conn, membre_id)


def update_membre(conn: sqlite3.Connection, session: Session, membre_id: int, nom: str,
                  sexe: Sexe | str, date_adhesion: date, today: date | None = None) -> Membre:
    """Le numéro de carnet n'est jamais modifiable."""
    session.require(Permission.MEMBER_EDIT)
    today = today or date.today()
    membre = membres.get(conn, membre_id)
    if membre is None:
        raise MembreError("Membre introuvable.")
    nom = _clean_nom(nom)
    sexe = _clean_sexe(sexe)
    adhesion = _clean_adhesion(date_adhesion, today)
    if membre.date_deces and adhesion > membre.date_deces:
        raise MembreError("La date d'adhésion ne peut pas être postérieure au décès.")

    changes = []
    if nom != membre.nom:
        changes.append(f"nom : {membre.nom} → {nom}")
    if sexe != membre.sexe:
        changes.append(f"sexe : {membre.sexe.label} → {sexe.label}")
    if adhesion != membre.date_adhesion:
        changes.append(f"adhésion : {_d(membre.date_adhesion)} → {_d(adhesion)}")

    with transaction(conn):
        membres.update(conn, membre_id, nom, sexe, adhesion)
        if changes:
            audit.log(conn, session.user, Action.MEMBRE_MODIF, carnet_service.format_carnet_label(membre.numero_carnet),
                      " · ".join(changes))
    return membres.get(conn, membre_id)


def declare_deceased(conn: sqlite3.Connection, session: Session, membre_id: int,
                     date_deces: date | None = None, today: date | None = None) -> Membre:
    """Passe le membre au statut « décédé » : il devient inactif et ne cotise plus.
    Permis à l'administrateur et aux secrétaires."""
    session.require(Permission.DEATH_CREATE)
    today = today or date.today()
    date_deces = date_deces or today
    membre = membres.get(conn, membre_id)
    if membre is None:
        raise MembreError("Membre introuvable.")
    if membre.statut != ACTIF:
        raise MembreError(f"{membre.nom} est déjà déclaré décédé.")
    if date_deces < membre.date_adhesion:
        raise MembreError("La date du décès ne peut pas précéder l'adhésion.")
    if date_deces > today:
        raise MembreError("La date du décès ne peut pas être dans le futur.")

    with transaction(conn):
        membres.set_deceased(conn, membre_id, date_deces)
        audit.log(conn, session.user, Action.MEMBRE_DECES, carnet_service.format_carnet_label(membre.numero_carnet),
                  f"{membre.nom} · décès le {_d(date_deces)}")
    return membres.get(conn, membre_id)


def delete_membre(conn: sqlite3.Connection, session: Session, membre_id: int) -> None:
    """Administrateur uniquement ; impossible si le membre a un historique."""
    session.require(Permission.DELETE)
    membre = membres.get(conn, membre_id)
    if membre is None:
        raise MembreError("Membre introuvable.")
    try:
        with transaction(conn):
            membres.delete(conn, membre_id)
            audit.log(conn, session.user, Action.MEMBRE_SUPPR, carnet_service.format_carnet_label(membre.numero_carnet),
                      membre.nom)
    except sqlite3.IntegrityError:
        raise MembreError(
            f"{membre.nom} a un historique (versements, amendes ou décès) : "
            "suppression impossible. Conservez-le avec son statut."
        ) from None