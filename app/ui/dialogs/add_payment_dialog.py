"""Dialogue des versements mensuels d'un membre : liste, ajout, modification, suppression.

Les versements ne sont pas liés à un mois précis : le service les répartit
automatiquement sur les mois, du plus ancien au plus récent. Après chaque
opération, la liste et le résumé (dû, perçu, dette, avance) sont recalculés.
"""
from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDateEdit, QDialog, QHBoxLayout,
                               QHeaderView, QLineEdit, QMessageBox, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from app.database.connection import get_connection
from app.models.versement import MENSUELLE
from app.repositories import exercices
from app.security.session import Permission
from app.services import versement_service
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant

_MOIS_LONGS = ("septembre", "octobre", "novembre", "décembre", "janvier", "février",
               "mars", "avril", "mai", "juin", "juillet", "août")


def _fmt(montant: int) -> str:
    return f"{montant:,}".replace(",", " ") + " FCFA"


def _normaliser(carnet: str) -> str:
    texte = str(carnet).strip()
    if texte.lower().startswith("carnet"):
        texte = texte[6:].strip()
    return texte


def _meme_carnet(a: str, b: str) -> bool:
    a, b = _normaliser(a), _normaliser(b)
    if a == b:
        return True
    return a.isdigit() and b.isdigit() and int(a) == int(b)


def _trouver_membre_id(conn: sqlite3.Connection, carnet: str) -> int | None:
    """Retrouve l'identifiant du membre à partir de son numéro de carnet."""
    for ligne in conn.execute("SELECT * FROM membres").fetchall():
        for cle in ligne.keys():
            if "carnet" in cle.lower() and _meme_carnet(str(ligne[cle]), carnet):
                return int(ligne["id"])
    return None


def _champ(titre: str, widget: QWidget) -> QVBoxLayout:
    colonne = QVBoxLayout()
    colonne.setSpacing(4)
    colonne.addWidget(make_label(titre, "caption"))
    colonne.addWidget(widget)
    return colonne


