"""Dialogue de modification de dépense."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget

from app.ui.widgets.dialog import FormDialog
from app.ui.widgets.form import TextInput, NumberInput, DateInput


class EditExpenseDialog(FormDialog):
    """Dialogue pour modifier une dépense existante."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Modifier la dépense", parent)

        # Libellé
        self.label_field = TextInput("Libellé", required=True, placeholder="Ex: Achat de chaises")
        self.add_field(self.label_field)

        # Bénéficiaire
        self.beneficiary_field = TextInput("Bénéficiaire", placeholder="Optionnel")
        self.add_field(self.beneficiary_field)

        # Montant prévu
        self.planned_field = NumberInput("Montant prévu (FCFA)", required=True, min_value=0)
        self.add_field(self.planned_field)

        # Montant dépensé
        self.spent_field = NumberInput("Montant dépensé (FCFA)", required=True, min_value=0)
        self.add_field(self.spent_field)

        # Date
        self.date_field = DateInput("Date de la dépense", required=True)
        self.add_field(self.date_field)

    def set_data(self, libelle: str, beneficiaire: str | None, montant_prevu: int,
                 montant_depense: int, date_depense: str) -> None:
        """Pré-remplit le formulaire avec les données existantes."""
        self.label_field.set_value(libelle)
        self.beneficiary_field.set_value(beneficiaire or "")
        self.planned_field.set_value(str(montant_prevu))
        self.spent_field.set_value(str(montant_depense))
        self.date_field.set_value(date_depense)

    def get_data(self) -> dict:
        return {
            "libelle": self.label_field.value(),
            "beneficiaire": self.beneficiary_field.value() or None,
            "montant_prevu": int(self.planned_field.value()),
            "montant_depense": int(self.spent_field.value()),
            "date_depense": self.date_field.value(),
        }
