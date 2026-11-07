"""Modèle de vue pour les cotisations parallèles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple


@dataclass(frozen=True)
class ParallelRow:
    id: int
    name: str
    period: str
    men: str
    women: str
    total_expected: str
    total_collected: str
    remaining: str
    is_complete: bool
    status: str


@dataclass(frozen=True)
class ParallelDetailRow:
    member_id: int
    carnet: str
    name: str
    sex: str
    expected: str
    collected: str
    debt: str
    status: str


@dataclass(frozen=True)
class ParallelViewModel:
    subtitle: str
    rows: tuple[ParallelRow, ...]
    total_expected: str
    total_collected: str
    total_debt: str
    selected_subscription_id: int | None
    selected_name: str
    selected_period: str
    detail_rows: tuple[ParallelDetailRow, ...]
    detail_counter: str
    empty: bool = False
    counter: str = ""


class ParallelQuery(NamedTuple):
    search: str = ""
    sort_key: str = "name"
    ascending: bool = True
    page: int = 1
    selected_subscription_id: int | None = None


def _format_amount(amount: int) -> str:
    return f"{amount:,}".replace(",", " ")


def build_row(sub) -> ParallelRow:
    remaining = sub.total_expected - sub.total_collected
    return ParallelRow(
        id=sub.id,
        name=sub.name,
        period=f"{sub.start_date} → {sub.end_date}",
        men=_format_amount(sub.amount_man),
        women=_format_amount(sub.amount_woman),
        total_expected=_format_amount(sub.total_expected),
        total_collected=_format_amount(sub.total_collected),
        remaining=_format_amount(remaining),
        is_complete=remaining <= 0,
        status="Soldée" if remaining <= 0 else "En cours",
    )


def build_view_model(data, query: ParallelQuery) -> ParallelViewModel:
    filtered = data.subscriptions
    if query.search:
        search_lower = query.search.lower()
        filtered = tuple(s for s in filtered if search_lower in s.name.lower())

    if query.sort_key == "name":
        filtered = sorted(filtered, key=lambda s: s.name, reverse=not query.ascending)
    elif query.sort_key == "date":
        filtered = sorted(filtered, key=lambda s: s.start_date, reverse=not query.ascending)

    page_size = 20
    offset = (query.page - 1) * page_size
    page_subs = filtered[offset:offset + page_size]
    total = len(filtered)
    page_count = (total + page_size - 1) // page_size if total else 1

    rows = tuple(build_row(s) for s in page_subs)
    selected = next((subscription for subscription in page_subs
                     if subscription.id == query.selected_subscription_id), None)
    if selected is None and page_subs:
        selected = page_subs[0]
    detail_rows = tuple(ParallelDetailRow(
        member_id=member.id,
        carnet=member.carnet,
        name=member.name,
        sex=member.sex,
        expected=_format_amount(member.expected),
        collected=_format_amount(member.collected),
        debt=_format_amount(member.debt) if member.debt else "—",
        status={"paye": "Payé", "partiel": "Partiel", "impaye": "Dette"}.get(
            member.status, member.status),
    ) for member in selected.members) if selected else ()

    return ParallelViewModel(
        subtitle=(f"{total} cotisations sur l’exercice {data.exercise_label} · "
                  "montants attendus selon le sexe du membre"),
        rows=rows,
        total_expected=_format_amount(sum(sub.total_expected for sub in data.subscriptions)),
        total_collected=_format_amount(sum(sub.total_collected for sub in data.subscriptions)),
        total_debt=_format_amount(sum(max(sub.total_expected - sub.total_collected, 0)
                          for sub in data.subscriptions)),
        selected_subscription_id=selected.id if selected else None,
        selected_name=selected.name if selected else "",
        selected_period=f"{selected.start_date} → {selected.end_date}" if selected else "",
        detail_rows=detail_rows,
        detail_counter=(f"{len(detail_rows)} membres concernés · les membres décédés sont exclus du total attendu"
                        if selected else "Aucune cotisation sélectionnée"),
        empty=len(rows) == 0,
        counter=f"Page {query.page}/{page_count} · {total} résultat{'s' if total != 1 else ''}",
    )