class PaymentsDialog(QDialog):
    def __init__(self, *, members: list[tuple[str, str]], carnet: str, month_index: int,
                 exercise_label: str, session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = exercise_label
        self._session = session
        self._editing_id: int | None = None
        self._versements: dict[int, object] = {}
        self._changed = False
        self.setWindowTitle("Versements")
        self.setModal(True)
        self.setMinimumWidth(700)

        racine = QVBoxLayout(self)
        racine.setContentsMargins(24, 24, 24, 24)
        racine.setSpacing(14)
        racine.addWidget(make_label("Versements de cotisation mensuelle", "card-title"))
        racine.addWidget(make_label(f"Exercice {exercise_label}", "caption"))

        self.membre_combo = QComboBox()
        self.membre_combo.setFixedHeight(Layout.INPUT_HEIGHT)
        for numero, nom in members:
            self.membre_combo.addItem(f"{_normaliser(numero)} · {nom}", numero)
        position = self.membre_combo.findData(carnet) if carnet else 0
        self.membre_combo.setCurrentIndex(max(position, 0))
        self.membre_combo.setEnabled(not carnet)   # choix libre seulement depuis le bouton du haut
        racine.addLayout(_champ("Membre", self.membre_combo))

        if 0 <= month_index < len(_MOIS_LONGS):
            racine.addWidget(make_label(
                f"Case sélectionnée : {_MOIS_LONGS[month_index]}. Un versement est réparti "
                "automatiquement sur les mois, du plus ancien au plus récent.", "caption", wrap=True))
        else:
            racine.addWidget(make_label(
                "Un versement est réparti automatiquement sur les mois, "
                "du plus ancien au plus récent.", "caption", wrap=True))

        self.resume = make_label("", "card-title", wrap=True)
        racine.addWidget(self.resume)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Date", "Montant", "Note"])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(180)
        racine.addWidget(self.table)

        actions = QHBoxLayout()
        self.btn_modifier = AppButton("Modifier", Variant.SECONDARY)
        self.btn_supprimer = AppButton("Supprimer", Variant.SECONDARY)
        self.btn_modifier.setVisible(session.can(Permission.PAYMENT_EDIT))
        self.btn_supprimer.setVisible(session.can(Permission.DELETE))
        actions.addWidget(self.btn_modifier)
        actions.addWidget(self.btn_supprimer)
        actions.addStretch(1)
        racine.addLayout(actions)

        formulaire = QHBoxLayout()
        formulaire.setSpacing(12)
        self.montant = QSpinBox()
        self.montant.setRange(0, 100_000_000)
        self.montant.setSingleStep(500)
        self.montant.setSuffix(" FCFA")
        self.montant.setSpecialValueText("Montant")
        self.montant.setFixedHeight(Layout.INPUT_HEIGHT)
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd/MM/yyyy")
        self.date.setMaximumDate(QDate.currentDate())
        self.date.setDate(QDate.currentDate())
        self.date.setFixedHeight(Layout.INPUT_HEIGHT)
        self.note = QLineEdit()
        self.note.setMaxLength(200)
        self.note.setPlaceholderText("Facultatif")
        self.note.setFixedHeight(Layout.INPUT_HEIGHT)
        formulaire.addLayout(_champ("Montant", self.montant), 2)
        formulaire.addLayout(_champ("Date", self.date), 2)
        formulaire.addLayout(_champ("Note", self.note), 3)
        racine.addLayout(formulaire)

        self.erreur = make_label("", "caption", wrap=True)
        self.erreur.setStyleSheet(f"color: {Color.DANGER_600};")
        self.erreur.hide()
        racine.addWidget(self.erreur)

        pied = QHBoxLayout()
        self.btn_annuler_modif = AppButton("Annuler la modification", Variant.SECONDARY)
        self.btn_annuler_modif.hide()
        self.btn_enregistrer = AppButton("Enregistrer le versement", Variant.PRIMARY)
        self.btn_fermer = AppButton("Fermer", Variant.SECONDARY)
        pied.addWidget(self.btn_fermer)
        pied.addStretch(1)
        pied.addWidget(self.btn_annuler_modif)
        pied.addWidget(self.btn_enregistrer)
        racine.addLayout(pied)

        self.membre_combo.currentIndexChanged.connect(lambda _i: self._changer_membre())
        self.table.itemSelectionChanged.connect(self._maj_boutons)
        self.btn_modifier.clicked.connect(lambda _=False: self._commencer_modification())
        self.btn_supprimer.clicked.connect(lambda _=False: self._supprimer())
        self.btn_enregistrer.clicked.connect(lambda _=False: self._enregistrer())
        self.btn_annuler_modif.clicked.connect(lambda _=False: self._fin_modification())
        self.btn_fermer.clicked.connect(self.accept)

        self._charger()

    # ---------- API ----------
    def a_change(self) -> bool:
        """Vrai si au moins un versement a été ajouté, modifié ou supprimé."""
        return self._changed

    # ---------- chargement ----------
    def _carnet_courant(self) -> str:
        return str(self.membre_combo.currentData() or "")

    def _contexte(self, conn: sqlite3.Connection) -> tuple[int, int]:
        membre_id = _trouver_membre_id(conn, self._carnet_courant())
        if membre_id is None:
            raise versement_service.VersementError("Membre introuvable.")
        for exercice in exercices.list_all(conn):
            if exercice.libelle == self._label:
                return membre_id, exercice.id
        raise versement_service.VersementError("Exercice introuvable.")

    def _charger(self) -> None:
        self._versements = {}
        self.table.setRowCount(0)
        conn = get_connection()
        try:
            membre_id, exercice_id = self._contexte(conn)
            liste = versement_service.list_versements(
                conn, membre_id, exercice_id=exercice_id, rubrique=MENSUELLE)
            self._remplir(liste)
            try:
                releve = versement_service.releve_mensuel(conn, membre_id, exercice_id)
                self.resume.setText(
                    f"Dû {_fmt(releve.total_due)} · Perçu {_fmt(releve.total_paid)} · "
                    f"Dette {_fmt(releve.total_debt)} · Avance {_fmt(releve.advance)}")
            except Exception as e:
                self.resume.setText(str(e))
        except Exception as e:
            self._afficher_erreur(str(e) or "Impossible de charger les versements.")
        finally:
            conn.close()
        self._maj_boutons()

    def _remplir(self, liste) -> None:
        self.table.setRowCount(len(liste))
        for ligne, v in enumerate(liste):
            self._versements[v.id] = v
            note = v.note or ""
            if getattr(v, "nature", "courant") == "arriere":
                note = (note + " (arriérés)").strip()
            cellules = (v.date_versement.strftime("%d/%m/%Y"), _fmt(v.montant), note)
            for colonne, texte in enumerate(cellules):
                item = QTableWidgetItem(texte)
                if colonne == 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if colonne == 0:
                    item.setData(Qt.ItemDataRole.UserRole, v.id)
                self.table.setItem(ligne, colonne, item)

    # ---------- état ----------
    def _selection_id(self) -> int | None:
        ligne = self.table.currentRow()
        item = self.table.item(ligne, 0) if ligne >= 0 else None
        return int(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

    def _maj_boutons(self) -> None:
        a_selection = self._selection_id() is not None
        self.btn_modifier.setEnabled(a_selection)
        self.btn_supprimer.setEnabled(a_selection)

    def _afficher_erreur(self, texte: str) -> None:
        self.erreur.setText(texte)
        self.erreur.setVisible(bool(texte))

    def _changer_membre(self) -> None:
        self._fin_modification()
        self._charger()

    # ---------- modification ----------
    def _commencer_modification(self) -> None:
        versement = self._versements.get(self._selection_id() or -1)
        if versement is None:
            return
        self._editing_id = versement.id
        self.montant.setValue(versement.montant)
        d = versement.date_versement
        self.date.setDate(QDate(d.year, d.month, d.day))
        self.note.setText(versement.note or "")
        self.btn_enregistrer.setText("Enregistrer les modifications")
        self.btn_annuler_modif.show()
        self._afficher_erreur("")

    def _fin_modification(self) -> None:
        self._editing_id = None
        self.montant.setValue(0)
        self.date.setDate(QDate.currentDate())
        self.note.clear()
        self.btn_enregistrer.setText("Enregistrer le versement")
        self.btn_annuler_modif.hide()
        self._afficher_erreur("")

    # ---------- enregistrement ----------
    def _enregistrer(self) -> None:
        montant = self.montant.value()
        if montant <= 0:
            self._afficher_erreur("Saisissez un montant supérieur à zéro.")
            return
        date_versement = self.date.date().toPython()
        note = self.note.text()
        conn = get_connection()
        try:
            membre_id, exercice_id = self._contexte(conn)
            if self._editing_id is None:
                versement_service.enregistrer(conn, self._session, membre_id, exercice_id,
                                              MENSUELLE, montant, date_versement, note)
            else:
                versement_service.modifier(conn, self._session, self._editing_id, montant,
                                           date_versement, note)
        except Exception as e:
            self._afficher_erreur(str(e) or "Opération refusée.")
            return
        finally:
            conn.close()
        self._changed = True
        self._fin_modification()
        self._charger()

    def _supprimer(self) -> None:
        versement = self._versements.get(self._selection_id() or -1)
        if versement is None:
            return
        reponse = QMessageBox.question(
            self, "Supprimer le versement",
            f"Supprimer le versement de {_fmt(versement.montant)} "
            f"du {versement.date_versement.strftime('%d/%m/%Y')} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reponse != QMessageBox.StandardButton.Yes:
            return
        conn = get_connection()
        try:
            versement_service.supprimer(conn, self._session, versement.id)
        except Exception as e:
            self._afficher_erreur(str(e) or "Opération refusée.")
            return
        finally:
            conn.close()
        self._changed = True
        self._fin_modification()
        self._charger()