"""Page Membres (maquette Figma) : filtres, tableau trié et paginé, légende.
Affichage seul : elle reçoit un MembersViewModel et émet des signaux."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QVBoxLayout, QWidget)

from app.ui.presenters.members_model import MemberRow, MembersViewModel
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.badge import Badge
from app.ui.widgets.base import ClickableFrame, make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card, Separator
from app.ui.widgets.page_header import PageHeader

# (clé de tri, titre, poids, aligné à droite)
_COLONNES = (
    ("carnet", "N° CARNET", 2, False),
    ("name", "NOM COMPLET", 5, False),
    ("sex", "SEXE", 1, False),
    ("joined", "ADHÉSION", 2, False),
    ("status", "STATUT", 2, False),
    ("du", "DÛ (FCFA)", 2, True),
    ("recu", "REÇU (FCFA)", 2, True),
    ("dette", "DETTE (FCFA)", 2, True),
    ("avance", "AVANCE (FCFA)", 2, True),
)
_COLONNE_ACTIONS = len(_COLONNES)
_PAD = 16
_LEGENDE = ("Légende : Dette en rouge = somme restant à verser · Avance en vert = versement "
            "supérieur au dû · Ligne grisée = membre décédé")


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


def _marges(colonne: int) -> tuple[int, int]:
    gauche = _PAD if colonne == 0 else 8
    droite = _PAD if colonne == _COLONNE_ACTIONS else 8
    return gauche, droite


class MembersView(QWidget):
    export_requested = Signal()
    export_excel_requested = Signal()
    add_requested = Signal()
    search_changed = Signal(str)
    status_changed = Signal(str)
    sex_changed = Signal(str)
    sort_requested = Signal(str)
    page_requested = Signal(int)
    member_action_requested = Signal(int, str)   # id, n° de carnet

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Membres", "")
        self.export_button = AppButton("Exporter PDF", Variant.SECONDARY, "file")
        self.export_excel_button = AppButton("Exporter Excel", Variant.SECONDARY)
        self.add_button = AppButton("Ajouter un membre", Variant.PRIMARY, "plus")
        self.header.add_action(self.export_button)
        self.header.add_action(self.export_excel_button)
        self.header.add_action(self.add_button)
        corps.addWidget(self.header)

        corps.addWidget(self._carte_filtres())
        corps.addWidget(self._carte_tableau())
        corps.addWidget(make_label(_LEGENDE, "caption"))
        corps.addStretch(1)

        self._row_count = 0
        self.export_button.clicked.connect(lambda: self.export_requested.emit())
        self.export_excel_button.clicked.connect(lambda: self.export_excel_requested.emit())
        self.add_button.clicked.connect(lambda: self.add_requested.emit())
        self.search.textChanged.connect(self.search_changed.emit)
        self.status_combo.currentIndexChanged.connect(
            lambda _i: self.status_changed.emit(str(self.status_combo.currentData())))
        self.sex_combo.currentIndexChanged.connect(
            lambda _i: self.sex_changed.emit(str(self.sex_combo.currentData())))
        self._find = QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self)
        self._find.activated.connect(self.focus_search)

    # ---------- construction ----------
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
        self.status_combo = self._liste((("Statut : Tous", "tous"), ("Statut : Actif", "actif"),
                                         ("Statut : Décédé", "decede")))
        self.sex_combo = self._liste((("Sexe : Tous", "tous"), ("Sexe : Masculin", "M"),
                                      ("Sexe : Féminin", "F")))
        ligne.addWidget(self.status_combo)
        ligne.addWidget(self.sex_combo)
        ligne.addStretch(2)
        ligne.addWidget(make_label("Ctrl + F pour rechercher · clic sur un en-tête pour trier", "caption"))
        carte.body.addLayout(ligne)
        return carte

    @staticmethod
    def _liste(options: tuple[tuple[str, str], ...]) -> QComboBox:
        liste = QComboBox()
        for texte, cle in options:
            liste.addItem(texte, cle)
        liste.setFixedHeight(Layout.INPUT_HEIGHT)
        liste.setMinimumWidth(150)
        return liste

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

    # ---------- API ----------
    def row_count(self) -> int:
        return self._row_count

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()

    def set_model(self, model: MembersViewModel) -> None:
        self.header.set_subtitle(model.subtitle)
        self._fill_table(model)
        self.counter.setText(model.counter)
        self._fill_pager(model)

    # ---------- remplissage ----------
    def _fill_table(self, model: MembersViewModel) -> None:
        _clear_layout(self._grid)
        for colonne, (cle, titre, _poids, droite) in enumerate(_COLONNES):
            fleche = (" ▲" if model.ascending else " ▼") if cle == model.sort_key else ""
            self._grid.addWidget(self._entete(cle, titre + fleche, colonne, droite), 0, colonne)
        self._grid.addWidget(self._entete("", "", _COLONNE_ACTIONS, False, cliquable=False),
                             0, _COLONNE_ACTIONS)
        ligne = 1
        for membre in model.rows:
            self._grid.addWidget(Separator(), ligne, 0, 1, _COLONNE_ACTIONS + 1)
            ligne += 1
            self._remplir_ligne(membre, ligne)
            ligne += 1
        if model.empty:
            vide = make_label("Aucun membre ne correspond à votre recherche.", "caption")
            vide.setContentsMargins(_PAD, 20, _PAD, 20)
            self._grid.addWidget(vide, ligne, 0, 1, _COLONNE_ACTIONS + 1)
        self._row_count = len(model.rows)

    def _entete(self, cle: str, texte: str, colonne: int, droite: bool, *, cliquable: bool = True) -> QWidget:
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

    def _remplir_ligne(self, m: MemberRow, ligne: int) -> None:
        gris = Color.GRAY_500
        base = gris if m.deceased else None
        self._grid.addWidget(self._cellule(m.carnet, "grid-total", 0, couleur=base), ligne, 0)
        self._grid.addWidget(self._cellule(m.name, "grid-cell", 1, couleur=base), ligne, 1)
        self._grid.addWidget(self._cellule(m.sex, "grid-cell", 2, couleur=gris), ligne, 2)
        self._grid.addWidget(self._cellule(m.joined, "grid-cell", 3, couleur=gris), ligne, 3)
        badge = Badge(m.status, m.status_kind)
        self._grid.addWidget(badge, ligne, 4, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._grid.addWidget(self._cellule(m.du, "grid-cell", 5, True, base), ligne, 5)
        self._grid.addWidget(self._cellule(m.recu, "grid-cell", 6, True, base), ligne, 6)
        couleur_dette = Color.DANGER_600 if m.has_debt else gris
        couleur_avance = Color.SUCCESS_600 if m.has_advance else gris
        role_dette = "grid-total" if m.has_debt else "grid-cell"
        role_avance = "grid-total" if m.has_advance else "grid-cell"
        self._grid.addWidget(self._cellule(m.dette, role_dette, 7, True, couleur_dette), ligne, 7)
        self._grid.addWidget(self._cellule(m.avance, role_avance, 8, True, couleur_avance), ligne, 8)
        actions = AppButton("•••", Variant.LINK)
        actions.setToolTip(f"Actions pour {m.name}")
        actions.setFixedWidth(40)
        actions.clicked.connect(lambda _=False, id=m.id, carnet=m.carnet: self.member_action_requested.emit(id, carnet))
        self._grid.addWidget(actions, ligne, _COLONNE_ACTIONS,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _fill_pager(self, model: MembersViewModel) -> None:
        _clear_layout(self._pager)
        precedent = AppButton("Précédent", Variant.SECONDARY)
        precedent.setEnabled(model.has_prev)
        precedent.clicked.connect(lambda: self.page_requested.emit(model.page - 1))
        self._pager.addWidget(precedent)
        for numero in model.page_numbers:
            courant = numero == model.page
            bouton = AppButton(str(numero), Variant.PRIMARY if courant else Variant.SECONDARY)
            bouton.setFixedWidth(40)
            bouton.clicked.connect(lambda _=False, p=numero: self.page_requested.emit(p))
            self._pager.addWidget(bouton)
        suivant = AppButton("Suivant", Variant.SECONDARY)
        suivant.setEnabled(model.has_next)
        suivant.clicked.connect(lambda: self.page_requested.emit(model.page + 1))
        self._pager.addWidget(suivant)
