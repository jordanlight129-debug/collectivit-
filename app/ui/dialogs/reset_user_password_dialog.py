"""Dialogue de réinitialisation du mot de passe d'un compte."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from app.security.passwords import PasswordPolicyError, validate_policy
from app.ui.theme.tokens import Layout
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant


class ResetUserPasswordDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Réinitialiser le mot de passe")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(make_label("Nouveau mot de passe", "card-title"))
        layout.addWidget(make_label("8 caractères minimum, avec au moins une lettre et un chiffre.",
                                    "caption", wrap=True))

        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_field.setPlaceholderText("Nouveau mot de passe")
        layout.addWidget(self.password_field)
        self.confirmation_field = QLineEdit()
        self.confirmation_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirmation_field.setPlaceholderText("Confirmer le mot de passe")
        layout.addWidget(self.confirmation_field)

        self.error_label = make_label("", "field-error", wrap=True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = AppButton("Annuler", Variant.SECONDARY)
        cancel.clicked.connect(self.reject)
        self.reset_button = AppButton("Réinitialiser", Variant.PRIMARY)
        self.reset_button.clicked.connect(self._submit)
        actions.addWidget(cancel)
        actions.addWidget(self.reset_button)
        layout.addLayout(actions)

    def password(self) -> str:
        return self.password_field.text()

    def _submit(self) -> None:
        password = self.password_field.text()
        if password != self.confirmation_field.text():
            self._show_error("Les deux mots de passe ne correspondent pas.")
            return
        try:
            validate_policy(password)
        except PasswordPolicyError as error:
            self._show_error(str(error))
            return
        self.accept()

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()