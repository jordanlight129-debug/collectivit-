"""Fenêtre de connexion : panneau de marque à gauche, formulaire à droite.
États : initial, champs manquants, identifiants refusés, compte verrouillé."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app.ui import icons
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.banner import Banner
from app.ui.widgets.base import make_label, set_property
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card
from app.ui.widgets.field import FormField


def _etiquette(texte: str, nom_objet: str, *, wrap: bool = False) -> QLabel:
    etiquette = QLabel(texte)
    etiquette.setObjectName(nom_objet)
    etiquette.setWordWrap(wrap)
    return etiquette


class LoginView(QWidget):
    """Affichage seul : émet `submitted(identifiant, mot de passe)` ; le présentateur décide."""

    submitted = Signal(str, str)

    def __init__(self, *, brand_name: str, brand_initials: str, tagline: str,
                 features: tuple[str, ...], footer: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LoginView")
        self.last_message = ""
        racine = QHBoxLayout(self)
        racine.setContentsMargins(0, 0, 0, 0)
        racine.setSpacing(0)
        racine.addWidget(self._panneau_marque(brand_name, brand_initials, tagline, features, footer), 44)
        racine.addWidget(self._panneau_formulaire(), 56)

    # ---------- construction ----------
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
        carte.body.addWidget(_etiquette("Connexion", "LoginTitle"))
        carte.body.addWidget(make_label("Saisissez vos identifiants pour accéder au logiciel.",
                                        "page-subtitle", wrap=True))
        self.banner = Banner("danger", "")
        self.banner.hide()
        carte.body.addWidget(self.banner)

        self.identifiant = QLineEdit()
        self.identifiant.setPlaceholderText("ex. yawa.dovi")
        self.identifiant.setMaxLength(64)
        self.mot_de_passe = QLineEdit()
        self.mot_de_passe.setEchoMode(QLineEdit.EchoMode.Password)
        self.mot_de_passe.setPlaceholderText("Votre mot de passe")

        # Champ identifiant
        self.field_identifiant = FormField("Identifiant", self.identifiant)
        carte.body.addWidget(self.field_identifiant)

        # Conteneur du mot de passe avec le bouton de visibilité
        password_container = QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(8)
        password_layout.addWidget(self.mot_de_passe, 1)

        # Bouton pour afficher/masquer le mot de passe
        self.password_toggle = QPushButton()
        self.password_toggle.setFixedSize(24, 24)
        self.password_toggle.setFlat(True)
        self.password_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_password_toggle_icon()
        self.password_toggle.clicked.connect(self._toggle_password_visibility)
        password_layout.addWidget(self.password_toggle, 0)

        # Champ mot de passe (étiquette + conteneur)
        self.field_password_container = QWidget()
        password_field_layout = QVBoxLayout(self.field_password_container)
        password_field_layout.setContentsMargins(0, 0, 0, 0)
        password_field_layout.setSpacing(6)
        password_label = make_label("Mot de passe", "field-label")
        password_field_layout.addWidget(password_label)
        password_field_layout.addWidget(password_container)
        carte.body.addWidget(self.field_password_container)

        self.connect_button = AppButton("Se connecter", Variant.PRIMARY)
        carte.body.addWidget(self.connect_button)
        carte.body.addWidget(_etiquette("Mot de passe oublié ? Contactez l’administrateur.",
                                        "LoginFootnote", wrap=True))

        self.identifiant.returnPressed.connect(self.mot_de_passe.setFocus)
        self.mot_de_passe.returnPressed.connect(self._emettre)
        self.connect_button.clicked.connect(self._emettre)
        self.setTabOrder(self.identifiant, self.mot_de_passe)
        self.setTabOrder(self.mot_de_passe, self.connect_button)
        return carte

    def _emettre(self) -> None:
        self.submitted.emit(*self.values())

    def _toggle_password_visibility(self) -> None:
        """Bascule l'affichage du mot de passe."""
        if self.mot_de_passe.echoMode() == QLineEdit.EchoMode.Password:
            self.mot_de_passe.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.mot_de_passe.setEchoMode(QLineEdit.EchoMode.Password)
        self._update_password_toggle_icon()

    def _update_password_toggle_icon(self) -> None:
        """Met à jour l'icône du bouton de visibilité."""
        if self.mot_de_passe.echoMode() == QLineEdit.EchoMode.Password:
            # Icône « œil fermé » (mot de passe masqué)
            icon = icons.icon("eye_off", Color.GRAY_500, 16)
        else:
            # Icône « œil ouvert » (mot de passe visible)
            icon = icons.icon("eye", Color.GRAY_500, 16)
        self.password_toggle.setIcon(icon)

    # ---------- API pour le présentateur ----------
    def values(self) -> tuple[str, str]:
        return self.identifiant.text(), self.mot_de_passe.text()

    def focus_identifier(self) -> None:
        self.identifiant.setFocus()

    def set_busy(self, busy: bool) -> None:
        self.connect_button.setEnabled(not busy)
        self.connect_button.setText("Connexion…" if busy else "Se connecter")

    def set_inputs_enabled(self, enabled: bool) -> None:
        for controle in (self.identifiant, self.mot_de_passe, self.connect_button):
            controle.setEnabled(enabled)

    def clear_password(self) -> None:
        self.mot_de_passe.clear()

    def clear_errors(self) -> None:
        self.banner.hide()
        self.last_message = ""
        self.field_identifiant.set_error(None)
        # Retire aussi le marquage rouge du champ mot de passe
        set_property(self.mot_de_passe, "error", False)

    def show_field_errors(self, identifiant: str | None, password: str | None) -> None:
        """Messages sous les champs manquants."""
        self.clear_errors()
        self.field_identifiant.set_error(identifiant)
        # Pour le mot de passe, l'erreur est affichée dans le bandeau
        if password:
            self._show_banner("danger", password)
        (self.identifiant if identifiant else self.mot_de_passe).setFocus()

    def show_refused(self, message: str) -> None:
        """Identifiants refusés : bandeau rouge, champs en rouge, mot de passe effacé."""
        self.clear_errors()
        self._show_banner("danger", message)
        self.field_identifiant.mark_invalid(True)
        set_property(self.mot_de_passe, "error", True)
        self.clear_password()
        self.mot_de_passe.setFocus()

    def show_locked(self, message: str) -> None:
        """Compte verrouillé : bandeau orange, saisie désactivée."""
        self.clear_errors()
        self._show_banner("warning", message)
        self.set_inputs_enabled(False)
        self.clear_password()

    def reset(self) -> None:
        """Retour à l'état initial (au démarrage et après une déconnexion)."""
        self.clear_errors()
        self.identifiant.clear()
        self.clear_password()
        self.set_inputs_enabled(True)
        self.set_busy(False)

    def _show_banner(self, kind: str, message: str) -> None:
        self.last_message = message
        self.banner.set_kind(kind)
        self.banner.set_text(message)
        self.banner.show()