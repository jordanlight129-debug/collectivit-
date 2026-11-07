"""Modèle de vue pour les reliquats."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple


@dataclass(frozen=True)
class LeftoverRow:
    id: int
    name: str
    expense_label: str
    amount: str
    date: str


@dataclass(frozen=True)
class LeftoversViewModel:
    subtitle: str
    total: str
    rows: tuple[LeftoverRow, ...]
    empty: bool = False
    counter: str = ""


class LeftoversQuery(NamedTuple):
    search: str = ""
    sort_key: str = "date"
    ascending: bool = False
    page: int = 1


def _format_amount(amount: int | Decimal) -> str:
    return f"{amount:,.0f}".replace(",", " ")


def build_row(record) -> LeftoverRow:
    return LeftoverRow(
        id=record.id,
        name=record.name,
        expense_label=record.expense_label,
        amount=_format_amount(record.amount),
        date=record.date,
    )


def build_view_model(data, query: LeftoversQuery) -> LeftoversViewModel:
    filtered = data.records
    if query.search:
        search_lower = query.search.lower()
        filtered = tuple(r for r in filtered if search_lower in r.name.lower() or search_lower in r.expense_label.lower())

    if query.sort_key == "date":
        filtered = sorted(filtered, key=lambda r: r.date, reverse=not query.ascending)
    elif query.sort_key == "name":
        filtered = sorted(filtered, key=lambda r: r.name, reverse=not query.ascending)

    page_size = 20
    offset = (query.page - 1) * page_size
    page_records = filtered[offset:offset + page_size]
    total = len(filtered)
    page_count = (total + page_size - 1) // page_size if total else 1

    rows = tuple(build_row(r) for r in page_records)

    return LeftoversViewModel(
        subtitle=f"Exercice {data.exercise_label} · {total} reliquat{'s' if total != 1 else ''}",
        total=_format_amount(data.total),
        rows=rows,
        empty=len(rows) == 0,
        counter=f"Page {query.page}/{page_count} · {total} résultat{'s' if total != 1 else ''}",
    )
