"""Page Cotisations parallèles."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QVBoxLayout, QWidget)

from app.ui.presenters.parallel_model import ParallelRow, ParallelViewModel
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.badge import Badge, Kind
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card, Separator
from app.ui.widgets.page_header import PageHeader

_COLONNES = (
    ("name", "NOM DE LA COTISATION", 3, False),
    ("period", "PÉRIODE", 3, False),
    ("men", "HOMMES", 1, True),
    ("women", "FEMMES", 1, True),
    ("expected", "ATTENDU", 2, True),
    ("collected", "PERÇU", 2, True),
    ("remaining", "DETTE", 2, True),
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


class ParallelView(QWidget):
    search_changed = Signal(str)
    sort_requested = Signal(str)
    page_requested = Signal(int)
    add_requested = Signal()
    subscription_action_requested = Signal(int)
    record_payment_requested = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Cotisations parallèles", "")
        self.add_button = AppButton("Nouvelle cotisation", Variant.PRIMARY, "plus")
        self.header.add_action(self.add_button)
        corps.addWidget(self.header)

        corps.addWidget(self._carte_filtres())
        corps.addWidget(self._carte_tableau())
        corps.addWidget(self._carte_details())
        corps.addStretch(1)

        self._row_count = 0
        self.search.textChanged.connect(self.search_changed.emit)
        self._find = QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self)
        self._find.activated.connect(self.focus_search)
        self.add_button.clicked.connect(lambda: self.add_requested.emit())

    def _carte_filtres(self) -> Card:
        carte = Card(padding=14, spacing=0)
        ligne = QHBoxLayout()
        ligne.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher par nom…")
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
        carte.body.addWidget(make_label("Cotisations de l’exercice", "card-title"))
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

    def _carte_details(self) -> Card:
        carte = Card(padding=0, spacing=0)
        entete = QVBoxLayout()
        entete.setContentsMargins(_PAD, _PAD, _PAD, 8)
        entete.setSpacing(4)
        entete.addWidget(make_label("Détail par membre", "card-title"))
        self.detail_title = make_label("Sélectionnez une cotisation", "caption")
        entete.addWidget(self.detail_title)
        carte.body.addLayout(entete)

        self._detail_grid = QGridLayout()
        self._detail_grid.setSpacing(0)
        self._detail_counter = make_label("", "caption")
        carte.body.addLayout(self._detail_grid)
        carte.body.addWidget(Separator())
        pied = QHBoxLayout()
        pied.setContentsMargins(_PAD, 10, _PAD, 10)
        pied.addWidget(self._detail_counter)
        pied.addStretch(1)
        carte.body.addLayout(pied)
        return carte

    def row_count(self) -> int:
        return self._row_count

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()

    def set_model(self, model: ParallelViewModel) -> None:
        self.header.set_subtitle(model.subtitle)
        self._fill_table(model)
        self.counter.setText(model.counter)
        self._fill_pager(model)
        self._fill_details(model)

    def _fill_table(self, model: ParallelViewModel) -> None:
        _clear_layout(self._grid)
        for colonne, (cle, titre, _poids, droite) in enumerate(_COLONNES):
            fleche = (" ▲" if model.rows and model.rows[0] else "") if cle == "name" else ""
            self._grid.addWidget(self._entete(cle, titre + fleche, colonne, droite), 0, colonne)
        self._grid.addWidget(self._entete("", "", _COLONNE_ACTIONS, False, cliquable=False),
                             0, _COLONNE_ACTIONS)
        ligne = 1
        for sub in model.rows:
            self._grid.addWidget(Separator(), ligne, 0, 1, _COLONNE_ACTIONS + 1)
            ligne += 1
            self._remplir_ligne(sub, ligne)
            ligne += 1
        if model.empty:
            vide = make_label("Aucune cotisation parallèle enregistrée.", "caption")
            vide.setContentsMargins(_PAD, 20, _PAD, 20)
            self._grid.addWidget(vide, ligne, 0, 1, _COLONNE_ACTIONS + 1)
        else:
            self._grid.addWidget(Separator(), ligne, 0, 1, _COLONNE_ACTIONS + 1)
            ligne += 1
            self._grid.addWidget(self._cellule("TOTAL", "grid-total", 0), ligne, 0)
            for colonne in (1, 2, 3, 7, 8):
                self._grid.addWidget(QWidget(), ligne, colonne)
            self._grid.addWidget(self._cellule(model.total_expected, "grid-total", 4, True), ligne, 4)
            self._grid.addWidget(self._cellule(model.total_collected, "grid-total", 5, True), ligne, 5)
            self._grid.addWidget(self._cellule(model.total_debt, "grid-total", 6, True), ligne, 6)
        self._row_count = len(model.rows)

    def _fill_details(self, model: ParallelViewModel) -> None:
        _clear_layout(self._detail_grid)
        self.detail_title.setText(
            f"{model.selected_name} · {model.selected_period}" if model.selected_name
            else "Sélectionnez une cotisation"
        )
        colonnes = ("N°", "MEMBRE", "SEXE", "ATTENDU (FCFA)", "PERÇU (FCFA)", "DETTE (FCFA)", "STATUT", "ACTION")
        poids = (1, 4, 1, 2, 2, 2, 2, 2)
        for column, (title, weight) in enumerate(zip(colonnes, poids)):
            self._detail_grid.setColumnStretch(column, weight)
            cadre = QWidget()
            cadre.setObjectName("ColHead")
            cadre.setStyleSheet(f"#ColHead {{ background: {Color.GRAY_100}; }}")
            disposition = QHBoxLayout(cadre)
            disposition.setContentsMargins(_PAD if column == 0 else 8, 0, 8, 0)
            label = make_label(title, "grid-head")
            label.setAlignment((Qt.AlignmentFlag.AlignRight if column in (3, 4, 5)
                                else Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignVCenter)
            disposition.addWidget(label)
            self._detail_grid.addWidget(cadre, 0, column)

        if not model.detail_rows:
            self._detail_grid.addWidget(make_label("Aucun membre concerné.", "caption"),
                                        1, 0, 1, len(colonnes))
        for row, member in enumerate(model.detail_rows, start=1):
            values = (member.carnet, member.name, member.sex, member.expected,
                      member.collected, member.debt, member.status, "")
            for column, text in enumerate(values):
                cell = make_label(text, "grid-cell")
                cell.setMinimumHeight(Layout.TABLE_ROW_HEIGHT + 6)
                cell.setContentsMargins(_PAD if column == 0 else 8, 0, 8, 0)
                if column in (3, 4, 5):
                    cell.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if column == 6:
                    kind = Kind.SUCCESS if member.status == "Payé" else Kind.WARNING if member.status == "Partiel" else Kind.DANGER
                    self._detail_grid.addWidget(Badge(text, kind), row, column,
                                                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                elif column == 7:
                    payment = AppButton("Encaisser", Variant.LINK)
                    payment.clicked.connect(
                        lambda _=False, mid=member.member_id, cid=model.selected_subscription_id:
                        self.record_payment_requested.emit(mid, cid)
                    )
                    self._detail_grid.addWidget(payment, row, column)
                else:
                    self._detail_grid.addWidget(cell, row, column)
        self._detail_counter.setText(model.detail_counter)

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

    def _remplir_ligne(self, r: ParallelRow, ligne: int) -> None:
        self._grid.addWidget(self._cellule(r.name, "grid-cell", 0), ligne, 0)
        self._grid.addWidget(self._cellule(r.period, "grid-cell", 1, couleur=Color.GRAY_500), ligne, 1)
        self._grid.addWidget(self._cellule(r.men, "grid-cell", 2, True), ligne, 2)
        self._grid.addWidget(self._cellule(r.women, "grid-cell", 3, True), ligne, 3)
        self._grid.addWidget(self._cellule(r.total_expected, "grid-cell", 4, True), ligne, 4)
        self._grid.addWidget(self._cellule(r.total_collected, "grid-cell", 5, True), ligne, 5)
        couleur_rest = Color.DANGER_600 if not r.is_complete else Color.SUCCESS_600
        self._grid.addWidget(self._cellule(r.remaining, "grid-total", 6, True, couleur_rest), ligne, 6)
        self._grid.addWidget(Badge(r.status, Kind.SUCCESS if r.is_complete else Kind.WARNING), ligne, 7,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        actions = AppButton("Détail", Variant.LINK)
        actions.setToolTip(f"Afficher les membres de {r.name}")
        actions.clicked.connect(lambda _=False, i=r.id: self.subscription_action_requested.emit(i))
        self._grid.addWidget(actions, ligne, _COLONNE_ACTIONS,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _fill_pager(self, model: ParallelViewModel) -> None:
        _clear_layout(self._pager)
