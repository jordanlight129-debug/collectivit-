"""Dialogue d'amende."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget

from app.ui.widgets.dialog import FormDialog
from app.ui.widgets.form import TextInput, NumberInput, DateInput


class AddFineDialog(FormDialog):
    """Dialogue pour enregistrer une amende."""

    def __init__(self, member_name: str, member_id: int, parent: QWidget | None = None) -> None:
        super().__init__(f"Amende - {member_name}", parent)
        self.member_id = member_id

        # Libellé de l'amende
        self.label_field = TextInput("Motif de l'amende", required=True,
                                     placeholder="Ex: Retard à une réunion")
        self.add_field(self.label_field)

        # Montant attendu
        self.amount_field = NumberInput("Montant de l'amende (FCFA)", required=True, min_value=100)
        self.add_field(self.amount_field)

        # Montant collecté
        self.collected_field = NumberInput("Montant payé (FCFA)", required=True, min_value=0)
        self.collected_field.set_value("0")
        self.add_field(self.collected_field)

        # Date de l'amende
        self.date_field = DateInput("Date de l'amende", required=True)
        self.date_field.set_value(date.today().strftime("%Y-%m-%d"))
        self.add_field(self.date_field)

    def get_data(self) -> dict:
        return {
            "membre_id": self.member_id,
            "libelle": self.label_field.value(),
            "montant_attendu": int(self.amount_field.value()),
            "montant_collecte": int(self.collected_field.value()),
            "date_amende": self.date_field.value(),
        }
