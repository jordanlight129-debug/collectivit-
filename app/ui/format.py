"""Formats d'affichage (montants en FCFA, dates)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal


def format_fcfa(montant: int | Decimal, *, unite: bool = True) -> str:
    """1250000 → « 1 250 000 FCFA » (espaces insécables). Jamais de montant négatif :
    pour un solde, utilisez affichage.depuis_ecart(...) et SituationLabel."""
    if montant < 0:
        raise ValueError("Un montant ne s'affiche jamais en négatif : utilisez une situation (excédent ou dette).")
    texte = f"{montant:,.0f}".replace(",", "\u00A0")
    return f"{texte} FCFA" if unite else texte


def format_date(valeur: date) -> str:
    return valeur.strftime("%d/%m/%Y")