"""Qui est concerné par quelle cotisation (règles d'applicabilité).

Fonctions pures, sans base de données : un membre cotise à partir de son
MOIS d'adhésion à la cotisation mensuelle, funéraire et parallèle.
"""
from __future__ import annotations

from datetime import date

Month = tuple[int, int]          # (année, mois)

_MOIS_ABREGES = ("Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
                 "Juil", "Août", "Sep", "Oct", "Nov", "Déc")


def month_of(d: date) -> Month:
    return d.year, d.month


def month_label(month: Month) -> str:
    """Libellé court d'un mois de l'exercice, par exemple « Sep 2026 »."""
    annee, mois = month
    return f"{_MOIS_ABREGES[mois - 1]} {annee}"


def applicable_months(adhesion: date, deces: date | None, months: list[Month]) -> list[Month]:
    """Cotisation mensuelle : du mois d'adhésion au mois du décès (inclus).

    `months` est la liste des 12 mois de l'exercice ; les mois non retournés
    s'affichent « non applicable » (case grise, hors total dû).
    """
    start = month_of(adhesion)
    end = month_of(deces) if deces else None
    return [m for m in months if m >= start and (end is None or m <= end)]


def concerned_by_death(adhesion: date, membre_deces: date | None, death_date: date, *,
                       is_defunct: bool = False, exempt: bool = False) -> bool:
    """Cotisation funéraire : le membre est concerné par ce décès si

    - il a adhéré au plus tard dans le mois du décès,
    - il n'était pas déjà décédé,
    - il n'est pas le défunt lui-même,
    - il n'est pas exempté (membre endeuillé, option décès par décès).
    """
    if is_defunct or exempt:
        return False
    if month_of(adhesion) > month_of(death_date):
        return False
    if membre_deces is not None and death_date > membre_deces:
        return False
    return True


def concerned_by_parallel(adhesion: date, membre_deces: date | None,
                          periode_debut: date, periode_fin: date) -> bool:
    """Cotisation parallèle : le membre est concerné s'il a adhéré au plus tard
    dans le mois de fin de la période et n'était pas décédé avant son début.
    Le montant est dû en entier (pas de proratisation)."""
    if month_of(adhesion) > month_of(periode_fin):
        return False
    if membre_deces is not None and membre_deces < periode_debut:
        return False
    return True