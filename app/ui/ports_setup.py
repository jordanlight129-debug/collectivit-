"""Contrat pour le premier démarrage."""
from __future__ import annotations

from typing import Protocol


class SetupPort(Protocol):
    """Port pour la création du premier administrateur."""

    def create_admin(self, identifiant: str, mot_de_passe: str, nom_complet: str) -> int: ...
