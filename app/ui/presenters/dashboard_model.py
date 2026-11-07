"""Modèle de vue du tableau de bord : transforme les chiffres bruts en textes prêts à afficher.
Python pur (aucun widget) : testable sans interface.

Règle d'affichage : jamais de montant négatif dans les cartes ; un écart est un mot et une couleur
(excédent vert, dette rouge, soldé neutre) fournis par app.services.affichage.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services import affichage
from app.ui.format import format_date, format_fcfa
from app.ui.ports import DashboardData
from app.ui.theme.tokens import Color
from app.ui.widgets.badge import Kind

_NBSP = "\u00a0"
_STATUTS = {
    "paye": ("Payé", Kind.SUCCESS),
    "enregistree": ("Enregistrée", Kind.NEUTRAL),
    "partiel": ("Partiel", Kind.WARNING),
    "attente": ("En attente", Kind.WARNING),
    "reliquat": ("Reliquat", Kind.INFO),
}


@dataclass(frozen=True)
class StatView:
    label: str
    amount: str
    note: str
    tone: str                      # 'neutre' | 'vert' | 'rouge'


@dataclass(frozen=True)
class AlertView:
    kind: str
    text: str


@dataclass(frozen=True)
class MonthView:
    label: str
    entrees: int
    depenses: int


@dataclass(frozen=True)
class ShareView:
    label: str
    text: str                      # « 4 860 000 · 68,6 % »
    ratio: float                   # 0 à 1
    color: str


@dataclass(frozen=True)
class OperationView:
    date: str
    label: str
    rubrique: str
    amount: str                    # « +10 000 », « −105 000 »
    tone: str                      # 'vert' | 'neutre' | 'gris'
    status: str
    status_kind: str


@dataclass(frozen=True)
class DebtorView:
    member: str
    carnet: str
    amount: str


@dataclass(frozen=True)
class DashboardViewModel:
    subtitle: str
    read_only: bool
    alerts: tuple[AlertView, ...]      # non affichées sur le tableau de bord (menu de la cloche)
    stats: tuple[StatView, ...]
    months: tuple[MonthView, ...]
    shares: tuple[ShareView, ...]
    operations: tuple[OperationView, ...]
    debtors: tuple[DebtorView, ...]
    debtors_counter: str               # « 5 sur 21 »


def _plural(nombre: int, singulier: str, pluriel: str) -> str:
    return f"{nombre} {singulier if nombre == 1 else pluriel}"


def _nombre(valeur: int) -> str:
    """Nombre groupé par milliers, sans unité : 4 860 000."""
    return f"{abs(valeur):,}".replace(",", _NBSP)


def _pourcent(ratio: float) -> str:
    return f"{ratio * 100:.1f}".replace(".", ",") + f"{_NBSP}%"


def _percu(data: DashboardData, mot: str) -> int:
    """Total perçu des rubriques dont le libellé contient `mot` (insensible à la casse).

    Si vos libellés diffèrent (ex. « Mensuelles »), ajustez les mots utilisés plus bas.
    """
    return sum(r.percu for r in data.rubriques if mot in r.label.lower())


def _operation(o) -> OperationView:
    signe = "+" if o.amount > 0 else "−"
    if o.amount < 0:
        ton = "neutre"
    elif o.status == "attente":
        ton = "gris"
    else:
        ton = "vert"
    texte, genre = _STATUTS.get(o.status, (o.status, Kind.NEUTRAL))
    return OperationView(format_date(o.on), o.label, o.rubrique, f"{signe}{_nombre(o.amount)}",
                         ton, texte, genre)


def build_view_model(data: DashboardData) -> DashboardViewModel:
    entrees = sum(r.percu for r in data.rubriques)
    solde = affichage.depuis_ecart(entrees - data.expenses)
    if data.debts_total > 0:
        note_dettes = "Non encaissé · " + _plural(data.debtor_members, "membre", "membres")
    else:
        note_dettes = "Aucune dette en cours"

    mensuel, funeraire = _percu(data, "mensuel"), _percu(data, "funéra")
    parallele, amende, reliquat = _percu(data, "parallèl"), _percu(data, "amende"), _percu(data, "reliquat")

    stats = (
        StatView("Cotisations mensuelles perçues", format_fcfa(mensuel), "Encaissé", "neutre"),
        StatView("Cotisations funéraires perçues", format_fcfa(funeraire), "Encaissé", "neutre"),
        StatView("Cotisations parallèles perçues", format_fcfa(parallele), "Encaissé", "neutre"),
        StatView("Amendes encaissées", format_fcfa(amende), "Encaissé", "neutre"),
        StatView("Total des dépenses", format_fcfa(data.expenses), "Sorties de l’exercice", "neutre"),
        StatView("Total des reliquats", format_fcfa(reliquat), "Entrées liées aux dépenses", "neutre"),
        StatView("Dettes restant à recouvrer", format_fcfa(data.debts_total), note_dettes,
                 "rouge" if data.debts_total > 0 else "neutre"),
        StatView("Solde financier", solde.texte(),
                 f"Entrées {format_fcfa(entrees)} − dépenses {format_fcfa(data.expenses)}", solde.couleur),
    )

    shares = tuple(
        ShareView(libelle, f"{_nombre(montant)} · {_pourcent(montant / entrees if entrees else 0.0)}",
                  montant / entrees if entrees else 0.0, couleur)
        for libelle, montant, couleur in (
            ("Cotisations mensuelles", mensuel, Color.NAVY_900),
            ("Cotisations funéraires", funeraire, Color.NAVY_700),
            ("Cotisations parallèles", parallele, Color.SUCCESS_600),
            ("Amendes", amende, Color.WARNING_600),
            ("Reliquats", reliquat, Color.GRAY_500),
        )
    )

    affiches = sorted(data.debtors, key=lambda debiteur: debiteur.amount, reverse=True)[:4]
    return DashboardViewModel(
        subtitle=(f"Synthèse de l’exercice {data.exercise_label} · montants en FCFA "
                  f"(encaissé réel uniquement)"),
        read_only=not data.is_open,
        alerts=tuple(AlertView(a.kind, a.text) for a in data.alerts),
        stats=stats,
        months=tuple(MonthView(m.label, m.entrees, m.depenses) for m in data.monthly),
        shares=shares,
        operations=tuple(_operation(o) for o in data.operations[:5]),
        debtors=tuple(DebtorView(d.member, d.carnet, format_fcfa(d.amount)) for d in affiches),
        debtors_counter=f"{len(affiches)} sur {max(data.debtor_members, len(affiches))}",
    )