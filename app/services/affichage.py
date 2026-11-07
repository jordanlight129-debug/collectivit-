"""Affichage d'un écart entre perçu et dû : jamais de chiffre négatif.

- perçu > dû  → « Excédent », en vert
- perçu < dû  → « Dette », en rouge
- perçu = dû  → « Soldé », en neutre
Le montant est toujours positif : c'est le mot et la couleur qui portent le sens.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

EXCEDENT = "excedent"
DETTE = "dette"
SOLDE = "solde"

_COULEURS = {EXCEDENT: "vert", DETTE: "rouge", SOLDE: "neutre"}
_LIBELLES = {EXCEDENT: "Excédent", DETTE: "Dette", SOLDE: "Soldé"}


@dataclass(frozen=True)
class Situation:
    kind: str           # EXCEDENT | DETTE | SOLDE
    montant: int | Decimal        # toujours >= 0

    @property
    def couleur(self) -> str:
        """'vert', 'rouge' ou 'neutre' (jetons de couleur de la maquette)."""
        return _COULEURS[self.kind]

    @property
    def libelle(self) -> str:
        return _LIBELLES[self.kind]

    def texte(self) -> str:
        """Ex. « Dette : 378 000 FCFA »."""
        return f"{self.libelle} : {self.montant:,.0f}".replace(",", "\u00A0") + " FCFA"


def depuis_ecart(ecart: int | Decimal) -> Situation:
    """ecart = perçu − dû (positif : excédent, négatif : dette)."""
    if ecart > 0:
        return Situation(EXCEDENT, ecart)
    if ecart < 0:
        return Situation(DETTE, -ecart)
    return Situation(SOLDE, 0)


def situation(du: int | Decimal, percu: int | Decimal) -> Situation:
    return depuis_ecart(percu - du)