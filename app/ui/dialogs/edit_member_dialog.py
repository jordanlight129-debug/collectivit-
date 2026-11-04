"""Dialogue de modification de membre."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget

from app.ui.widgets.dialog import FormDialog
from app.ui.widgets.form import TextInput, SelectInput, DateInput


class EditMemberDialog(FormDialog):
    """Dialogue pour modifier un membre existant."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Modifier le membre", parent)

        # Nom complet
        self.name_field = TextInput("Nom complet", required=True, placeholder="Ex: Komlan Akakpo")
        self.add_field(self.name_field)

        # Sexe (non modifiable après création selon le cahier des charges)
        self.sex_field = SelectInput("Sexe", [("Masculin", "M"), ("Féminin", "F")], required=True)
        self.add_field(self.sex_field)

        # Date d'adhésion
        self.adhesion_field = DateInput("Date d'adhésion", required=True)
        self.add_field(self.adhesion_field)

    def set_data(self, nom: str, sexe: str, date_adhesion: str) -> None:
        """Pré-remplit le formulaire avec les données existantes."""
        self.name_field.set_value(nom)
        self.sex_field.set_value(sexe)
        self.adhesion_field.set_value(date_adhesion)

    def get_data(self) -> dict:
        """Retourne les données du formulaire."""
        return {
            "nom": self.name_field.value(),
            "sexe": self.sex_field.value(),
            "date_adhesion": self.adhesion_field.value(),
        }
