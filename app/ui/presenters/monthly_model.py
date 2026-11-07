"""Modèle de vue pour les cotisations mensuelles : transformation des données brutes en structure d'affichage."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

PAGE_SIZE = 20


@dataclass(frozen=True)
class MonthlyCellInfo:
    symbol: str           # texte affiché dans la case : montant, « — » (impayé) ou « n.a. »
    status: str           # paye, partiel, impaye, non_applicable
    amount: str           # montant versé ou dû, formaté (« — » si non applicable)


@dataclass(frozen=True)
class MonthlyMemberRow:
    carnet: str
    name: str
    sex: str
    joined: str
    cells: tuple[MonthlyCellInfo, ...]
    total_due: str
    total_paid: str
    total_debt: str
    advance: str
    has_debt: bool
    has_advance: bool
    inactive: bool = False


@dataclass(frozen=True)
class MonthlyViewModel:
    subtitle: str
    tariff_man: str
    tariff_woman: str
    rows: tuple[MonthlyMemberRow, ...]
    empty: bool = False
    counter: str = ""
    totals: tuple[str, str, str, str] | None = None   # DÛ, PERÇU, DETTE, AVANCE de la page
    page: int = 1
    page_count: int = 1


class MonthlyQuery(NamedTuple):
    search: str = ""
    sex: str = "all"
    sort_key: str = "carnet"
    ascending: bool = True
    page: int = 1
    status: str = "all"   # all, a_jour, partiel, dette, avance


def _format_amount(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def _format_or_dash(amount: int) -> str:
    return _format_amount(amount) if amount else "—"


def _cell_info(cell) -> MonthlyCellInfo:
    """Convertit une cellule du service en info d'affichage (rendu de la maquette)."""
    if cell.status == "paye":
        return MonthlyCellInfo(_format_amount(cell.paid), "paye", _format_amount(cell.paid))
    if cell.status == "partiel":
        return MonthlyCellInfo(_format_amount(cell.paid), "partiel", _format_amount(cell.paid))
    if cell.status == "impaye":
        return MonthlyCellInfo("—", "impaye", _format_amount(cell.due))
    # le service renvoie « na » pour un mois non applicable
    return MonthlyCellInfo("n.a.", "non_applicable", "—")


def build_member_row(member, tariffs: dict[str, int]) -> MonthlyMemberRow:
    cells = tuple(_cell_info(cell) for cell in member.cells)
    return MonthlyMemberRow(
        carnet=member.carnet,
        name=member.name,
        sex=member.sex,
        joined=member.joined,
        cells=cells,
        total_due=_format_amount(member.total_due),
        total_paid=_format_amount(member.total_paid),
        total_debt=_format_or_dash(member.total_debt),
        advance=_format_or_dash(member.advance),
        has_debt=member.total_debt > 0,
        has_advance=member.advance > 0,
        inactive=bool(getattr(member, "inactive", False)),
    )


def _matches_status(member, status: str) -> bool:
    if status == "dette":
        return member.total_debt > 0
    if status == "avance":
        return member.advance > 0
    if status == "partiel":
        return any(cell.status == "partiel" for cell in member.cells)
    if status == "a_jour":
        return member.total_debt == 0
    return True


_TRIS = {
    "carnet": lambda m: m.carnet,
    "name": lambda m: m.name.lower(),
    "dû": lambda m: m.total_due,
    "perçu": lambda m: m.total_paid,
    "dette": lambda m: m.total_debt,
    "debt": lambda m: m.total_debt,
    "avance": lambda m: m.advance,
}


def build_view_model(data, query: MonthlyQuery) -> MonthlyViewModel:
    filtered = tuple(data.members)
    if query.search:
        search_lower = query.search.lower()
        filtered = tuple(m for m in filtered if search_lower in m.name.lower() or search_lower in m.carnet.lower())
    if query.sex != "all":
        filtered = tuple(m for m in filtered if m.sex == query.sex)
    if query.status != "all":
        filtered = tuple(m for m in filtered if _matches_status(m, query.status))

    cle_tri = _TRIS.get(query.sort_key)
    if cle_tri is not None:
        filtered = tuple(sorted(filtered, key=cle_tri, reverse=not query.ascending))

    total = len(filtered)
    page_count = (total + PAGE_SIZE - 1) // PAGE_SIZE if total else 1
    page = min(max(query.page, 1), page_count)
    offset = (page - 1) * PAGE_SIZE
    page_members = filtered[offset:offset + PAGE_SIZE]

    tariffs = {"M": data.tariff_man, "F": data.tariff_woman}
    rows = tuple(build_member_row(m, tariffs) for m in page_members)

    totals = None
    if page_members:
        totals = (
            _format_amount(sum(m.total_due for m in page_members)),
            _format_amount(sum(m.total_paid for m in page_members)),
            _format_or_dash(sum(m.total_debt for m in page_members)),
            _format_or_dash(sum(m.advance for m in page_members)),
        )

    return MonthlyViewModel(
        subtitle=(f"Suivi des 12 mois de l'exercice {data.exercise_label} · "
                  "montants dus selon le sexe (configurables dans Paramètres)"),
        tariff_man=_format_amount(data.tariff_man),
        tariff_woman=_format_amount(data.tariff_woman),
        rows=rows,
        empty=len(rows) == 0,
        counter=f"Page {page}/{page_count} · {total} résultat{'s' if total != 1 else ''}",
        totals=totals,
        page=page,
        page_count=page_count,
    )