"""Dialogue de modification de membre."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget

from app.ui.widgets.dialog import FormDialog
from app.ui.widgets.form import TextInput, SelectInput, DateInput, ReadOnlyInput


class EditMemberDialog(FormDialog):
    """Dialogue pour modifier un membre existant."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Modifier le membre", parent)

        # Numéro de carnet (lecture seule, non modifiable)
        self.carnet_field = ReadOnlyInput("N° de carnet")
        self.add_field(self.carnet_field)

        # Nom complet
        self.name_field = TextInput("Nom complet", required=True, placeholder="Ex: Komlan Akakpo")
        self.add_field(self.name_field)

        # Sexe (affiché mais non modifiable)
        self.sex_display = ReadOnlyInput("Sexe")
        self.add_field(self.sex_display)

        # Date d'adhésion
        self.adhesion_field = DateInput("Date d'adhésion", required=True)
        self.add_field(self.adhesion_field)

    def set_data(self, carnet: str, nom: str, sexe: str, date_adhesion: str) -> None:
        """Pré-remplit le formulaire avec les données existantes."""
        self.carnet_field.set_value(carnet)
        self.name_field.set_value(nom)
        sexe_label = "Masculin" if sexe == "M" else "Féminin"
        self.sex_display.set_value(sexe_label)
        self.adhesion_field.set_value(date_adhesion)

    def get_data(self) -> dict:
        """Retourne les données du formulaire."""
        return {
            "nom": self.name_field.value(),
            "date_adhesion": self.adhesion_field.value(),
        }
