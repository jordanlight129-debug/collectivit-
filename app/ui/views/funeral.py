"""Page Cotisations funéraires : liste des décès et collectes."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QVBoxLayout, QWidget)

from app.ui.presenters.funeral_model import FuneralRow, FuneralViewModel
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.badge import Badge
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card, Separator
from app.ui.widgets.page_header import PageHeader

_COLONNES = (
    ("date", "DATE", 2, False),
    ("name", "DÉFUNT", 4, False),
    ("type", "TYPE", 2, False),
    ("carnet", "N° CARNET", 2, False),
    ("expected", "ATTENDU (FCFA)", 2, True),
    ("collected", "COLLECTÉ (FCFA)", 2, True),
    ("remaining", "RESTANT (FCFA)", 2, True),
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


class FuneralView(QWidget):
    search_changed = Signal(str)
    sort_requested = Signal(str)
    page_requested = Signal(int)
    add_requested = Signal()
    record_action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Cotisations funéraires", "")
        self.add_button = AppButton("Nouveau décès", Variant.PRIMARY, "plus")
        self.header.add_action(self.add_button)
        corps.addWidget(self.header)

        corps.addWidget(self._legende())
        corps.addWidget(self._carte_filtres())
        corps.addWidget(self._carte_tableau())
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
        self.search.setPlaceholderText("Rechercher un membre ou un n° de carnet…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(Layout.INPUT_HEIGHT)
        self.search.setMinimumWidth(320)
        ligne.addWidget(self.search, 3)
        ligne.addStretch(2)
        ligne.addWidget(make_label("Ctrl + F pour rechercher · clic sur un en-tête pour trier", "caption"))
        carte.body.addLayout(ligne)
        return carte

    @staticmethod
    def _legende() -> QWidget:
        legende = QWidget()
        ligne = QHBoxLayout(legende)
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(18)
        ligne.addWidget(make_label("Légende", "caption"))
        for couleur, texte in ((Color.SUCCESS_600, "Payé"), (Color.WARNING_600, "Partiel"),
                               (Color.DANGER_600, "Dette"), (Color.GRAY_500, "Non concerné / exempté")):
            etiquette = make_label(f"●  {texte}", "caption")
            etiquette.setStyleSheet(f"color: {couleur};")
            ligne.addWidget(etiquette)
        ligne.addStretch(1)
        return legende

    def _carte_tableau(self) -> Card:
        carte = Card(padding=0, spacing=0)
        self._grid = QGridLayout()
        self._grid.setSpacing(0)
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

    def set_model(self, model: FuneralViewModel) -> None:
        self.header.set_subtitle(model.subtitle)
        self._fill_table(model)
        self.counter.setText(model.counter)
        self._fill_pager(model)

    def _fill_table(self, model: FuneralViewModel) -> None:
        _clear_layout(self._grid)
        from app.ui.widgets.base import ClickableFrame

        labels = ["N°", "MEMBRE"] + [column.title for column in model.columns] + ["DÛ", "PERÇU", "DETTE", "ACTION"]
        sort_keys = ["carnet", "name"] + [None] * len(model.columns) + ["due", "paid", "debt", None]
        column_count = len(labels)
        for column, (text, sort_key) in enumerate(zip(labels, sort_keys)):
            header = ClickableFrame()
            header.setObjectName("ColHead")
            header.setStyleSheet(f"#ColHead {{ background: {Color.GRAY_100}; }}")
            header.setMinimumHeight(Layout.TABLE_HEADER_HEIGHT)
            layout = QVBoxLayout(header)
            layout.setContentsMargins(8 if column else _PAD, 4, 8, 4)
            caption = make_label(text, "grid-head")
            layout.addWidget(caption)
            if 2 <= column < 2 + len(model.columns):
                death = model.columns[column - 2]
                layout.addWidget(make_label(death.detail, "caption", wrap=True))
                layout.addWidget(make_label(death.tariff, "caption", wrap=True))
            if sort_key:
                header.clicked.connect(lambda key=sort_key: self.sort_requested.emit(key))
                header.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                header.setCursor(Qt.CursorShape.ArrowCursor)
                header.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._grid.addWidget(header, 0, column)
            weight = 4 if column == 1 else (3 if 2 <= column < 2 + len(model.columns) else 1)
            self._grid.setColumnStretch(column, weight)

        if model.empty:
            empty = make_label("Aucun membre ou aucune collecte ne correspond à la recherche.", "caption")
            empty.setContentsMargins(_PAD, 20, _PAD, 20)
            self._grid.addWidget(empty, 1, 0, 1, column_count)
            self._row_count = 0
            return

        status_colors = {
            "paye": (Color.SUCCESS_600, "#E3F4EB"),
            "partiel": (Color.WARNING_600, "#FDEFDD"),
            "impaye": (Color.DANGER_600, "#FBE6E6"),
            "defunt": (Color.GRAY_500, Color.GRAY_100),
            "exempte": (Color.GRAY_500, Color.GRAY_100),
            "non_concerne": (Color.GRAY_500, Color.GRAY_100),
            "na": (Color.GRAY_500, Color.GRAY_100),
        }

        def add_cell(text: str, row: int, column: int, *, role: str = "grid-cell",
                     right: bool = False, status: str | None = None) -> None:
            label = make_label(text, role, wrap=True)
            label.setMinimumHeight(Layout.TABLE_ROW_HEIGHT + 6)
            label.setContentsMargins(8 if column else _PAD, 4, _PAD if column == column_count - 1 else 8, 4)
            align = Qt.AlignmentFlag.AlignRight if right else Qt.AlignmentFlag.AlignLeft
            label.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            if status in status_colors:
                foreground, background = status_colors[status]
                label.setStyleSheet(f"color: {foreground}; background: {background};")
            self._grid.addWidget(label, row, column)

        for row, member in enumerate(model.rows, start=1):
            self._grid.addWidget(Separator(), row * 2 - 1, 0, 1, column_count)
            display_row = row * 2
            add_cell(member.carnet, display_row, 0, role="grid-total")
            add_cell(member.name, display_row, 1, role="grid-total")
            for index, cell in enumerate(member.cells):
                add_cell(cell.text, display_row, index + 2, status=cell.status)
            start_total = 2 + len(model.columns)
            add_cell(member.due, display_row, start_total, right=True)
            add_cell(member.paid, display_row, start_total + 1, right=True)
            add_cell(member.debt, display_row, start_total + 2, right=True,
                     status="impaye" if member.debt not in ("0", "—") else "paye")
            payment = AppButton("Encaisser", Variant.LINK)
            payment.setToolTip(f"Enregistrer un versement pour {member.name}")
            payment.clicked.connect(lambda _=False, i=member.id: self.record_action_requested.emit(i))
            self._grid.addWidget(payment, display_row, start_total + 3,
                                 Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        total_row = len(model.rows) * 2 + 1
        self._grid.addWidget(Separator(), total_row, 0, 1, column_count)
        total_label = make_label(model.total_row_label, "grid-total", wrap=True)
        total_label.setMinimumHeight(Layout.TABLE_ROW_HEIGHT + 6)
        total_label.setContentsMargins(_PAD, 4, 8, 4)
        self._grid.addWidget(total_label, total_row + 1, 0, 1, 2)
        for index in range(len(model.columns)):
            self._grid.addWidget(QWidget(), total_row + 1, index + 2)
        start_total = 2 + len(model.columns)
        add_cell(model.page_due, total_row + 1, start_total, role="grid-total", right=True)
        add_cell(model.page_paid, total_row + 1, start_total + 1, role="grid-total", right=True)
        add_cell(model.page_debt, total_row + 1, start_total + 2, role="grid-total", right=True)
        self._grid.addWidget(QWidget(), total_row + 1, start_total + 3)
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

    def _remplir_ligne(self, r: FuneralRow, ligne: int) -> None:
        gris = Color.GRAY_500
        self._grid.addWidget(self._cellule(r.death_date, "grid-cell", 0, couleur=gris), ligne, 0)
        self._grid.addWidget(self._cellule(r.deceased_name, "grid-cell", 1), ligne, 1)
        self._grid.addWidget(self._cellule(r.death_type, "grid-cell", 2, couleur=gris), ligne, 2)
        self._grid.addWidget(self._cellule(r.member_carnet, "grid-total", 3), ligne, 3)
        self._grid.addWidget(self._cellule(r.total_expected, "grid-cell", 4, True), ligne, 4)
        self._grid.addWidget(self._cellule(r.total_collected, "grid-cell", 5, True), ligne, 5)
        couleur_rest = Color.DANGER_600 if not r.is_complete else Color.SUCCESS_600
        self._grid.addWidget(self._cellule(r.remaining, "grid-total", 6, True, couleur_rest), ligne, 6)
        actions = AppButton("•••", Variant.LINK)
        actions.setFixedWidth(40)
        actions.clicked.connect(lambda _=False, i=r.id: self.record_action_requested.emit(i))
        self._grid.addWidget(actions, ligne, _COLONNE_ACTIONS,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _fill_pager(self, model: FuneralViewModel) -> None:
        _clear_layout(self._pager)
        precedent = AppButton("Précédent", Variant.SECONDARY)
        precedent.setEnabled(model.has_previous)
        precedent.clicked.connect(lambda: self.page_requested.emit(model.page - 1))
        self._pager.addWidget(precedent)
        self._pager.addWidget(make_label(f"Page {model.page} sur {model.page_count}", "caption"))
        suivant = AppButton("Suivant", Variant.SECONDARY)
        suivant.setEnabled(model.has_next)
        suivant.clicked.connect(lambda: self.page_requested.emit(model.page + 1))
        self._pager.addWidget(suivant)
