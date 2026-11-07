"""Fiche de consultation d'un membre et de son historique financier."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QGridLayout, QHBoxLayout,
                               QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from app.models.membre import Membre
from app.services import carnet_service
from app.services.historique_service import PageHistorique
from app.ui.format import format_date, format_fcfa
from app.ui.theme.tokens import Layout
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import StatCard


class MemberDashboardDialog(QDialog):
    """Synthèse de l'exercice courant et historique complet, en lecture seule."""

    def __init__(self, membre: Membre, exercise_label: str,
                 exercice: PageHistorique, historique: PageHistorique,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Fiche membre — {membre.nom}")
        self.setMinimumSize(760, 560)
        self.resize(900, 650)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(make_label(membre.nom, "page-title"))
        statut = "Actif" if membre.statut == "actif" else "Décédé"
        layout.addWidget(make_label(
            f"{carnet_service.format_carnet_label(membre.numero_carnet)} · {statut} · Membre depuis "
            f"{format_date(membre.date_adhesion)}", "caption"))

        cards = QGridLayout()
        cards.setSpacing(Layout.CARD_GAP)
        dernier = format_date(historique.lignes[0].date_operation) if historique.lignes else "Aucun"
        valeurs = (
            ("Total encaissé", format_fcfa(exercice.entrees), f"Exercice {exercise_label}"),
            ("Opérations", str(exercice.total), f"Exercice {exercise_label}"),
            ("Dernière opération", dernier, "Tous exercices"),
        )
        self.summary_cards: list[StatCard] = []
        for index, (titre, valeur, note) in enumerate(valeurs):
            carte = StatCard()
            carte.set_content(titre, valeur, note, "neutre")
            cards.addWidget(carte, 0, index)
            self.summary_cards.append(carte)
        layout.addLayout(cards)

        layout.addWidget(make_label("Historique des paiements", "card-title"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(("DATE", "EXERCICE", "OPÉRATION", "MONTANT (FCFA)"))
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setRowCount(len(historique.lignes))
        for row, transaction in enumerate(historique.lignes):
            valeurs_ligne = (
                format_date(transaction.date_operation),
                transaction.periode or "",
                transaction.libelle,
                format_fcfa(transaction.montant),
            )
            for column, value in enumerate(valeurs_ligne):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)
        self.table.setMinimumHeight(260)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.close_button = AppButton("Fermer", Variant.SECONDARY)
        self.close_button.clicked.connect(self.accept)
        actions.addWidget(self.close_button)
        layout.addLayout(actions)