"""Authentification : premier administrateur, connexion, déconnexion, blocage."""
from __future__ import annotations

import math
import sqlite3
from datetime import datetime, timedelta

from app.database.connection import transaction
from app.repositories import utilisateurs
from app.security import audit
from app.security.audit import Action
from app.security.passwords import (
    hash_password, needs_rehash, validate_policy, verify_password,
)
from app.security.session import CurrentUser, Role, Session

MAX_ATTEMPTS = 5
LOCK_SECONDS = 30
_FMT = "%Y-%m-%d %H:%M:%S"


class AuthError(Exception):
    """Erreur d'authentification ou de création de compte."""


class InvalidCredentials(AuthError):
    def __init__(self, remaining: int | None = None) -> None:
        self.remaining = remaining
        msg = "Identifiant ou mot de passe incorrect."
        if remaining is not None and remaining > 0:
            msg += f" {remaining} essai{'s' if remaining > 1 else ''} restant{'s' if remaining > 1 else ''}."
        super().__init__(msg)


class AccountLocked(AuthError):
    def __init__(self, until: datetime, now: datetime | None = None) -> None:
        self.until = until
        seconds = max(1, int((until - (now or datetime.now())).total_seconds()))
        super().__init__(f"Compte verrouillé. Réessayez dans {seconds} seconde{'s' if seconds > 1 else ''}.")


class AccountDisabled(AuthError):
    def __init__(self) -> None:
        super().__init__("Ce compte est désactivé. Contactez l'administrateur.")


_dummy_hash: str | None = None


def _dummy() -> str:
    """Hash factice pour égaliser le temps de réponse (identifiant inconnu)."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("Factice-0000")
    return _dummy_hash


def has_admin(conn: sqlite3.Connection) -> bool:
    return utilisateurs.count_by_role(conn, Role.ADMINISTRATEUR) > 0


def create_first_admin(conn: sqlite3.Connection, identifiant: str, nom_complet: str,
                       password: str) -> int:
    """Crée l'administrateur initial (premier lancement uniquement)."""
    if has_admin(conn):
        raise AuthError("Un administrateur existe déjà.")
    identifiant, nom_complet = identifiant.strip(), nom_complet.strip()
    if not identifiant or not nom_complet:
        raise AuthError("L'identifiant et le nom complet sont obligatoires.")
    validate_policy(password)
    with transaction(conn):
        user_id = utilisateurs.create(conn, identifiant, nom_complet, hash_password(password),
                                      Role.ADMINISTRATEUR)
        audit.log(conn, None, Action.UTILISATEUR_AJOUT, identifiant, "Premier administrateur")
    return user_id


def login(conn: sqlite3.Connection, session: Session, identifiant: str, password: str,
          now: datetime | None = None) -> CurrentUser:
    now = now or datetime.now()
    identifiant = identifiant.strip()
    user = utilisateurs.get_by_identifiant(conn, identifiant)

    if user is None:
        verify_password(password, _dummy())
        with transaction(conn):
            audit.log(conn, None, Action.ECHEC_CONNEXION, identifiant=identifiant,
                      detail="Identifiant inconnu")
        raise InvalidCredentials()

    if not user.actif:
        with transaction(conn):
            audit.log(conn, None, Action.ECHEC_CONNEXION, identifiant=identifiant,
                      detail="Compte désactivé")
        raise AccountDisabled()

    if user.verrouille_jusqua:
        until = datetime.strptime(user.verrouille_jusqua, _FMT)
        if now < until:
            raise AccountLocked(until, now)

    if not verify_password(password, user.mot_de_passe_hash):
        attempts = user.tentatives_echouees + 1
        locked_until: datetime | None = None
        with transaction(conn):
            if attempts >= MAX_ATTEMPTS:
                locked_until = now + timedelta(seconds=LOCK_SECONDS)
                utilisateurs.record_failure(conn, user.id, 0, locked_until.strftime(_FMT))
                detail = f"Compte verrouillé {LOCK_SECONDS} s après {MAX_ATTEMPTS} échecs"
            else:
                utilisateurs.record_failure(conn, user.id, attempts, None)
                detail = f"Mot de passe incorrect ({attempts}/{MAX_ATTEMPTS})"
            audit.log(conn, None, Action.ECHEC_CONNEXION, identifiant=identifiant, detail=detail)
        if locked_until:
            raise AccountLocked(locked_until, now)
        raise InvalidCredentials(MAX_ATTEMPTS - attempts)

    current = CurrentUser(user.id, user.identifiant, user.nom_complet, user.role)
    with transaction(conn):
        utilisateurs.reset_failures(conn, user.id)
        if needs_rehash(user.mot_de_passe_hash):
            utilisateurs.update_hash(conn, user.id, hash_password(password))
        audit.log(conn, current, Action.CONNEXION)
    session.login(current)
    return current


def logout(conn: sqlite3.Connection, session: Session) -> None:
    if session.is_authenticated:
        with transaction(conn):
            audit.log(conn, session.user, Action.DECONNEXION)
    session.logout()