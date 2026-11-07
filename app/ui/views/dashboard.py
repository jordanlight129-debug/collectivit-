"""Tableau de bord (maquette Figma) : 8 cartes, graphique mensuel, répartition des recettes,
dernières opérations, raccourcis, membres avec dettes.
Affichage seul : il reçoit un DashboardViewModel et émet des signaux."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLayout, QVBoxLayout, QWidget

from app.ui.presenters.dashboard_model import (DashboardViewModel, DebtorView, OperationView,
                                               ShareView)
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.badge import Badge
from app.ui.widgets.banner import Banner
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card, Separator, StatCard
from app.ui.widgets.charts import MonthlyChart, RatioBar
from app.ui.widgets.page_header import PageHeader

_COLONNES_OPERATIONS = ("DATE", "LIBELLÉ", "RUBRIQUE", "MONTANT (FCFA)", "STATUT")
_POIDS_OPERATIONS = (2, 5, 2, 3, 2)
_TONS = {"vert": Color.SUCCESS_600, "neutre": Color.GRAY_900, "gris": Color.GRAY_500}
_NOMBRE_CARTES = 8
_CARTES_PAR_LIGNE = 4


def _clear_layout(layout: QLayout) -> None:
    """Retire et détruit tous les éléments d'une disposition (rafraîchissement)."""
    while layout.count():
        element = layout.takeAt(0)
        widget = element.widget()
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        elif element.layout() is not None:
            _clear_layout(element.layout())
            element.layout().deleteLater()


def _colorer(etiquette: QLabel, couleur: str) -> QLabel:
    etiquette.setStyleSheet(f"color: {couleur};")
    return etiquette


