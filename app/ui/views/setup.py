"""Écran de premier démarrage : création du compte administrateur."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.form import TextInput, PasswordInput
from app.ui.widgets.card import Card


class SetupView(QWidget):
    """Écran de configuration initiale : création du compte administrateur."""

    submitted = Signal(str, str, str)  # identifiant, mot_de_passe, confirmation

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        # Titre et description
        corps.addStretch(2)
        titre = make_label("Premier démarrage", "hero-title")
        titre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corps.addWidget(titre)

        description = make_label(
            "Bienvenue ! Créez votre compte administrateur pour commencer à utiliser l'application.",
            "caption"
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        corps.addWidget(description)
        corps.addStretch(1)

        # Formulaire
        carte = Card(padding=24, spacing=16)
        self.identifiant_field = TextInput("Identifiant", required=True, placeholder="Ex: admin")
        carte.body.addWidget(self.identifiant_field)

        self.password_field = PasswordInput(
            "Mot de passe",
            required=True,
            placeholder="Au moins 8 caractères, une lettre et un chiffre"
        )
        carte.body.addWidget(self.password_field)

        self.confirmation_field = PasswordInput(
            "Confirmer le mot de passe",
            required=True,
            placeholder="Resaissez le mot de passe"
        )
        carte.body.addWidget(self.confirmation_field)

        corps.addWidget(carte)
        corps.addStretch(1)

        # Bouton de validation
        bouton_layout = QHBoxLayout()
        bouton_layout.addStretch(1)
        self.submit_button = AppButton("Créer le compte", Variant.PRIMARY, "check")
        self.submit_button.setFixedWidth(200)
        bouton_layout.addWidget(self.submit_button)
        bouton_layout.addStretch(1)
        corps.addLayout(bouton_layout)
        corps.addStretch(2)

        self.submit_button.clicked.connect(self._submit)

    def _submit(self) -> None:
        identifiant = self.identifiant_field.value()
        password = self.password_field.value()
        confirmation = self.confirmation_field.value()
        self.submitted.emit(identifiant, password, confirmation)

    def reset(self) -> None:
        """Réinitialise le formulaire."""
        self.identifiant_field.set_value("")
        self.password_field.set_value("")
        self.confirmation_field.set_value("")
        self.identifiant_field.clear_error()
        self.password_field.clear_error()
        self.confirmation_field.clear_error()

    def set_error(self, field: str, message: str) -> None:
        """Affiche une erreur sur un champ."""
        if field == "identifiant":
            self.identifiant_field.set_error(message)
        elif field == "password":
            self.password_field.set_error(message)
        elif field == "confirmation":
            self.confirmation_field.set_error(message)

    def clear_errors(self) -> None:
        """Efface toutes les erreurs."""
        self.identifiant_field.clear_error()
        self.password_field.clear_error()
        self.confirmation_field.clear_error()
