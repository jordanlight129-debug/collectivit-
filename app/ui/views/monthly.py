"""Page Cotisations mensuelles : grille membres × 12 mois, saisie des versements par clic sur une case."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout,
                               QLineEdit, QVBoxLayout, QWidget)

from app.ui.presenters.monthly_model import MonthlyMemberRow, MonthlyViewModel
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.base import ClickableFrame, make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card, Separator
from app.ui.widgets.page_header import PageHeader

_MOIS = ("SEP", "OCT", "NOV", "DÉC", "JAN", "FÉV", "MAR", "AVR", "MAI", "JUIN", "JUIL", "AOÛT")
_COL_MOIS = 2                      # première colonne des mois (après N° et MEMBRE)
_COL_DU = _COL_MOIS + len(_MOIS)   # DÛ, PERÇU, DETTE, AVANCE
_NB_COLS = _COL_DU + 4
_PAD = 16

# (couleur du texte, couleur de fond) selon l'état d'une case — conforme à la maquette
_STYLES = {
    "paye": (Color.SUCCESS_600, "#E6F6EC"),
    "partiel": (Color.WARNING_600, "#FFF4DD"),
    "impaye": (Color.DANGER_600, "#FDE8E8"),
    "non_applicable": (Color.GRAY_500, "#EEF0F4"),
}
_FOND_TOTAL = "#EDF1F8"


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
    droite = _PAD if colonne == _NB_COLS - 1 else 8
    return gauche, droite


def _entier(texte: str) -> int:
    chiffres = "".join(c for c in str(texte) if c.isdigit())
    return int(chiffres) if chiffres else 0


def _montant(valeur: int) -> str:
    return f"{valeur:,}".replace(",", " ") if valeur else "—"


class MonthlyView(QWidget):
    search_changed = Signal(str)
    status_changed = Signal(str)
    sex_changed = Signal(str)
    sort_requested = Signal(str)
    page_requested = Signal(int)
    # Versement : carnet du membre, ou "" pour laisser l'utilisateur choisir le membre
    record_payment_requested = Signal(str)
    # Clic sur une case : carnet du membre, index du mois (0 = septembre … 11 = août)
    cell_clicked = Signal(str, int)
    export_requested = Signal()
    export_excel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        corps.addLayout(self._entete_page())
        corps.addWidget(self._carte_filtres())
        corps.addWidget(self._legende())
        corps.addWidget(self._carte_tableau())
        corps.addStretch(1)

        self._row_count = 0
        self.search.textChanged.connect(self.search_changed.emit)
        self.status_combo.currentIndexChanged.connect(
            lambda _i: self.status_changed.emit(str(self.status_combo.currentData())))
        self.sex_combo.currentIndexChanged.connect(
            lambda _i: self.sex_changed.emit(str(self.sex_combo.currentData())))
        self.export_button.clicked.connect(lambda _=False: self.export_requested.emit())
        self.export_excel_button.clicked.connect(lambda _=False: self.export_excel_requested.emit())
        self.record_button.clicked.connect(lambda _=False: self.record_payment_requested.emit(""))
        self._find = QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self)
        self._find.activated.connect(self.focus_search)

    # ---------- construction ----------
    def _entete_page(self) -> QHBoxLayout:
        ligne = QHBoxLayout()
        ligne.setSpacing(12)
        self.header = PageHeader("Cotisations mensuelles", "")
        ligne.addWidget(self.header, 1)
        self.export_button = AppButton("Exporter PDF", Variant.SECONDARY)
        self.export_excel_button = AppButton("Exporter Excel", Variant.SECONDARY)
        self.record_button = AppButton("+  Enregistrer un versement", Variant.PRIMARY)
        ligne.addWidget(self.export_button, 0, Qt.AlignmentFlag.AlignTop)
        ligne.addWidget(self.export_excel_button, 0, Qt.AlignmentFlag.AlignTop)
        ligne.addWidget(self.record_button, 0, Qt.AlignmentFlag.AlignTop)
        return ligne

    def _carte_filtres(self) -> Card:
        carte = Card(padding=14, spacing=0)
        ligne = QHBoxLayout()
        ligne.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher un membre…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(Layout.INPUT_HEIGHT)
        self.search.setMinimumWidth(280)
        ligne.addWidget(self.search, 3)
        self.status_combo = self._liste((
            ("Statut : Tous", "all"), ("Statut : À jour", "a_jour"), ("Statut : Partiel", "partiel"),
            ("Statut : En dette", "dette"), ("Statut : Avance", "avance")))
        ligne.addWidget(self.status_combo)
        self.sex_combo = self._liste((("Sexe : Tous", "all"), ("Sexe : Masculin", "M"),
                                      ("Sexe : Féminin", "F")))
        ligne.addWidget(self.sex_combo)
        ligne.addStretch(2)
        ligne.addWidget(make_label("Cliquer sur une case pour voir ou corriger le versement", "caption"))
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

    def _legende(self) -> QWidget:
        conteneur = QWidget()
        ligne = QHBoxLayout(conteneur)
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(16)
        ligne.addWidget(make_label("Légende", "caption"))
        for etat, texte in (("paye", "Payé"), ("partiel", "Partiel"),
                            ("impaye", "Dette (mois impayé)"), ("non_applicable", "Non applicable")):
            couleur, fond = _STYLES[etat]
            pastille = QFrame()
            pastille.setObjectName("Pastille")
            pastille.setFixedSize(14, 14)
            pastille.setStyleSheet(
                f"#Pastille {{ background: {fond}; border: 1.5px solid {couleur}; border-radius: 3px; }}")
            groupe = QHBoxLayout()
            groupe.setSpacing(6)
            groupe.addWidget(pastille)
            groupe.addWidget(make_label(texte, "caption"))
            ligne.addLayout(groupe)
        ligne.addStretch(1)
        return conteneur

    def _carte_tableau(self) -> Card:
        carte = Card(padding=0, spacing=0)
        self._grid = QGridLayout()
        self._grid.setSpacing(0)
        for colonne in range(_NB_COLS):
            if colonne == 0:
                poids = 1
            elif colonne == 1:
                poids = 4
            else:
                poids = 2
            self._grid.setColumnStretch(colonne, poids)
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

    # ---------- API pour le présentateur ----------
    def row_count(self) -> int:
        return self._row_count

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()

    def set_model(self, model: MonthlyViewModel) -> None:
        self.header.set_subtitle(model.subtitle)
        self._fill_table(model)
        self.counter.setText(model.counter)
        self._fill_pager(model)

    # ---------- tableau ----------
    def _fill_table(self, model: MonthlyViewModel) -> None:
        _clear_layout(self._grid)
        colonne = 0
        self._grid.addWidget(self._entete("carnet", "N°", colonne, False), 0, colonne)
        colonne += 1
        self._grid.addWidget(self._entete("name", "MEMBRE", colonne, False), 0, colonne)
        colonne += 1
        for mois in _MOIS:
            self._grid.addWidget(self._entete(f"month_{mois}", mois, colonne, False, centre=True), 0, colonne)
            colonne += 1
        for titre in ("DÛ", "PERÇU", "DETTE", "AVANCE"):
            self._grid.addWidget(self._entete(titre.lower(), titre, colonne, True), 0, colonne)
            colonne += 1

        ligne = 1
        for membre in model.rows:
            self._grid.addWidget(Separator(), ligne, 0, 1, _NB_COLS)
            ligne += 1
            self._remplir_ligne(membre, ligne)
            ligne += 1

        if model.empty:
            vide = make_label("Aucun membre ne correspond à votre recherche.", "caption")
            vide.setContentsMargins(_PAD, 20, _PAD, 20)
            self._grid.addWidget(vide, ligne, 0, 1, _NB_COLS)
        else:
            self._grid.addWidget(Separator(), ligne, 0, 1, _NB_COLS)
            ligne += 1
            self._remplir_totaux(model, ligne)
        self._row_count = len(model.rows)

    def _entete(self, cle: str, texte: str, colonne: int, droite: bool, *, centre: bool = False) -> QWidget:
        cadre = ClickableFrame()
        cadre.setObjectName("ColHead")
        cadre.setStyleSheet(f"#ColHead {{ background: {Color.GRAY_100}; }}")
        cadre.setMinimumHeight(Layout.TABLE_HEADER_HEIGHT)
        disposition = QHBoxLayout(cadre)
        gauche, droit = _marges(colonne)
        disposition.setContentsMargins(gauche, 0, droit, 0)
        etiquette = make_label(texte, "grid-head")
        if centre:
            etiquette.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            alignement = Qt.AlignmentFlag.AlignRight if droite else Qt.AlignmentFlag.AlignLeft
            etiquette.setAlignment(alignement | Qt.AlignmentFlag.AlignVCenter)
        disposition.addWidget(etiquette)
        cadre.clicked.connect(lambda k=cle: self.sort_requested.emit(k))
        return cadre

    @staticmethod
    def _cellule(texte: str, role: str, colonne: int, droite: bool = False,
                 couleur: str | None = None, fond: str | None = None) -> QLabel:
        etiquette = make_label(texte, role)
        etiquette.setMinimumHeight(Layout.TABLE_ROW_HEIGHT + 6)
        gauche, droit = _marges(colonne)
        etiquette.setContentsMargins(gauche, 0, droit, 0)
        alignement = Qt.AlignmentFlag.AlignRight if droite else Qt.AlignmentFlag.AlignLeft
        etiquette.setAlignment(alignement | Qt.AlignmentFlag.AlignVCenter)
        style = ""
        if couleur:
            style += f"color: {couleur};"
        if fond:
            style += f"background: {fond};"
        if style:
            etiquette.setStyleSheet(style)
        return etiquette

    def _case_mois(self, carnet: str, index_mois: int, cell) -> QWidget:
        """Case colorée et cliquable : un clic demande à voir/corriger le versement du mois."""
        couleur, fond = _STYLES.get(cell.status, _STYLES["non_applicable"])
        cadre = ClickableFrame()
        cadre.setObjectName("MonthCell")
        cadre.setStyleSheet(f"#MonthCell {{ background: {fond}; }}")
        cadre.setMinimumHeight(Layout.TABLE_ROW_HEIGHT + 6)
        cadre.setCursor(Qt.CursorShape.PointingHandCursor)
        cadre.setToolTip(f"{_MOIS[index_mois].capitalize()} · cliquer pour saisir ou corriger")
        disposition = QHBoxLayout(cadre)
        disposition.setContentsMargins(4, 0, 4, 0)
        etiquette = make_label(cell.symbol, "grid-cell")
        etiquette.setAlignment(Qt.AlignmentFlag.AlignCenter)
        etiquette.setStyleSheet(f"color: {couleur}; background: transparent;")
        etiquette.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        disposition.addWidget(etiquette)
        cadre.clicked.connect(lambda c=carnet, i=index_mois: self.cell_clicked.emit(c, i))
        return cadre

    def _remplir_ligne(self, m: MonthlyMemberRow, ligne: int) -> None:
        gris = Color.GRAY_500
        inactif = getattr(m, "inactive", False)
        couleur_nom = gris if inactif else None
        self._grid.addWidget(self._cellule(m.carnet, "grid-total", 0, couleur=couleur_nom or None), ligne, 0)
        self._grid.addWidget(self._cellule(m.name, "grid-cell", 1, couleur=couleur_nom), ligne, 1)
        colonne = _COL_MOIS
        for index_mois, cell in enumerate(m.cells):
            self._grid.addWidget(self._case_mois(m.carnet, index_mois, cell), ligne, colonne)
            colonne += 1
        couleur_dette = Color.DANGER_600 if m.has_debt else gris
        couleur_avance = Color.SUCCESS_600 if m.has_advance else gris
        role_dette = "grid-total" if m.has_debt else "grid-cell"
        role_avance = "grid-total" if m.has_advance else "grid-cell"
        self._grid.addWidget(self._cellule(m.total_due, "grid-cell", _COL_DU, True), ligne, _COL_DU)
        self._grid.addWidget(self._cellule(m.total_paid, "grid-cell", _COL_DU + 1, True), ligne, _COL_DU + 1)
        self._grid.addWidget(self._cellule(m.total_debt, role_dette, _COL_DU + 2, True, couleur_dette),
                             ligne, _COL_DU + 2)
        self._grid.addWidget(self._cellule(m.advance, role_avance, _COL_DU + 3, True, couleur_avance),
                             ligne, _COL_DU + 3)

    def _remplir_totaux(self, model: MonthlyViewModel, ligne: int) -> None:
        """Ligne « TOTAL (page) ». Utilise `model.totals` s'il existe, sinon additionne les lignes."""
        totaux = getattr(model, "totals", None)
        if totaux:
            du, percu, dette, avance = totaux
        else:
            du = _montant(sum(_entier(m.total_due) for m in model.rows))
            percu = _montant(sum(_entier(m.total_paid) for m in model.rows))
            dette = _montant(sum(_entier(m.total_debt) for m in model.rows))
            avance = _montant(sum(_entier(m.advance) for m in model.rows))
        self._grid.addWidget(self._cellule("", "grid-cell", 0, fond=_FOND_TOTAL), ligne, 0)
        self._grid.addWidget(self._cellule("TOTAL (page)", "grid-total", 1, fond=_FOND_TOTAL), ligne, 1)
        for colonne in range(_COL_MOIS, _COL_DU):
            self._grid.addWidget(self._cellule("", "grid-cell", colonne, fond=_FOND_TOTAL), ligne, colonne)
        self._grid.addWidget(self._cellule(du, "grid-total", _COL_DU, True, fond=_FOND_TOTAL), ligne, _COL_DU)
        self._grid.addWidget(self._cellule(percu, "grid-total", _COL_DU + 1, True, fond=_FOND_TOTAL),
                             ligne, _COL_DU + 1)
        self._grid.addWidget(self._cellule(dette, "grid-total", _COL_DU + 2, True, Color.DANGER_600, _FOND_TOTAL),
                             ligne, _COL_DU + 2)
        self._grid.addWidget(self._cellule(avance, "grid-total", _COL_DU + 3, True, Color.SUCCESS_600, _FOND_TOTAL),
                             ligne, _COL_DU + 3)

    # ---------- pagination ----------
    def _fill_pager(self, model: MonthlyViewModel) -> None:
        """Boutons Précédent/Suivant affichés seulement s'il y a plusieurs pages."""
        _clear_layout(self._pager)
        page = getattr(model, "page", 1)
        pages = getattr(model, "page_count", 1)
        if pages <= 1:
            return
        precedent = AppButton("Précédent", Variant.SECONDARY)
        precedent.setEnabled(page > 1)
        precedent.clicked.connect(lambda _=False, p=page - 1: self.page_requested.emit(p))
        self._pager.addWidget(precedent)
        self._pager.addWidget(make_label(f"Page {page}/{pages}", "caption"))
        suivant = AppButton("Suivant", Variant.SECONDARY)
        suivant.setEnabled(page < pages)
        suivant.clicked.connect(lambda _=False, p=page + 1: self.page_requested.emit(p))
        self._pager.addWidget(suivant)