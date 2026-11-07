"""Écran de premier démarrage : création de l'administrateur initial."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.ui import icons
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.banner import Banner
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card
from app.ui.widgets.field import FormField


def _etiquette(texte: str, nom_objet: str, *, wrap: bool = False) -> QLabel:
    etiquette = QLabel(texte)
    etiquette.setObjectName(nom_objet)
    etiquette.setWordWrap(wrap)
    return etiquette


class SetupView(QWidget):
    """Écran de premier démarrage : création de l'administrateur initial."""

    submitted = Signal(str, str, str)  # identifiant, nom_complet, mot_de_passe

    def __init__(self, *, brand_name: str, brand_initials: str, tagline: str,
                 features: tuple[str, ...], footer: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SetupView")
        racine = QHBoxLayout(self)
        racine.setContentsMargins(0, 0, 0, 0)
        racine.setSpacing(0)
        racine.addWidget(self._panneau_marque(brand_name, brand_initials, tagline, features, footer), 44)
        racine.addWidget(self._panneau_formulaire(), 56)

    def _panneau_marque(self, nom: str, initiales: str, accroche: str, atouts: tuple[str, ...],
                        pied: str) -> QFrame:
        panneau = QFrame()
        panneau.setObjectName("LoginBrand")
        panneau.setMinimumWidth(Layout.LOGIN_BRAND_WIDTH * 2 // 3)
        colonne = QVBoxLayout(panneau)
        colonne.setContentsMargins(56, 56, 56, 40)
        colonne.setSpacing(16)
        marque = _etiquette(initiales, "LoginBrandMark")
        marque.setFixedSize(48, 48)
        marque.setAlignment(Qt.AlignmentFlag.AlignCenter)
        colonne.addWidget(marque, 0, Qt.AlignmentFlag.AlignLeft)
        colonne.addSpacing(24)
        colonne.addWidget(_etiquette(nom, "LoginBrandName", wrap=True))
        colonne.addWidget(_etiquette(accroche, "LoginBrandTagline", wrap=True))
        colonne.addSpacing(16)
        for texte in atouts:
            ligne = QHBoxLayout()
            ligne.setSpacing(10)
            coche = QLabel()
            coche.setFixedSize(18, 18)
            coche.setPixmap(icons.icon("check", Color.NAVY_100, 18).pixmap(18, 18))
            ligne.addWidget(coche, 0, Qt.AlignmentFlag.AlignTop)
            ligne.addWidget(_etiquette(texte, "LoginFeature", wrap=True), 1)
            colonne.addLayout(ligne)
        colonne.addStretch(1)
        colonne.addWidget(_etiquette(pied, "LoginBrandFooter"))
        return panneau

    def _panneau_formulaire(self) -> QWidget:
        panneau = QWidget()
        panneau.setObjectName("LoginPanel")
        vertical = QVBoxLayout(panneau)
        vertical.setContentsMargins(32, 32, 32, 32)
        vertical.addStretch(1)
        centre = QHBoxLayout()
        centre.addStretch(1)
        centre.addWidget(self._carte())
        centre.addStretch(1)
        vertical.addLayout(centre)
        vertical.addStretch(1)
        return panneau

    def _carte(self) -> Card:
        carte = Card(padding=32, spacing=16)
        carte.setFixedWidth(Layout.LOGIN_CARD_WIDTH)
        carte.body.addWidget(_etiquette("Premier démarrage", "LoginTitle"))
        carte.body.addWidget(make_label("Créez le compte administrateur initial pour commencer.",
                                        "page-subtitle", wrap=True))
        self.banner = Banner("danger", "")
        self.banner.hide()
        carte.body.addWidget(self.banner)

        self.identifiant = QLineEdit()
        self.identifiant.setPlaceholderText("ex. admin")
        self.identifiant.setMaxLength(64)
        self.nom_complet = QLineEdit()
        self.nom_complet.setPlaceholderText("ex. Administrateur")
        self.nom_complet.setMaxLength(100)
        self.mot_de_passe = QLineEdit()
        self.mot_de_passe.setEchoMode(QLineEdit.EchoMode.Password)
        self.mot_de_passe.setPlaceholderText("Mot de passe (min. 8 caractères)")
        self.mot_de_passe_confirmation = QLineEdit()
        self.mot_de_passe_confirmation.setEchoMode(QLineEdit.EchoMode.Password)
        self.mot_de_passe_confirmation.setPlaceholderText("Confirmer le mot de passe")

        self.field_identifiant = FormField("Identifiant", self.identifiant, required=True)
        self.field_nom = FormField("Nom complet", self.nom_complet, required=True)
        self.field_password = FormField("Mot de passe", self.mot_de_passe, required=True)
        self.field_password_confirm = FormField("Confirmation", self.mot_de_passe_confirmation, required=True)

        carte.body.addWidget(self.field_identifiant)
        carte.body.addWidget(self.field_nom)
        carte.body.addWidget(self.field_password)
        carte.body.addWidget(self.field_password_confirm)

        self.create_button = AppButton("Créer l'administrateur", Variant.PRIMARY)
        carte.body.addWidget(self.create_button)
        carte.body.addWidget(_etiquette("L'identifiant et le mot de passe seront requis pour vous connecter.",
                                        "LoginFootnote", wrap=True))

        self.identifiant.returnPressed.connect(self.nom_complet.setFocus)
        self.nom_complet.returnPressed.connect(self.mot_de_passe.setFocus)
        self.mot_de_passe.returnPressed.connect(self.mot_de_passe_confirmation.setFocus)
        self.mot_de_passe_confirmation.returnPressed.connect(self._emettre)
        self.create_button.clicked.connect(self._emettre)
        self.setTabOrder(self.identifiant, self.nom_complet)
        self.setTabOrder(self.nom_complet, self.mot_de_passe)
        self.setTabOrder(self.mot_de_passe, self.mot_de_passe_confirmation)
        self.setTabOrder(self.mot_de_passe_confirmation, self.create_button)
        return carte

    def _emettre(self) -> None:
        self.submitted.emit(*self.values())

    def values(self) -> tuple[str, str, str]:
        return self.identifiant.text(), self.nom_complet.text(), self.mot_de_passe.text()

    def focus_identifier(self) -> None:
        self.identifiant.setFocus()

    def set_busy(self, busy: bool) -> None:
        self.create_button.setEnabled(not busy)
        self.create_button.setText("Création…" if busy else "Créer l'administrateur")

    def set_inputs_enabled(self, enabled: bool) -> None:
        for controle in (self.identifiant, self.nom_complet, self.mot_de_passe,
                         self.mot_de_passe_confirmation, self.create_button):
            controle.setEnabled(enabled)

    def clear_passwords(self) -> None:
        self.mot_de_passe.clear()
        self.mot_de_passe_confirmation.clear()

    def clear_errors(self) -> None:
        self.banner.hide()
        self.field_identifiant.set_error(None)
        self.field_nom.set_error(None)
        self.field_password.set_error(None)
        self.field_password_confirm.set_error(None)

    def show_field_errors(self, identifiant: str | None, nom: str | None, password: str | None,
                          confirmation: str | None) -> None:
        """Messages sous les champs manquants."""
        self.clear_errors()
        self.field_identifiant.set_error(identifiant)
        self.field_nom.set_error(nom)
        self.field_password.set_error(password)
        self.field_password_confirm.set_error(confirmation)
        if identifiant:
            self.identifiant.setFocus()
        elif nom:
            self.nom_complet.setFocus()
        elif password:
            self.mot_de_passe.setFocus()
        else:
            self.mot_de_passe_confirmation.setFocus()

    def show_error(self, message: str) -> None:
        """Erreur de création : bandeau rouge."""
        self.clear_errors()
        self._show_banner("danger", message)
        self.clear_passwords()
        self.mot_de_passe.setFocus()

    def _show_banner(self, kind: str, message: str) -> None:
        self.banner.set_kind(kind)
        self.banner.set_text(message)
        self.banner.show()
