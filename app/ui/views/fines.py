"""Page Amendes."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QVBoxLayout, QWidget)

from app.ui.presenters.fines_model import FineRow, FinesViewModel
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.badge import Badge
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card, Separator, StatCard
from app.ui.widgets.page_header import PageHeader

_COLONNES = (
    ("date", "DATE", 2, False),
    ("name", "MEMBRE", 4, False),
    ("label", "LIBELLÉ", 3, False),
    ("expected", "ATTENDU", 2, True),
    ("collected", "COLLECTÉ", 2, True),
    ("remaining", "MANQUE À GAGNER", 2, True),
    ("status", "STATUT", 2, False),
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


class FinesView(QWidget):
    search_changed = Signal(str)
    status_changed = Signal(str)
    sort_requested = Signal(str)
    page_requested = Signal(int)
    add_requested = Signal()
    fine_action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Amendes", "")
        self.add_button = AppButton("Nouvelle amende", Variant.PRIMARY, "plus")
        self.header.add_action(self.add_button)
        corps.addWidget(self.header)

        resume = QHBoxLayout()
        resume.setSpacing(Layout.CARD_GAP)
        self.expected_card = StatCard()
        self.collected_card = StatCard()
        self.remaining_card = StatCard()
        for card in (self.expected_card, self.collected_card, self.remaining_card):
            resume.addWidget(card, 1)
        corps.addLayout(resume)

        corps.addWidget(self._carte_filtres())
        corps.addWidget(self._carte_tableau())
        corps.addStretch(1)

        self._row_count = 0
        self.search.textChanged.connect(self.search_changed.emit)
        self.status_combo.currentIndexChanged.connect(
            lambda _index: self.status_changed.emit(str(self.status_combo.currentData())))
        self._find = QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self)
        self._find.activated.connect(self.focus_search)
        self.add_button.clicked.connect(lambda: self.add_requested.emit())

    def _carte_filtres(self) -> Card:
        carte = Card(padding=14, spacing=0)
        ligne = QHBoxLayout()
        ligne.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher par nom ou n° de carnet…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(Layout.INPUT_HEIGHT)
        self.search.setMinimumWidth(320)
        ligne.addWidget(self.search, 3)
        self.status_combo = QComboBox()
        for label, key in (("Statut : Tous", "tous"), ("Payée", "payee"),
                           ("Partielle", "partielle"), ("Impayée", "impayee")):
            self.status_combo.addItem(label, key)
        self.status_combo.setFixedHeight(Layout.INPUT_HEIGHT)
        self.status_combo.setMinimumWidth(160)
        ligne.addWidget(self.status_combo)
        ligne.addWidget(make_label("Période : Exercice", "caption"))
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

    def set_model(self, model: FinesViewModel) -> None:
        self.header.set_subtitle(model.subtitle)
        self.expected_card.set_content("Amendes attendues", f"{model.total_expected} FCFA", "Montant total infligé")
        self.collected_card.set_content("Amendes collectées", f"{model.total_collected} FCFA", "Encaissé", "vert")
        self.remaining_card.set_content("Manque à gagner", f"{model.total_remaining} FCFA", "Non encaissé",
                                        "rouge" if model.total_remaining != "0" else "vert")
        self.add_button.setEnabled(model.is_open)
        self._fill_table(model)
        self.counter.setText(model.counter)
        self._fill_pager(model)

    def _fill_table(self, model: FinesViewModel) -> None:
        _clear_layout(self._grid)
        for colonne, (cle, titre, _poids, droite) in enumerate(_COLONNES):
            fleche = (" ▲" if model.rows and model.rows[0] else "") if cle == "date" else ""
            self._grid.addWidget(self._entete(cle, titre + fleche, colonne, droite), 0, colonne)
        self._grid.addWidget(self._entete("", "", _COLONNE_ACTIONS, False, cliquable=False),
                             0, _COLONNE_ACTIONS)
        ligne = 1
        for fine in model.rows:
            self._grid.addWidget(Separator(), ligne, 0, 1, _COLONNE_ACTIONS + 1)
            ligne += 1
            self._remplir_ligne(fine, ligne)
            ligne += 1
        if model.empty:
            vide = make_label("Aucune amende ne correspond aux filtres.", "caption")
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

    def _remplir_ligne(self, f: FineRow, ligne: int) -> None:
        gris = Color.GRAY_500
        self._grid.addWidget(self._cellule(f.date, "grid-cell", 0, couleur=gris), ligne, 0)
        self._grid.addWidget(self._cellule(f.member_name, "grid-cell", 1), ligne, 1)
        self._grid.addWidget(self._cellule(f.label, "grid-cell", 2), ligne, 2)
        self._grid.addWidget(self._cellule(f.amount_expected, "grid-cell", 3, True), ligne, 3)
        self._grid.addWidget(self._cellule(f.amount_collected, "grid-cell", 4, True), ligne, 4)
        couleur_rest = Color.DANGER_600 if not f.is_paid else Color.SUCCESS_600
        self._grid.addWidget(self._cellule(f.remaining, "grid-total", 5, True, couleur_rest), ligne, 5)
        self._grid.addWidget(Badge(f.status, f.status_kind), ligne, 6,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        actions = AppButton("Encaisser", Variant.LINK)
        actions.setToolTip(f"Encaisser une partie ou la totalité de l’amende de {f.member_name}")
        actions.setEnabled(not f.is_paid)
        actions.clicked.connect(lambda _=False, i=f.id: self.fine_action_requested.emit(i))
        self._grid.addWidget(actions, ligne, _COLONNE_ACTIONS,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _fill_pager(self, model: FinesViewModel) -> None:
        _clear_layout(self._pager)
