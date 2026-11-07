"""Page Rapports et exports : catalogue des états disponibles pour l’exercice."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from app.ui.ports_reports import ReportsData
from app.ui.theme.tokens import Layout
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card
from app.ui.widgets.page_header import PageHeader

_REPORTS = (
    ("balance", "Bilan de l’exercice", "Entrées, dépenses, solde et manque à gagner par rubrique."),
    ("funeral", "Cotisations funéraires", "Une colonne par décès, montants perçus et dettes."),
    ("members", "Liste des membres", "Statuts, cotisations dues, versements, dettes et avances."),
    ("debts", "Dettes à recouvrer", "Membres débiteurs par rubrique, du plus ancien au plus récent."),
    ("monthly", "Cotisations mensuelles", "Tableau des 12 mois par membre."),
    ("expenses", "Journal des dépenses", "Dépenses, reliquats et bénéficiaires par période."),
)


class ReportsView(QWidget):
    export_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Rapports et exports", "")
        corps.addWidget(self.header)

        grille = QGridLayout()
        grille.setSpacing(Layout.CARD_GAP)
        self.report_cards: list[Card] = []
        self.export_buttons: list[AppButton] = []
        for index, (report_key, title, description) in enumerate(_REPORTS):
            card = Card(padding=16, spacing=10)
            card.body.addWidget(make_label(title, "card-title"))
            detail = make_label(description, "caption", wrap=True)
            detail.setMinimumHeight(36)
            card.body.addWidget(detail)
            actions = QHBoxLayout()
            for format_name, file_format in (("Excel", "excel"), ("PDF", "pdf"), ("Imprimer", "print")):
                button = AppButton(format_name, Variant.SECONDARY)
                button.setEnabled(file_format in ("excel", "pdf"))
                if file_format == "print":
                    button.setToolTip("L’impression directe n’est pas encore disponible.")
                else:
                    button.clicked.connect(
                        lambda _=False, key=report_key, fmt=file_format:
                        self.export_requested.emit(key, fmt)
                    )
                actions.addWidget(button)
                self.export_buttons.append(button)
            actions.addStretch(1)
            card.body.addLayout(actions)
            grille.addWidget(card, index // 3, index % 3)
            self.report_cards.append(card)
        corps.addLayout(grille)

        historique = Card(padding=16, spacing=8)
        historique.body.addWidget(make_label("Derniers exports", "card-title"))
        self.empty_history = make_label("Aucun export enregistré pour le moment.", "caption")
        self.empty_history.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_history.setMinimumHeight(76)
        historique.body.addWidget(self.empty_history)
        corps.addWidget(historique)
        corps.addStretch(1)

    def set_model(self, model: ReportsData) -> None:
        self.header.set_subtitle(
            f"États de l’exercice {model.exercise_label} · export Excel ou PDF"
        )