class DashboardView(QWidget):
    payment_requested = Signal()
    expense_requested = Signal()
    member_requested = Signal()
    collecte_requested = Signal()
    export_requested = Signal()          # « Exporter le bilan »
    export_excel_requested = Signal()
    backup_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Tableau de bord", "")
        self.payment_button = AppButton("Enregistrer un versement", Variant.PRIMARY, "plus")
        self.expense_button = AppButton("Nouvelle dépense", Variant.SECONDARY, "plus")
        self.header.add_action(self.payment_button)
        self.header.add_action(self.expense_button)
        corps.addWidget(self.header)

        self.alerts_container = QWidget()
        self.alerts_layout = QVBoxLayout(self.alerts_container)
        self.alerts_layout.setContentsMargins(0, 0, 0, 0)
        self.alerts_layout.setSpacing(10)
        corps.addWidget(self.alerts_container)
        self.alerts_container.hide()

        cartes = QGridLayout()
        cartes.setSpacing(Layout.CARD_GAP)
        self.stat_cards = [StatCard() for _ in range(_NOMBRE_CARTES)]
        for index, carte in enumerate(self.stat_cards):
            ligne, colonne = divmod(index, _CARTES_PAR_LIGNE)
            cartes.addWidget(carte, ligne, colonne)
            cartes.setColumnStretch(colonne, 1)
        corps.addLayout(cartes)

        haut = QHBoxLayout()
        haut.setSpacing(Layout.CARD_GAP)
        haut.addWidget(self._carte_graphique(), 5)
        haut.addWidget(self._carte_repartition(), 3)
        corps.addLayout(haut)

        bas = QHBoxLayout()
        bas.setSpacing(Layout.CARD_GAP)
        bas.addWidget(self._carte_operations(), 5)
        droite = QVBoxLayout()
        droite.setSpacing(Layout.CARD_GAP)
        droite.addWidget(self._carte_raccourcis())
        droite.addWidget(self._carte_dettes())
        droite.addStretch(1)
        bas.addLayout(droite, 3)
        corps.addLayout(bas)
        corps.addStretch(1)

        self._share_count = 0
        self._operation_rows = 0
        self._debtor_rows = 0
        self.payment_button.clicked.connect(lambda: self.payment_requested.emit())
        self.expense_button.clicked.connect(lambda: self.expense_requested.emit())
        self.member_button.clicked.connect(lambda: self.member_requested.emit())
        self.collecte_button.clicked.connect(lambda: self.collecte_requested.emit())
        self.export_button.clicked.connect(lambda: self.export_requested.emit())
        self.export_excel_button.clicked.connect(lambda: self.export_excel_requested.emit())
        self.backup_button.clicked.connect(lambda: self.backup_requested.emit())

    # ---------- construction ----------
    def _carte_graphique(self) -> Card:
        carte = Card()
        entete = QHBoxLayout()
        entete.addWidget(make_label("Entrées et dépenses par mois (milliers de FCFA)", "card-title"))
        entete.addStretch(1)
        legende = make_label(
            f'<span style="color:{Color.SUCCESS_600}">■</span> Entrées &nbsp;&nbsp; '
            f'<span style="color:{Color.NAVY_900}">■</span> Dépenses', "caption")
        legende.setTextFormat(Qt.TextFormat.RichText)
        entete.addWidget(legende)
        carte.body.addLayout(entete)
        self.chart = MonthlyChart()
        carte.body.addWidget(self.chart, 1)
        return carte

    def _carte_repartition(self) -> Card:
        carte = Card()
        carte.body.addWidget(make_label("Répartition des recettes", "card-title"))
        self._shares = QVBoxLayout()
        self._shares.setSpacing(10)
        carte.body.addLayout(self._shares)
        carte.body.addStretch(1)
        return carte

    def _carte_operations(self) -> Card:
        carte = Card()
        carte.body.addWidget(make_label("Dernières opérations", "card-title"))
        self._ops = QGridLayout()
        self._ops.setHorizontalSpacing(12)
        self._ops.setVerticalSpacing(0)
        for colonne, poids in enumerate(_POIDS_OPERATIONS):
            self._ops.setColumnStretch(colonne, poids)
        carte.body.addLayout(self._ops)
        carte.body.addStretch(1)
        return carte

    def _carte_raccourcis(self) -> Card:
        carte = Card()
        carte.body.addWidget(make_label("Raccourcis", "card-title"))
        grille = QGridLayout()
        grille.setSpacing(10)
        self.member_button = AppButton("Ajouter un membre", Variant.SECONDARY, "users")
        self.collecte_button = AppButton("Nouvelle collecte", Variant.SECONDARY, "heart")
        self.export_button = AppButton("Bilan PDF", Variant.SECONDARY, "file")
        self.export_excel_button = AppButton("Bilan Excel", Variant.SECONDARY)
        self.backup_button = AppButton("Sauvegarder", Variant.SECONDARY, "database")
        for index, bouton in enumerate((self.member_button, self.collecte_button,
                        self.export_button, self.export_excel_button,
                        self.backup_button)):
            grille.addWidget(bouton, *divmod(index, 2))
        grille.setColumnStretch(0, 1)
        grille.setColumnStretch(1, 1)
        carte.body.addLayout(grille)
        return carte

    def _carte_dettes(self) -> Card:
        carte = Card()
        entete = QHBoxLayout()
        entete.addWidget(make_label("Membres avec dettes", "card-title"))
        entete.addStretch(1)
        self.debtors_counter = make_label("", "caption")
        entete.addWidget(self.debtors_counter)
        carte.body.addLayout(entete)
        self._debtors = QVBoxLayout()
        self._debtors.setSpacing(0)
        carte.body.addLayout(self._debtors)
        return carte

    # ---------- API ----------
    def share_count(self) -> int:
        return self._share_count

    def operation_row_count(self) -> int:
        return self._operation_rows

    def debtor_row_count(self) -> int:
        return self._debtor_rows

    def set_model(self, model: DashboardViewModel) -> None:
        self.header.set_subtitle(model.subtitle)
        for bouton in (self.payment_button, self.expense_button):
            bouton.setEnabled(not model.read_only)
            bouton.setToolTip("Exercice clôturé : saisie impossible" if model.read_only else "")

        while self.alerts_layout.count():
            item = self.alerts_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if model.alerts:
            for alert in model.alerts:
                self.alerts_layout.addWidget(Banner(alert.kind, alert.text))
            self.alerts_container.show()
        else:
            self.alerts_container.hide()

        for carte, stat in zip(self.stat_cards, model.stats):
            carte.set_content(stat.label, stat.amount, stat.note, stat.tone)
        self.chart.set_months([(m.label, m.entrees, m.depenses) for m in model.months])
        self._fill_shares(model.shares)
        self._fill_operations(model.operations)
        self.debtors_counter.setText(model.debtors_counter)
        self._fill_debtors(model.debtors)

    # ---------- remplissage ----------
    def _fill_shares(self, shares: tuple[ShareView, ...]) -> None:
        _clear_layout(self._shares)
        for part in shares:
            bloc = QVBoxLayout()
            bloc.setSpacing(4)
            ligne = QHBoxLayout()
            ligne.addWidget(make_label(part.label, "row-title"))
            ligne.addStretch(1)
            ligne.addWidget(make_label(part.text, "caption"))
            bloc.addLayout(ligne)
            bloc.addWidget(RatioBar(part.ratio, part.color))
            self._shares.addLayout(bloc)
        self._share_count = len(shares)

    @staticmethod
    def _cellule(texte: str, role: str, droite: bool = False) -> QLabel:
        etiquette = make_label(texte, role)
        etiquette.setMinimumHeight(Layout.TABLE_ROW_HEIGHT)
        alignement = Qt.AlignmentFlag.AlignRight if droite else Qt.AlignmentFlag.AlignLeft
        etiquette.setAlignment(alignement | Qt.AlignmentFlag.AlignVCenter)
        return etiquette

    def _fill_operations(self, operations: tuple[OperationView, ...]) -> None:
        _clear_layout(self._ops)
        for colonne, texte in enumerate(_COLONNES_OPERATIONS):
            self._ops.addWidget(self._cellule(texte, "grid-head", colonne == 3), 0, colonne)
        ligne = 1
        for operation in operations:
            self._ops.addWidget(Separator(), ligne, 0, 1, 5)
            ligne += 1
            self._ops.addWidget(_colorer(self._cellule(operation.date, "grid-cell"), Color.GRAY_500), ligne, 0)
            self._ops.addWidget(self._cellule(operation.label, "grid-cell"), ligne, 1)
            self._ops.addWidget(_colorer(self._cellule(operation.rubrique, "grid-cell"), Color.GRAY_500), ligne, 2)
            montant = _colorer(self._cellule(operation.amount, "grid-total", True), _TONS[operation.tone])
            self._ops.addWidget(montant, ligne, 3)
            self._ops.addWidget(Badge(operation.status, operation.status_kind), ligne, 4,
                                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            ligne += 1
        self._operation_rows = len(operations)

    def _fill_debtors(self, debtors: tuple[DebtorView, ...]) -> None:
        _clear_layout(self._debtors)
        if not debtors:
            self._debtors.addWidget(make_label("Aucune dette en cours.", "caption"))
        for index, debiteur in enumerate(debtors):
            if index:
                self._debtors.addWidget(Separator())
            ligne = QWidget()
            disposition = QHBoxLayout(ligne)
            disposition.setContentsMargins(0, 8, 0, 8)
            textes = QVBoxLayout()
            textes.setSpacing(2)
            textes.addWidget(make_label(debiteur.member, "row-title"))
            textes.addWidget(make_label(debiteur.carnet, "caption"))
            disposition.addLayout(textes, 1)
            disposition.addWidget(_colorer(make_label(debiteur.amount, "grid-total"), Color.DANGER_600), 0,
                                  Qt.AlignmentFlag.AlignVCenter)
            self._debtors.addWidget(ligne)
        self._debtor_rows = len(debtors)