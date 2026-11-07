"""Modèle de vue pour les amendes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple


@dataclass(frozen=True)
class FineRow:
    id: int
    member_carnet: str
    member_name: str
    label: str
    date: str
    amount_expected: str
    amount_collected: str
    remaining: str
    is_paid: bool
    status: str
    status_kind: str


@dataclass(frozen=True)
class FinesViewModel:
    subtitle: str
    rows: tuple[FineRow, ...]
    total_expected: str
    total_collected: str
    total_remaining: str
    is_open: bool
    empty: bool = False
    counter: str = ""


class FinesQuery(NamedTuple):
    search: str = ""
    sort_key: str = "date"
    ascending: bool = False
    page: int = 1
    status: str = "tous"


def _format_amount(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def build_row(record) -> FineRow:
    if record.remaining <= 0:
        status, status_kind = "Payée", "success"
    elif record.amount_collected > 0:
        status, status_kind = "Partielle", "warning"
    else:
        status, status_kind = "Impayée", "danger"
    return FineRow(
        id=record.id,
        member_carnet=record.member_carnet,
        member_name=record.member_name,
        label=record.label,
        date=record.date,
        amount_expected=_format_amount(record.amount_expected),
        amount_collected=_format_amount(record.amount_collected),
        remaining=_format_amount(record.remaining),
        is_paid=record.remaining <= 0,
        status=status,
        status_kind=status_kind,
    )


def build_view_model(data, query: FinesQuery) -> FinesViewModel:
    filtered = data.records
    if query.search:
        search_lower = query.search.lower()
        filtered = tuple(r for r in filtered if search_lower in r.member_name.lower()
                         or search_lower in r.member_carnet.lower()
                         or search_lower in r.label.lower())

    if query.status != "tous":
        filtered = tuple(r for r in filtered if (
            "payee" if r.remaining <= 0 else "partielle" if r.amount_collected > 0 else "impayee"
        ) == query.status)

    if query.sort_key == "date":
        filtered = sorted(filtered, key=lambda r: datetime.strptime(r.date, "%d/%m/%Y"),
                          reverse=not query.ascending)
    elif query.sort_key == "name":
        filtered = sorted(filtered, key=lambda r: r.member_name, reverse=not query.ascending)

    page_size = 8
    offset = (query.page - 1) * page_size
    page_records = filtered[offset:offset + page_size]
    total = len(filtered)
    page_count = (total + page_size - 1) // page_size if total else 1

    rows = tuple(build_row(r) for r in page_records)
    shown = len(rows)
    counter = (f"{shown} dernière amende sur {total}" if shown == 1
               else f"{shown} dernières amendes sur {total}")

    return FinesViewModel(
        subtitle=(f"Amendes de l’exercice {data.exercise_label} · montant attendu, collecté et manque à gagner"),
        rows=rows,
        total_expected=_format_amount(data.total_expected or sum(r.amount_expected for r in data.records)),
        total_collected=_format_amount(data.total_collected or sum(r.amount_collected for r in data.records)),
        total_remaining=_format_amount(sum(r.remaining for r in data.records)),
        is_open=data.is_open,
        empty=len(rows) == 0,
        counter=counter,
    )
