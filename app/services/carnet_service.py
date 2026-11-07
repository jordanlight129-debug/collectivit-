"""Numéros de carnet du système.

Convention de référence : le carnet est une chaîne texte contenant exactement 4
chiffres (ex. "0042"), avec zéros initiaux conservés. Les fonctions ci-dessous
centralisent le formatage et la validation pour éviter les variantes dupliquées.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from app.database.connection import transaction
from app.repositories import membres, parametres
from app.security import audit
from app.security.audit import Action
from app.security.session import Permission, Session

KEY_PREFIX = "carnet_prefixe"
KEY_WIDTH = "carnet_largeur"
KEY_NEXT = "carnet_prochain"

DEFAULT_PREFIX = ""
DEFAULT_WIDTH = 4
DEFAULT_NEXT = 1

_PREFIX_RE = re.compile(r"^[A-Z0-9\-/]{0,10}$")


class CarnetError(Exception):
    """Format de numéro de carnet invalide (message affichable)."""


def formater_carnet(number: int, prefix: str = "", *, width: int = DEFAULT_WIDTH) -> str:
    """Formate un numéro d'ordre en chaîne texte, avec 4 chiffres par défaut."""
    if isinstance(number, bool) or not isinstance(number, int) or number < 0:
        raise CarnetError("Le numéro de carnet doit être un entier positif.")
    if isinstance(width, bool) or not isinstance(width, int) or width != DEFAULT_WIDTH:
        raise CarnetError("Le numéro de carnet doit contenir exactement 4 chiffres.")
    normalized_prefix = (prefix or "").strip().upper()
    if not _PREFIX_RE.match(normalized_prefix):
        raise CarnetError("Préfixe invalide : lettres, chiffres, « - » ou « / » (10 caractères maximum).")
    return f"{normalized_prefix}{number:0{width}d}"


def valider_carnet(numero: str) -> str:
    """Valide et normalise un carnet en texte. Autorise un préfixe optionnel, mais garde 4 chiffres numériques."""
    if numero is None:
        raise CarnetError("Le numéro de carnet est obligatoire.")
    value = str(numero).strip()
    if not value:
        raise CarnetError("Le numéro de carnet est obligatoire.")

    match = re.fullmatch(r"(?i)(?:(?P<prefix>[A-Z0-9\-/]{0,10})?(?P<num>\d{4}))", value)
    if match is None:
        raise CarnetError("Le numéro de carnet doit contenir exactement 4 chiffres, avec zéros initiaux conservés.")
    prefix = match.group("prefix") or ""
    return f"{prefix.upper()}{match.group('num')}" if prefix else match.group("num")


def format_carnet_label(numero: str | int | None) -> str:
    """Retourne le libellé normalisé, ex. 'Carnet 0001' ou 'Carnet LT-0043'."""
    if numero is None:
        return "Carnet inconnu"
    value = str(numero).strip()
    if not value:
        return "Carnet inconnu"
    return f"Carnet {valider_carnet(value)}"


@dataclass(frozen=True)
class CarnetFormat:
    prefix: str
    width: int
    next_number: int

    def render(self, number: int | None = None) -> str:
        n = self.next_number if number is None else number
        return formater_carnet(n, self.prefix, width=self.width)


def get_format(conn: sqlite3.Connection) -> CarnetFormat:
    raw_width = int(parametres.get(conn, KEY_WIDTH, str(DEFAULT_WIDTH)) or DEFAULT_WIDTH)
    width = DEFAULT_WIDTH if raw_width != DEFAULT_WIDTH else DEFAULT_WIDTH
    return CarnetFormat(
        prefix=(parametres.get(conn, KEY_PREFIX, DEFAULT_PREFIX) or "").strip().upper(),
        width=width,
        next_number=int(parametres.get(conn, KEY_NEXT, str(DEFAULT_NEXT)) or DEFAULT_NEXT),
    )


def preview(conn: sqlite3.Connection) -> str:
    """Prochain numéro assignable, sans le consommer, en gardant la convention 4 chiffres."""
    fmt = get_format(conn)
    n = fmt.next_number
    while True:
        numero = fmt.render(n)
        if not membres.get_by_carnet(conn, valider_carnet(numero)):
            return numero
        n += 1


def allocate(conn: sqlite3.Connection) -> str:
    """Attribue le prochain numéro libre dans une transaction SQLite protégée."""
    with transaction(conn):
        fmt = get_format(conn)
        n = fmt.next_number
        while True:
            numero = fmt.render(n)
            if not membres.get_by_carnet(conn, valider_carnet(numero)):
                parametres.set_(conn, KEY_NEXT, str(n + 1))
                return numero
            n += 1


def set_format(conn: sqlite3.Connection, session: Session, prefix: str, width: int,
               next_number: int) -> CarnetFormat:
    """Administrateur uniquement. La convention de référence impose 4 chiffres."""
    session.require(Permission.SETTINGS_MANAGE)
    prefix = (prefix or "").strip().upper()
    if not _PREFIX_RE.match(prefix):
        raise CarnetError("Préfixe invalide : lettres, chiffres, « - » ou « / » (10 caractères maximum).")
    if isinstance(width, bool) or not isinstance(width, int) or width != DEFAULT_WIDTH:
        raise CarnetError("Le numéro de carnet doit contenir exactement 4 chiffres.")
    if isinstance(next_number, bool) or not isinstance(next_number, int) or next_number < 1:
        raise CarnetError("Le prochain numéro doit être un entier supérieur ou égal à 1.")

    old = get_format(conn)
    new = CarnetFormat(prefix, width, next_number)
    with transaction(conn):
        parametres.set_(conn, KEY_PREFIX, new.prefix)
        parametres.set_(conn, KEY_WIDTH, str(new.width))
        parametres.set_(conn, KEY_NEXT, str(new.next_number))
        audit.log(conn, session.user, Action.CARNET_FORMAT, "Numéros de carnet",
                  f"{old.render()} → {new.render()}")
    return new