"""Utilisateur connecté et permissions par rôle.

Les services appellent session.require(Permission.X) avant toute opération
sensible : l'interface masque les boutons, mais c'est ici que l'on refuse.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    ADMINISTRATEUR = "administrateur"
    SECRETAIRE = "secretaire"

    @property
    def label(self) -> str:
        return "Administrateur" if self is Role.ADMINISTRATEUR else "Secrétaire"


class Permission(str, Enum):
    # Création (administrateur et secrétaires)
    MEMBER_CREATE = "member_create"
    PAYMENT_CREATE = "payment_create"
    EXPENSE_CREATE = "expense_create"
    FINE_CREATE = "fine_create"
    DEATH_CREATE = "death_create"
    PARALLEL_DEFINE = "parallel_define"
    EXPORT = "export"
    # Administrateur uniquement
    MEMBER_EDIT = "member_edit"
    DELETE = "delete"
    USERS_MANAGE = "users_manage"
    AUDIT_VIEW = "audit_view"
    BALANCE_VIEW = "balance_view"
    EXERCISE_CLOSE = "exercise_close"
    BACKUP_MANAGE = "backup_manage"
    SETTINGS_MANAGE = "settings_manage"
    PAYMENT_EDIT = "payment_edit"

_SECRETARY_PERMISSIONS = frozenset({
    Permission.MEMBER_CREATE,
    Permission.PAYMENT_CREATE,
    Permission.EXPENSE_CREATE,
    Permission.FINE_CREATE,
    Permission.DEATH_CREATE,
    Permission.PARALLEL_DEFINE,
    Permission.EXPORT,
})

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMINISTRATEUR: frozenset(Permission),
    Role.SECRETAIRE: _SECRETARY_PERMISSIONS,
}


class PermissionDenied(Exception):
    """L'utilisateur connecté n'a pas le droit d'effectuer cette action."""


class NotAuthenticated(Exception):
    """Aucun utilisateur n'est connecté."""


@dataclass(frozen=True)
class CurrentUser:
    id: int
    identifiant: str
    nom_complet: str
    role: Role


class Session:
    """Session unique de l'application de bureau."""

    def __init__(self) -> None:
        self._user: CurrentUser | None = None

    # -- état -----------------------------------------------------------
    @property
    def is_authenticated(self) -> bool:
        return self._user is not None

    @property
    def user(self) -> CurrentUser:
        if self._user is None:
            raise NotAuthenticated("Aucun utilisateur connecté.")
        return self._user

    @property
    def is_admin(self) -> bool:
        return self._user is not None and self._user.role is Role.ADMINISTRATEUR

    # -- connexion ------------------------------------------------------
    def login(self, user: CurrentUser) -> None:
        self._user = user

    def logout(self) -> None:
        self._user = None

    # -- droits ---------------------------------------------------------
    def can(self, permission: Permission) -> bool:
        if self._user is None:
            return False
        return permission in ROLE_PERMISSIONS[self._user.role]

    def require(self, permission: Permission) -> None:
        if self._user is None:
            raise NotAuthenticated("Aucun utilisateur connecté.")
        if not self.can(permission):
            raise PermissionDenied("Vous n'avez pas le droit d'effectuer cette action.")


# Instance partagée par toute l'application
session = Session()