"""Modèle de vue matriciel pour les cotisations funéraires."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from app.models.deces import TYPE_LABELS


@dataclass(frozen=True)
class FuneralDeathColumn:
    id: int
    title: str
    detail: str
    tariff: str


@dataclass(frozen=True)
class FuneralCellView:
    text: str
    status: str


@dataclass(frozen=True)
class FuneralRow:
    id: int
    carnet: str
    name: str
    cells: tuple[FuneralCellView, ...]
    due: str
    paid: str
    debt: str


@dataclass(frozen=True)
class FuneralViewModel:
    subtitle: str
    columns: tuple[FuneralDeathColumn, ...]
    rows: tuple[FuneralRow, ...]
    total_members: int
    total_due: str
    total_paid: str
    total_debt: str
    page_due: str
    page_paid: str
    page_debt: str
    total_row_label: str
    empty: bool = False
    counter: str = ""
    page: int = 1
    page_count: int = 1
    has_previous: bool = False
    has_next: bool = False


class FuneralQuery(NamedTuple):
    search: str = ""
    sort_key: str = "carnet"
    ascending: bool = True
    page: int = 1


def _format_amount(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def _cell_view(cell) -> FuneralCellView:
    if cell.reason == "defunt":
        return FuneralCellView("Défunt", cell.reason)
    if cell.reason == "exempte":
        return FuneralCellView("Exemptée", cell.reason)
    if cell.reason == "non_concerne":
        return FuneralCellView("n.c.", cell.reason)
    if cell.paid:
        return FuneralCellView(_format_amount(cell.paid), cell.status)
    return FuneralCellView("—", cell.status)


def build_view_model(data, query: FuneralQuery) -> FuneralViewModel:
    filtered = data.members
    if query.search:
        search_lower = query.search.lower()
        filtered = tuple(member for member in filtered
                         if search_lower in member.name.lower() or search_lower in member.carnet.lower())

    sort_key = {
        "carnet": lambda member: member.carnet,
        "name": lambda member: member.name.casefold(),
        "due": lambda member: member.due,
        "paid": lambda member: member.paid,
        "debt": lambda member: member.debt,
    }.get(query.sort_key, lambda member: member.carnet)
    filtered = sorted(filtered, key=sort_key, reverse=not query.ascending)

    page_size = 10
    offset = (query.page - 1) * page_size
    page_members = filtered[offset:offset + page_size]
    total = len(filtered)
    page_count = (total + page_size - 1) // page_size if total else 1

    rows = tuple(FuneralRow(
        id=member.id,
        carnet=member.carnet,
        name=member.name,
        cells=tuple(_cell_view(cell) for cell in member.cells),
        due=_format_amount(member.due),
        paid=_format_amount(member.paid),
        debt=_format_amount(member.debt),
    ) for member in page_members)
    columns = tuple(FuneralDeathColumn(
        id=record.id,
        title=record.deceased_name,
        detail=f"{TYPE_LABELS.get(record.death_type, record.death_type)} · {record.death_date}",
        tariff=(f"H {_format_amount(record.amount_man)} · F {_format_amount(record.amount_woman)} / membre"),
    ) for record in data.records)
    end = min(offset + len(rows), total)
    start = offset + 1 if rows else 0

    return FuneralViewModel(
        subtitle=(f"{len(columns)} collectes sur l’exercice {data.exercise_label} · une colonne par décès · "
                  f"{_format_amount(data.total_paid)} FCFA perçus"),
        columns=columns,
        rows=rows,
        total_members=data.total_members,
        total_due=_format_amount(data.total_due),
        total_paid=_format_amount(data.total_paid),
        total_debt=_format_amount(data.total_debt or sum(member.debt for member in data.members)),
        page_due=_format_amount(sum(member.due for member in page_members)),
        page_paid=_format_amount(sum(member.paid for member in page_members)),
        page_debt=_format_amount(sum(member.debt for member in page_members)),
        total_row_label=(f"TOTAL · {len(rows)} membre{'s' if len(rows) != 1 else ''} affiché"
                 f"{'s' if len(rows) != 1 else ''} sur {data.total_members or total}"),
        empty=len(rows) == 0,
        counter=f"Affichage {start}–{end} sur {data.total_members or total} membres",
        page=query.page,
        page_count=page_count,
        has_previous=query.page > 1,
        has_next=query.page < page_count,
    )
