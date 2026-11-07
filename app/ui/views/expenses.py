"""Page Dépenses."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QVBoxLayout, QWidget)

from app.ui.presenters.expenses_model import ExpenseRow, ExpensesViewModel
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card, Separator
from app.ui.widgets.page_header import PageHeader

_COLONNES = (
    ("date", "DATE", 2, False),
    ("label", "LIBELLÉ", 4, False),
    ("beneficiary", "BÉNÉFICIAIRE", 3, False),
    ("planned", "PRÉVU (FCFA)", 2, True),
    ("spent", "DÉPENSÉ (FCFA)", 2, True),
)
_COLONNE_ACTIONS = len(_COLONNES)
_PAD = 16


def _clear_layout(layout: QLayout) -> None:
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


def _marges(colonne: int) -> tuple[int, int]:
    gauche = _PAD if colonne == 0 else 8
    droite = _PAD if colonne == _COLONNE_ACTIONS else 8
    return gauche, droite


class ExpensesView(QWidget):
    search_changed = Signal(str)
    sort_requested = Signal(str)
    page_requested = Signal(int)
    add_requested = Signal()
    expense_action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Dépenses", "")
        self.add_button = AppButton("Nouvelle dépense", Variant.PRIMARY, "plus")
        self.header.add_action(self.add_button)
        corps.addWidget(self.header)

        corps.addWidget(self._carte_totaux())
        corps.addWidget(self._carte_filtres())
        corps.addWidget(self._carte_tableau())
        corps.addStretch(1)

        self._row_count = 0
        self._model: ExpensesViewModel | None = None
        self._can_delete = False
        self.search.textChanged.connect(self.search_changed.emit)
        self._find = QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self)
        self._find.activated.connect(self.focus_search)
        self.add_button.clicked.connect(lambda: self.add_requested.emit())

    def _carte_totaux(self) -> Card:
        carte = Card(padding=14, spacing=0)
        ligne = QHBoxLayout()
        ligne.setSpacing(12)
        self.total_planned_label = make_label("", "caption")
        self.total_spent_label = make_label("", "caption")
        ligne.addWidget(make_label("Totaux :", "card-title"))
        ligne.addWidget(self.total_planned_label)
        ligne.addWidget(make_label("Prévu", "caption"))
        ligne.addWidget(self.total_spent_label)
        ligne.addWidget(make_label("Dépensé", "caption"))
        ligne.addStretch(1)
        carte.body.addLayout(ligne)
        return carte

    def _carte_filtres(self) -> Card:
        carte = Card(padding=14, spacing=0)
        ligne = QHBoxLayout()
        ligne.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher par libellé…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(Layout.INPUT_HEIGHT)
        self.search.setMinimumWidth(320)
        ligne.addWidget(self.search, 3)
        ligne.addStretch(2)
        ligne.addWidget(make_label("Ctrl + F pour rechercher · clic sur un en-tête pour trier", "caption"))
        carte.body.addLayout(ligne)
        return carte

    def _carte_tableau(self) -> Card:
        carte = Card(padding=0, spacing=0)
        self._grid = QGridLayout()
        self._grid.setSpacing(0)
        for colonne, (_cle, _titre, poids, _droite) in enumerate(_COLONNES):
            self._grid.setColumnStretch(colonne, poids)
        self._grid.setColumnStretch(_COLONNE_ACTIONS, 1)
        carte.body.addLayout(self._grid)
        carte.body.addWidget(Separator())
        pied = QHBoxLayout()
        pied.setContentsMargins(_PAD, 12, _PAD, 12)
        self.counter = make_label("", "caption")
        pied.addWidget(self.counter)
        pied.addStretch(1)
        self._pager = QHBoxLayout()
        self._pager.setSpacing(6)
        pied.addLayout(self._pager)
        carte.body.addLayout(pied)
        return carte

    def row_count(self) -> int:
        return self._row_count

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()

    def set_model(self, model: ExpensesViewModel) -> None:
        self._model = model
        self.header.set_subtitle(model.subtitle)
        self.total_planned_label.setText(model.total_planned)
        self.total_spent_label.setText(model.total_spent)
        self.add_button.setEnabled(not model.read_only)
        self.add_button.setToolTip("Exercice clôturé : saisie impossible" if model.read_only else "")
        self._fill_table(model)
        self.counter.setText(model.counter)
        self._fill_pager(model)

    def set_error(self, message: str) -> None:
        self._model = None
        self.header.set_subtitle("")
        self.total_planned_label.setText("—")
        self.total_spent_label.setText("—")
        self.add_button.setEnabled(False)
        self.add_button.setToolTip(message)
        _clear_layout(self._grid)
        self.error_label = make_label(message, "caption", wrap=True)
        self.error_label.setContentsMargins(_PAD, 20, _PAD, 20)
        self._grid.addWidget(self.error_label, 0, 0, 1, _COLONNE_ACTIONS + 1)
        _clear_layout(self._pager)
        self.counter.setText("")
        self._row_count = 0

    def set_can_delete(self, can_delete: bool) -> None:
        self._can_delete = can_delete
        if self._model is not None:
            self._fill_table(self._model)

    def _fill_table(self, model: ExpensesViewModel) -> None:
        _clear_layout(self._grid)
        for colonne, (cle, titre, _poids, droite) in enumerate(_COLONNES):
            fleche = (" ▲" if model.ascending else " ▼") if cle == model.sort_key else ""
            self._grid.addWidget(self._entete(cle, titre + fleche, colonne, droite), 0, colonne)
        self._grid.addWidget(self._entete("", "", _COLONNE_ACTIONS, False, cliquable=False),
                             0, _COLONNE_ACTIONS)
        ligne = 1
        for expense in model.rows:
            self._grid.addWidget(Separator(), ligne, 0, 1, _COLONNE_ACTIONS + 1)
            ligne += 1
            self._remplir_ligne(expense, ligne)
            ligne += 1
        if model.empty:
            vide = make_label("Aucune dépense enregistrée.", "caption")
            vide.setContentsMargins(_PAD, 20, _PAD, 20)
            self._grid.addWidget(vide, ligne, 0, 1, _COLONNE_ACTIONS + 1)
        self._row_count = len(model.rows)

    def _entete(self, cle: str, texte: str, colonne: int, droite: bool, *, cliquable: bool = True) -> QWidget:
        from app.ui.widgets.base import ClickableFrame
        cadre = ClickableFrame()
        cadre.setObjectName("ColHead")
        cadre.setStyleSheet(f"#ColHead {{ background: {Color.GRAY_100}; }}")
        cadre.setMinimumHeight(Layout.TABLE_HEADER_HEIGHT)
        disposition = QHBoxLayout(cadre)
        gauche, droit = _marges(colonne)
        disposition.setContentsMargins(gauche, 0, droit, 0)
        etiquette = make_label(texte, "grid-head")
        alignement = Qt.AlignmentFlag.AlignRight if droite else Qt.AlignmentFlag.AlignLeft
        etiquette.setAlignment(alignement | Qt.AlignmentFlag.AlignVCenter)
        disposition.addWidget(etiquette)
        if cliquable:
            cadre.clicked.connect(lambda k=cle: self.sort_requested.emit(k))
        else:
            cadre.setCursor(Qt.CursorShape.ArrowCursor)
            cadre.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return cadre

    @staticmethod
    def _cellule(texte: str, role: str, colonne: int, droite: bool = False,
                 couleur: str | None = None) -> QLabel:
        etiquette = make_label(texte, role)
        etiquette.setMinimumHeight(Layout.TABLE_ROW_HEIGHT + 6)
        gauche, droit = _marges(colonne)
        etiquette.setContentsMargins(gauche, 0, droit, 0)
        alignement = Qt.AlignmentFlag.AlignRight if droite else Qt.AlignmentFlag.AlignLeft
        etiquette.setAlignment(alignement | Qt.AlignmentFlag.AlignVCenter)
        if couleur:
            etiquette.setStyleSheet(f"color: {couleur};")
        return etiquette

    def _remplir_ligne(self, e: ExpenseRow, ligne: int) -> None:
        gris = Color.GRAY_500
        self._grid.addWidget(self._cellule(e.date, "grid-cell", 0, couleur=gris), ligne, 0)
        self._grid.addWidget(self._cellule(e.label, "grid-cell", 1), ligne, 1)
        self._grid.addWidget(self._cellule(e.beneficiary, "grid-cell", 2, couleur=gris), ligne, 2)
        self._grid.addWidget(self._cellule(e.amount_planned, "grid-cell", 3, True), ligne, 3)
        couleur_spent = Color.DANGER_600 if e.is_over_budget else None
        self._grid.addWidget(self._cellule(e.amount_spent, "grid-total", 4, True, couleur_spent), ligne, 4)
        actions = AppButton("•••", Variant.LINK)
        actions.setFixedWidth(40)
        actions.setVisible(self._can_delete)
        actions.setEnabled(not self._model.read_only if self._model is not None else False)
        actions.clicked.connect(lambda _=False, i=e.id: self.expense_action_requested.emit(i))
        self._grid.addWidget(actions, ligne, _COLONNE_ACTIONS,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _fill_pager(self, model: ExpensesViewModel) -> None:
        _clear_layout(self._pager)
        precedent = AppButton("Précédent", Variant.SECONDARY)
        precedent.setEnabled(model.page > 1)
        precedent.clicked.connect(lambda: self.page_requested.emit(model.page - 1))
        self._pager.addWidget(precedent)
        suivant = AppButton("Suivant", Variant.SECONDARY)
        suivant.setEnabled(model.page < model.page_count)
        suivant.clicked.connect(lambda: self.page_requested.emit(model.page + 1))
        self.previous_button = precedent
        self.next_button = suivant
        self._pager.addWidget(suivant)
