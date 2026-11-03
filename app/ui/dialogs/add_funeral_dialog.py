"""Dialogue de collecte décès."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget

from app.ui.widgets.dialog import FormDialog
from app.ui.widgets.form import TextInput, NumberInput, DateInput, SelectInput


class AddFuneralDialog(FormDialog):
    """Dialogue pour enregistrer une collecte décès."""

    def __init__(self, member_name: str, member_id: int, parent: QWidget | None = None) -> None:
        super().__init__(f"Collecte décès - {member_name}", parent)
        self.member_id = member_id

        # Type de parenté
        self.type_field = SelectInput("Type de parenté", [
            ("Père/Mère", "parent"),
            ("Conjoint(e)", "conjoint"),
            ("Enfant", "enfant"),
            ("Frère/Sœur", "frere_soeur"),
            ("Autre", "autre"),
        ], required=True)
        self.add_field(self.type_field)

        # Montant collecté
        self.amount_field = NumberInput("Montant collecté (FCFA)", required=True, min_value=0)
        self.add_field(self.amount_field)

        # Date de la collecte
        self.date_field = DateInput("Date de la collecte", required=True)
        self.date_field.set_value(date.today().strftime("%Y-%m-%d"))
        self.add_field(self.date_field)

        # Note
        self.note_field = TextInput("Note", placeholder="Optionnel")
        self.add_field(self.note_field)

    def get_data(self) -> dict:
        return {
            "membre_id": self.member_id,
            "type_parente": self.type_field.value(),
            "montant": int(self.amount_field.value()),
            "date_collecte": self.date_field.value(),
            "note": self.note_field.value(),
        }
