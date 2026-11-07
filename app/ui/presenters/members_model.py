"""Modèle de vue de la page Membres : filtre, tri, pagination et textes prêts à afficher.
Python pur (aucun widget) : testable sans interface.

Dette = max(dû − reçu, 0) ; avance = max(reçu − dû, 0). Un montant nul s'affiche « — ».
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from math import ceil

from app.ui.format import format_date
from app.ui.ports_members import MemberInfo, MembersData, MemberStatus
from app.ui.widgets.badge import Kind

PAGE_SIZE = 10
_NBSP = "\u00a0"
_STATUT_TEXTE = {MemberStatus.ACTIF: ("Actif", Kind.INFO), MemberStatus.DECEDE: ("Décédé", Kind.NEUTRAL)}


@dataclass(frozen=True)
class MembersQuery:
    text: str = ""
    status: str = "tous"          # 'tous' | 'actif' | 'decede'
    sex: str = "tous"             # 'tous' | 'M' | 'F'
    sort_key: str = "carnet"      # carnet, name, sex, joined, status, du, recu, dette, avance
    ascending: bool = True
    page: int = 1


@dataclass(frozen=True)
class MemberRow:
    id: int
    carnet: str
    name: str
    sex: str
    joined: str
    status: str
    status_kind: str
    du: str
    recu: str
    dette: str
    avance: str
    deceased: bool
    has_debt: bool
    has_advance: bool


@dataclass(frozen=True)
class MembersViewModel:
    subtitle: str
    rows: tuple[MemberRow, ...]
    counter: str
    page: int
    pages: int
    page_numbers: tuple[int, ...]
    has_prev: bool
    has_next: bool
    sort_key: str
    ascending: bool
    empty: bool


def _plural(nombre: int, singulier: str, pluriel: str) -> str:
    return f"{nombre} {singulier if nombre == 1 else pluriel}"


def _norm(texte: str) -> str:
    """Minuscules sans accents, pour une recherche tolérante."""
    decompose = unicodedata.normalize("NFD", texte.casefold())
    return "".join(c for c in decompose if not unicodedata.combining(c))


def _nombre(valeur: int) -> str:
    return f"{valeur:,}".replace(",", _NBSP)


def _montant(valeur: int) -> str:
    return _nombre(valeur) if valeur else "—"


def dette(m: MemberInfo) -> int:
    return max(m.du - m.recu, 0)


def avance(m: MemberInfo) -> int:
    return max(m.recu - m.du, 0)


def _cle_tri(m: MemberInfo, cle: str):
    return {
        "carnet": m.carnet, "name": _norm(m.name), "sex": m.sex, "joined": m.joined_on,
        "status": m.status, "du": m.du, "recu": m.recu, "dette": dette(m), "avance": avance(m),
    }[cle]


def _filtrer(membres: tuple[MemberInfo, ...], q: MembersQuery) -> list[MemberInfo]:
    texte = _norm(q.text.strip())
    resultat = []
    for m in membres:
        if q.status != "tous" and m.status != q.status:
            continue
        if q.sex != "tous" and m.sex != q.sex:
            continue
        if texte and texte not in _norm(m.name) and texte not in m.carnet.casefold():
            continue
        resultat.append(m)
    return resultat


def _numeros_pages(page: int, pages: int) -> tuple[int, ...]:
    if pages <= 5:
        return tuple(range(1, pages + 1))
    debut = min(max(page - 2, 1), pages - 4)
    return tuple(range(debut, debut + 5))


def _ligne(m: MemberInfo) -> MemberRow:
    texte, genre = _STATUT_TEXTE.get(m.status, (m.status, Kind.NEUTRAL))
    d, a = dette(m), avance(m)
    return MemberRow(m.id, m.carnet, m.name, m.sex, format_date(m.joined_on), texte, genre,
                     _nombre(m.du), _nombre(m.recu), _montant(d), _montant(a),
                     m.status == MemberStatus.DECEDE, d > 0, a > 0)


def build_view_model(data: MembersData, q: MembersQuery) -> MembersViewModel:
    tous = data.members
    actifs = sum(1 for m in tous if m.status == MemberStatus.ACTIF)
    decedes = sum(1 for m in tous if m.status == MemberStatus.DECEDE)
    subtitle = (f"{_plural(len(tous), 'membre', 'membres')} · {_plural(actifs, 'actif', 'actifs')} · "
                f"{_plural(decedes, 'décédé', 'décédés')} · cotisations en FCFA")

    filtres = _filtrer(tous, q)
    filtres.sort(key=lambda m: m.carnet)                       # ordre stable pour les égalités
    filtres.sort(key=lambda m: _cle_tri(m, q.sort_key), reverse=not q.ascending)

    total = len(filtres)
    pages = max(1, ceil(total / PAGE_SIZE))
    page = min(max(q.page, 1), pages)
    debut = (page - 1) * PAGE_SIZE
    affiches = filtres[debut:debut + PAGE_SIZE]
    if total:
        counter = f"Affichage {debut + 1}–{debut + len(affiches)} sur {_plural(total, 'membre', 'membres')}"
    else:
        counter = "Aucun membre à afficher"
    return MembersViewModel(
        subtitle=subtitle, rows=tuple(_ligne(m) for m in affiches), counter=counter,
        page=page, pages=pages, page_numbers=_numeros_pages(page, pages),
        has_prev=page > 1, has_next=page < pages,
        sort_key=q.sort_key, ascending=q.ascending, empty=total == 0,
    )
