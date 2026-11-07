"""Page Paramètres : aperçu des réglages actuellement fournis par le modèle."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QFormLayout, QGridLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from app.security.session import Role
from app.ui.ports_settings import ManagedUser, SettingsData
from app.ui.theme.tokens import Layout
from app.ui.widgets.banner import Banner
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card
from app.ui.widgets.page_header import PageHeader

_LABELS = {
    "association_name": "Nom de l’association",
    "brand_initials": "Initiales de la marque",
    "default_tarif_homme": "Hommes (FCFA)",
    "default_tarif_femme": "Femmes (FCFA)",
}


class SettingsView(QWidget):
    save_requested = Signal(int, int, int, int)
    create_secretary_requested = Signal(str, str, str)
    set_user_active_requested = Signal(int, bool)
    reset_user_password_requested = Signal(int)
    user_input_error = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Paramètres", "")
        corps.addWidget(self.header)

        corps.addWidget(Banner("info", "Montants configurables, utilisateurs et rôles · réservé à l’administrateur"))

        grille = QGridLayout()
        grille.setSpacing(Layout.CARD_GAP)
        self.monthly_values = self._form_card("Cotisation mensuelle selon le sexe", (
            ("monthly_men", _LABELS["default_tarif_homme"]),
            ("monthly_women", _LABELS["default_tarif_femme"]),
        ))
        self.funeral_values = self._form_card("Cotisation funéraire selon le sexe", (
            ("funeral_men", "Hommes (FCFA)"),
            ("funeral_women", "Femmes (FCFA)"),
        ))
        self.identity_values = self._identity_card()
        grille.addWidget(self.monthly_values[0], 0, 0)
        grille.addWidget(self.identity_values[0], 0, 1)
        grille.addWidget(self.funeral_values[0], 1, 0)

        calendrier = Card(padding=18, spacing=8)
        calendrier.body.addWidget(make_label("Exercice comptable", "card-title"))
        calendrier.body.addWidget(make_label("Septembre → août", "grid-total"))
        calendrier.body.addWidget(make_label("Période annuelle de l’association", "caption"))
        grille.addWidget(calendrier, 1, 1)

        comptes = self._user_management_card()
        grille.addWidget(comptes, 2, 0, 1, 2)
        corps.addLayout(grille)

        autres = Card(padding=16, spacing=8)
        autres.body.addWidget(make_label("Autres paramètres", "card-title"))
        self.other_parameters = QFormLayout()
        self.other_parameters.setHorizontalSpacing(20)
        self.other_parameters.setVerticalSpacing(10)
        autres.body.addLayout(self.other_parameters)
        corps.addWidget(autres)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.save_button = AppButton("Enregistrer les modifications", Variant.PRIMARY)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(lambda: self.save_requested.emit(
            self.monthly_values[1]["monthly_men"].value(),
            self.monthly_values[1]["monthly_women"].value(),
            self.funeral_values[1]["funeral_men"].value(),
            self.funeral_values[1]["funeral_women"].value(),
        ))
        for controls in (self.monthly_values[1], self.funeral_values[1]):
            for control in controls.values():
                control.valueChanged.connect(lambda _value: self.save_button.setEnabled(True))
        actions.addWidget(self.save_button)
        corps.addLayout(actions)
        corps.addStretch(1)

    def _user_management_card(self) -> Card:
        card = Card(padding=18, spacing=10)
        card.body.addWidget(make_label("Utilisateurs et rôles", "card-title"))
        card.body.addWidget(make_label(
            "Les secrétaires peuvent enregistrer les opérations autorisées. "
            "Les suppressions, les paramètres et le journal d’audit restent réservés à l’administrateur.",
            "caption", wrap=True))

        self.active_secretaries_label = make_label("", "caption")
        card.body.addWidget(self.active_secretaries_label)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)
        self.secretary_name = QLineEdit()
        self.secretary_name.setMaxLength(100)
        self.secretary_name.setPlaceholderText("Nom complet")
        self.secretary_identifier = QLineEdit()
        self.secretary_identifier.setMaxLength(30)
        self.secretary_identifier.setPlaceholderText("Identifiant (ex. kawa.dovi)")
        self.secretary_password = QLineEdit()
        self.secretary_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.secretary_password.setPlaceholderText("Au moins 8 caractères, lettre et chiffre")
        self.secretary_password_confirmation = QLineEdit()
        self.secretary_password_confirmation.setEchoMode(QLineEdit.EchoMode.Password)
        self.secretary_password_confirmation.setPlaceholderText("Confirmer le mot de passe")
        for column, (label, field) in enumerate((
            ("Nom complet", self.secretary_name),
            ("Identifiant", self.secretary_identifier),
            ("Mot de passe initial", self.secretary_password),
            ("Confirmation", self.secretary_password_confirmation),
        )):
            row = column // 2 * 2
            grid_column = column % 2
            form.addWidget(make_label(label, "field-label"), row, grid_column)
            form.addWidget(field, row + 1, grid_column)
        card.body.addLayout(form)

        self.create_secretary_button = AppButton("Créer un compte secrétaire", Variant.SECONDARY, "plus")
        self.create_secretary_button.clicked.connect(self._submit_secretary)
        card.body.addWidget(self.create_secretary_button, 0, Qt.AlignmentFlag.AlignRight)

        self.users_table = QTableWidget(0, 5)
        self.users_table.setHorizontalHeaderLabels(("NOM COMPLET", "IDENTIFIANT", "RÔLE", "STATUT", "ACTIONS"))
        self.users_table.verticalHeader().hide()
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.users_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.users_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.users_table.setMinimumHeight(190)
        headers = self.users_table.horizontalHeader()
        for column in range(4):
            headers.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        headers.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        card.body.addWidget(self.users_table)
        self.users_empty = make_label("Aucun compte utilisateur.", "caption")
        card.body.addWidget(self.users_empty)
        return card

    def _submit_secretary(self) -> None:
        password = self.secretary_password.text()
        if password != self.secretary_password_confirmation.text():
            self.user_input_error.emit("Les deux mots de passe ne correspondent pas.")
            return
        self.create_secretary_requested.emit(
            self.secretary_identifier.text(), self.secretary_name.text(), password)

    def clear_secretary_form(self) -> None:
        for field in (self.secretary_name, self.secretary_identifier,
                      self.secretary_password, self.secretary_password_confirmation):
            field.clear()

    def _fill_users(self, users: tuple[ManagedUser, ...]) -> None:
        self.users_table.setRowCount(len(users))
        active_secretaries = sum(user.role is Role.SECRETAIRE and user.actif for user in users)
        self.active_secretaries_label.setText(f"Secrétaires actifs : {active_secretaries}/3")
        can_create = active_secretaries < 3
        self.create_secretary_button.setEnabled(can_create)
        self.create_secretary_button.setToolTip(
            "" if can_create else "Désactive un compte secrétaire avant d’en créer un autre.")
        self.users_empty.setVisible(not users)
        self.users_table.setVisible(bool(users))

        for row, user in enumerate(users):
            values = (user.nom_complet, user.identifiant, user.role.label,
                      "Actif" if user.actif else "Désactivé")
            for column, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.users_table.setItem(row, column, item)

            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            reset = AppButton("Réinitialiser le mot de passe", Variant.LINK)
            reset.clicked.connect(lambda _=False, user_id=user.id:
                                  self.reset_user_password_requested.emit(user_id))
            action_layout.addWidget(reset)
            if user.role is Role.SECRETAIRE:
                toggle_text = "Désactiver" if user.actif else "Activer"
                toggle = AppButton(toggle_text, Variant.LINK)
                toggle.clicked.connect(lambda _=False, user_id=user.id, actif=not user.actif:
                                       self.set_user_active_requested.emit(user_id, actif))
                action_layout.addWidget(toggle)
            self.users_table.setCellWidget(row, 4, actions)

    @staticmethod
    def _form_card(title: str, fields: tuple[tuple[str, str], ...]) -> tuple[Card, dict[str, QSpinBox]]:
        card = Card(padding=18, spacing=10)
        card.body.addWidget(make_label(title, "card-title"))
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        controls: dict[str, QSpinBox] = {}
        for key, label in fields:
            value = QSpinBox()
            value.setRange(0, 100_000_000)
            value.setSuffix(" FCFA")
            value.setFixedHeight(Layout.INPUT_HEIGHT)
            form.addRow(QLabel(label), value)
            controls[key] = value
        card.body.addLayout(form)
        return card, controls

    @staticmethod
    def _identity_card() -> tuple[Card, dict[str, QLineEdit]]:
        card = Card(padding=18, spacing=10)
        card.body.addWidget(make_label("Identité de l’association", "card-title"))
        form = QFormLayout()
        controls: dict[str, QLineEdit] = {}
        for key in ("association_name", "brand_initials"):
            value = QLineEdit()
            value.setReadOnly(True)
            form.addRow(QLabel(_LABELS[key]), value)
            controls[key] = value
        card.body.addLayout(form)
        return card, controls

    def set_model(self, model: SettingsData) -> None:
        self.header.set_subtitle("Montants configurables, utilisateurs et rôles · réservé à l’administrateur")
        values = {parameter.key: parameter.value for parameter in model.parameters}
        self._fill_users(model.users)
        self.identity_values[1]["association_name"].setText(values.get("association_name", ""))
        self.identity_values[1]["brand_initials"].setText(values.get("brand_initials", ""))
        for controls, names in (
            (self.monthly_values[1], ("monthly_men", "monthly_women")),
            (self.funeral_values[1], ("funeral_men", "funeral_women")),
        ):
            for name in names:
                controls[name].blockSignals(True)
            controls[names[0]].setValue(model.monthly_men if names[0] == "monthly_men" else model.funeral_men)
            controls[names[1]].setValue(model.monthly_women if names[1] == "monthly_women" else model.funeral_women)
            for name in names:
                controls[name].blockSignals(False)
                controls[name].setEnabled(model.is_open)
        self.save_button.setEnabled(model.is_open)
        self.save_button.setToolTip("" if model.is_open else "Un exercice clôturé ne peut plus être modifié.")

        while self.other_parameters.count():
            item = self.other_parameters.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        known = set(_LABELS)
        for parameter in model.parameters:
            if parameter.key in known:
                continue
            label = parameter.description or parameter.key.replace("_", " ").capitalize()
            value = QLineEdit(parameter.value)
            value.setReadOnly(True)
            self.other_parameters.addRow(QLabel(label), value)
