"""Dialogue de changement de mot de passe par son titulaire."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from app.security.passwords import PasswordPolicyError, validate_policy
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant


class ChangePasswordDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Changer mon mot de passe")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(make_label("Sécurité du compte", "card-title"))
        layout.addWidget(make_label(
            "Saisis ton mot de passe actuel, puis un nouveau mot de passe d’au moins "
            "8 caractères contenant une lettre et un chiffre.",
            "caption", wrap=True))

        self.current_password_field = QLineEdit()
        self.current_password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_field.setPlaceholderText("Mot de passe actuel")
        layout.addWidget(self.current_password_field)
        self.new_password_field = QLineEdit()
        self.new_password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_field.setPlaceholderText("Nouveau mot de passe")
        layout.addWidget(self.new_password_field)
        self.confirmation_field = QLineEdit()
        self.confirmation_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirmation_field.setPlaceholderText("Confirmer le nouveau mot de passe")
        layout.addWidget(self.confirmation_field)

        self.error_label = make_label("", "field-error", wrap=True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = AppButton("Annuler", Variant.SECONDARY)
        cancel.clicked.connect(self.reject)
        self.submit_button = AppButton("Mettre à jour", Variant.PRIMARY)
        self.submit_button.clicked.connect(self._submit)
        actions.addWidget(cancel)
        actions.addWidget(self.submit_button)
        layout.addLayout(actions)

    def passwords(self) -> tuple[str, str]:
        return self.current_password_field.text(), self.new_password_field.text()

    def _submit(self) -> None:
        current_password, new_password = self.passwords()
        if not current_password:
            self._show_error("Saisis ton mot de passe actuel.")
            return
        if new_password != self.confirmation_field.text():
            self._show_error("Les deux nouveaux mots de passe ne correspondent pas.")
            return
        try:
            validate_policy(new_password)
        except PasswordPolicyError as error:
            self._show_error(str(error))
            return
        self.accept()

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()