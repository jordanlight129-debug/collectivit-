"""Dialogue de création de cotisation parallèle."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget

from app.ui.widgets.dialog import FormDialog
from app.ui.widgets.form import TextInput, NumberInput, DateInput


class AddParallelDialog(FormDialog):
    """Dialogue pour créer une cotisation parallèle."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Nouvelle cotisation parallèle", parent)

        # Nom de la cotisation
        self.name_field = TextInput("Nom de la cotisation", required=True,
                                    placeholder="Ex: Fête de fin d'année")
        self.add_field(self.name_field)

        # Montant pour les hommes
        self.amount_man_field = NumberInput("Montant hommes (FCFA)", required=True, min_value=0)
        self.add_field(self.amount_man_field)

        # Montant pour les femmes
        self.amount_woman_field = NumberInput("Montant femmes (FCFA)", required=True, min_value=0)
        self.add_field(self.amount_woman_field)

        # Date de début
        self.start_field = DateInput("Date de début", required=True)
        self.start_field.set_value(date.today().strftime("%Y-%m-%d"))
        self.add_field(self.start_field)

        # Date de fin
        self.end_field = DateInput("Date de fin", required=True)
        self.end_field.set_value(date.today().strftime("%Y-%m-%d"))
        self.add_field(self.end_field)

    def get_data(self) -> dict:
        return {
            "nom": self.name_field.value(),
            "montant_homme": int(self.amount_man_field.value()),
            "montant_femme": int(self.amount_woman_field.value()),
            "date_debut": self.start_field.value(),
            "date_fin": self.end_field.value(),
        }
