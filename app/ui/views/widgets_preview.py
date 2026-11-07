"""Aperçu des composants dans une coquille proche de la fenêtre principale (données factices)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLineEdit, QMainWindow, QScrollArea, QVBoxLayout, QWidget,
)

from app.config import APP_NAME
from app.config import ASSOCIATION_NAME, BRAND_INITIALS
from app.services.affichage import DETTE, EXCEDENT, SOLDE, Situation
from app.ui.format import format_fcfa
from app.ui.navigation import Page, allowed_keys
from app.ui.theme.tokens import Layout
from app.ui.widgets.badge import Badge, Kind, status_badge
from app.ui.widgets.banner import Banner, Toast
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, IconButton, Variant
from app.ui.widgets.card import Card, StatCard
from app.ui.widgets.field import FormField
from app.ui.widgets.labels import SituationLabel
from app.ui.widgets.page_header import PageHeader
from app.ui.widgets.sidebar import Sidebar
from app.ui.widgets.statusbar import AppStatusBar
from app.ui.widgets.topbar import TopBar


class WidgetsPreview(QMainWindow):
    """Coquille de démonstration : barre latérale, barre supérieure, contenu, barre d'état."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} : aperçu des composants")
        self.setMinimumSize(*Layout.MIN_WINDOW)
        self.resize(1360, 860)
        self._admin = True

        centre = QWidget()
        racine = QHBoxLayout(centre)
        racine.setContentsMargins(0, 0, 0, 0)
        racine.setSpacing(0)

        self.sidebar = Sidebar(brand_name=ASSOCIATION_NAME, brand_sub="Gestion d’association",
                       brand_initials=BRAND_INITIALS, footer="Version 1.0 · Mode hors ligne")
        self.sidebar.set_active(Page.DASHBOARD)
        self.sidebar.navigate.connect(self._on_navigate)
        racine.addWidget(self.sidebar)

        droite = QVBoxLayout()
        droite.setContentsMargins(0, 0, 0, 0)
        droite.setSpacing(0)
        self.topbar = TopBar(f"Association {ASSOCIATION_NAME}")
        self.topbar.set_exercise("Exercice 2025–2026 (sept. → août)")
        self.topbar.set_user("Ama Kpodar", "Administrateur")
        self.topbar.exercise_requested.connect(lambda w: self.toast.popup("warning", "Sélecteur d'exercice", "Popover à venir (étape suivante)."))
        self.topbar.notifications_requested.connect(lambda w: self.toast.popup("success", "Notifications", "Popover à venir (étape suivante)."))
        self.topbar.user_requested.connect(lambda w: self.toast.popup("success", "Menu utilisateur", "Popover à venir (étape suivante)."))
        droite.addWidget(self.topbar)

        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        defilement.setFrameShape(QFrame.Shape.NoFrame)
        defilement.setWidget(self._page())
        droite.addWidget(defilement, 1)

        self.statusbar = AppStatusBar()
        self.statusbar.set_database(True, "Base de données locale : connectée")
        self.statusbar.set_exercise("Exercice actif : 2025–2026")
        self.statusbar.set_last_backup("Dernière sauvegarde : 28/08/2026 à 17:42")
        self.statusbar.set_notice("Données fictives de démonstration")
        droite.addWidget(self.statusbar)
        racine.addLayout(droite, 1)
        self.setCentralWidget(centre)

        self.toast = Toast(centre)

    def _on_navigate(self, key: str) -> None:
        self.header.set_subtitle(f"Entrée de la barre latérale cliquée : {key}")

    def _bascule_role(self) -> None:
        self._admin = not self._admin
        self.sidebar.set_allowed(allowed_keys(self._admin))
        self.topbar.set_user("Ama Kpodar" if self._admin else "Yawa Dovi",
                             "Administrateur" if self._admin else "Secrétaire")

    def _page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("Page")
        corps = QVBoxLayout(page)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Composants", "Chaque composant dans ses états : passez la souris, cliquez, naviguez au clavier")
        self.header.add_action(AppButton("Exporter", Variant.SECONDARY, "file"))
        self.header.add_action(AppButton("Enregistrer un versement", Variant.PRIMARY, "plus"))
        corps.addWidget(self.header)

        cartes = QGridLayout()
        cartes.setSpacing(Layout.CARD_GAP)
        stats = (
            ("Cotisations mensuelles perçues", format_fcfa(4860000), "Encaissé", "neutre"),
            ("Dettes restant à recouvrer", format_fcfa(1430000), "Non encaissé · 21 membres", "rouge"),
            ("Solde financier", Situation(EXCEDENT, 122000).texte(), "Entrées − dépenses", "vert"),
            ("Solde d'ouverture", Situation(DETTE, 378000).texte(), "L'association a dépensé plus qu'elle n'a encaissé", "rouge"),
        )
        for colonne, (libelle, montant, note, ton) in enumerate(stats):
            cartes.addWidget(StatCard(libelle, montant, note, ton), 0, colonne)
            cartes.setColumnStretch(colonne, 1)
        corps.addLayout(cartes)

        corps.addWidget(self._carte_boutons())
        corps.addWidget(self._carte_badges())
        corps.addWidget(self._carte_champs())
        corps.addWidget(self._carte_messages())
        corps.addStretch(1)
        return page

    def _carte_boutons(self) -> Card:
        carte = Card()
        carte.body.addWidget(make_label("Boutons", "card-title"))
        ligne = QHBoxLayout()
        ligne.setSpacing(Layout.CARD_GAP)
        for texte, variante, icone, actif in (
                ("Enregistrer", Variant.PRIMARY, "check", True), ("Annuler", Variant.SECONDARY, None, True),
                ("Supprimer", Variant.DANGER, "trash", True), ("Enregistrer", Variant.PRIMARY, None, False),
                ("Annuler", Variant.SECONDARY, None, False), ("Voir le détail", Variant.LINK, None, True)):
            bouton = AppButton(texte, variante, icone)
            bouton.setEnabled(actif)
            ligne.addWidget(bouton)
        ligne.addWidget(IconButton("bell", "Notifications"))
        ligne.addStretch(1)
        carte.body.addLayout(ligne)
        return carte

    def _carte_badges(self) -> Card:
        carte = Card()
        carte.body.addWidget(make_label("Badges et situations (jamais de signe moins)", "card-title"))
        ligne = QHBoxLayout()
        ligne.setSpacing(Layout.SECTION_GAP)
        for statut in ("paye", "partiel", "impaye", "na", "actif", "decede"):
            ligne.addWidget(status_badge(statut))
        ligne.addWidget(Badge("Reliquat", Kind.INFO))
        for situation in (Situation(EXCEDENT, 122000), Situation(DETTE, 378000), Situation(SOLDE, 0)):
            ligne.addWidget(SituationLabel(situation))
        ligne.addStretch(1)
        carte.body.addLayout(ligne)
        return carte

    def _carte_champs(self) -> Card:
        carte = Card()
        carte.body.addWidget(make_label("Champs de formulaire", "card-title"))
        ligne = QHBoxLayout()
        ligne.setSpacing(Layout.CARD_GAP)
        nom = QLineEdit()
        nom.setPlaceholderText("Saisir le nom et les prénoms")
        carnet = QLineEdit("043")
        carnet.setReadOnly(True)
        montant = QLineEdit("-5")
        statut = QComboBox()
        statut.addItems(["Actif", "Décédé"])
        champs = (FormField("Nom complet", nom, required=True),
                  FormField("N° de carnet", carnet, hint="Attribué automatiquement"),
                  FormField("Montant (FCFA)", montant, required=True),
                  FormField("Statut", statut))
        champs[2].set_error("Le montant doit être un entier positif.")
        for champ in champs:
            ligne.addWidget(champ, 1)
        carte.body.addLayout(ligne)
        return carte

    def _carte_messages(self) -> Card:
        carte = Card()
        carte.body.addWidget(make_label("Bandeaux et messages temporaires", "card-title"))
        carte.body.addWidget(Banner("info", "Un paiement partiel est imputé au décès le plus ancien. Les membres exemptés sont grisés."))
        carte.body.addWidget(Banner("warning", "La restauration remplace toutes les données actuelles. Une copie de sécurité est créée avant."))
        carte.body.addWidget(Banner("danger", "Le numéro de carnet 009 est déjà attribué."))
        ligne = QHBoxLayout()
        ligne.setSpacing(Layout.CARD_GAP)
        succes = AppButton("Message de succès", Variant.SECONDARY)
        succes.clicked.connect(lambda: self.toast.popup("success", "Versement enregistré", "18 000 FCFA imputés sur Avril et Mai."))
        erreur = AppButton("Message d'erreur", Variant.SECONDARY)
        erreur.clicked.connect(lambda: self.toast.popup("danger", "Enregistrement impossible", "Le numéro de carnet existe déjà."))
        alerte = AppButton("Avertissement", Variant.SECONDARY)
        alerte.clicked.connect(lambda: self.toast.popup("warning", "Sauvegarde ancienne", "La dernière date de plus de 7 jours."))
        role = AppButton("Basculer vue secrétaire", Variant.PRIMARY, "user")
        role.clicked.connect(self._bascule_role)
        for bouton in (succes, erreur, alerte, role):
            ligne.addWidget(bouton)
        ligne.addStretch(1)
        carte.body.addLayout(ligne)
        return carte