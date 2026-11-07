"""Modèle de vue pour le bilan financier."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BalanceViewModel:
    subtitle: str
    period_start: str
    period_end: str
    total_revenue: str
    total_expenses: str
    balance: str
    carried_forward: str
    closing_balance: str
    is_positive: bool


def _format_amount(amount: int | Decimal) -> str:
    return f"{amount:,.0f}".replace(",", " ")


def build_view_model(data) -> BalanceViewModel:
    return BalanceViewModel(
        subtitle=f"Exercice {data.exercise_label}",
        period_start=data.period_start,
        period_end=data.period_end,
        total_revenue=_format_amount(data.total_revenue),
        total_expenses=_format_amount(data.total_expenses),
        balance=_format_amount(data.balance),
        carried_forward=_format_amount(data.carried_forward),
        closing_balance=_format_amount(data.closing_balance),
        is_positive=data.closing_balance >= 0,
    )
