"""Modèle de vue pour les dépenses."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import NamedTuple


@dataclass(frozen=True)
class ExpenseRow:
    id: int
    date: str
    label: str
    beneficiary: str
    amount_planned: str
    amount_spent: str
    is_over_budget: bool


@dataclass(frozen=True)
class ExpensesViewModel:
    subtitle: str
    total_planned: str
    total_spent: str
    rows: tuple[ExpenseRow, ...]
    read_only: bool
    page: int
    page_count: int
    sort_key: str
    ascending: bool
    empty: bool = False
    counter: str = ""


class ExpensesQuery(NamedTuple):
    search: str = ""
    sort_key: str = "date"
    ascending: bool = False
    page: int = 1


def _format_amount(amount: int | Decimal) -> str:
    return f"{amount:,.0f}".replace(",", " ")


def build_row(record) -> ExpenseRow:
    return ExpenseRow(
        id=record.id,
        date=date.fromisoformat(record.date).strftime("%d/%m/%Y"),
        label=record.label,
        beneficiary=record.beneficiary or "—",
        amount_planned=_format_amount(record.amount_planned),
        amount_spent=_format_amount(record.amount_spent),
        is_over_budget=record.amount_spent > record.amount_planned,
    )


def build_view_model(data, query: ExpensesQuery) -> ExpensesViewModel:
    filtered = data.records
    if query.search:
        search_lower = query.search.lower()
        filtered = tuple(r for r in filtered if search_lower in r.label.lower())

    sort_keys = {
        "date": lambda record: record.date,
        "label": lambda record: record.label.lower(),
        "beneficiary": lambda record: (record.beneficiary or "").lower(),
        "planned": lambda record: record.amount_planned,
        "spent": lambda record: record.amount_spent,
    }
    sort_key = sort_keys.get(query.sort_key)
    if sort_key is not None:
        filtered = sorted(filtered, key=sort_key, reverse=not query.ascending)

    page_size = 20
    total = len(filtered)
    page_count = (total + page_size - 1) // page_size if total else 1
    page = min(max(query.page, 1), page_count)
    offset = (page - 1) * page_size
    page_records = filtered[offset:offset + page_size]

    rows = tuple(build_row(r) for r in page_records)

    return ExpensesViewModel(
        subtitle=f"Exercice {data.exercise_label} · {total} dépense{'s' if total != 1 else ''}",
        total_planned=_format_amount(data.total_planned),
        total_spent=_format_amount(data.total_spent),
        rows=rows,
        read_only=not data.is_open,
        page=page,
        page_count=page_count,
        sort_key=query.sort_key,
        ascending=query.ascending,
        empty=len(rows) == 0,
        counter=f"Page {page}/{page_count} · {total} résultat{'s' if total != 1 else ''}",
    )
