"""Dialogue d'amende."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget

from app.ui.ports_members import MemberInfo, MemberStatus
from app.ui.widgets.dialog import FormDialog
from app.ui.widgets.form import TextInput, NumberInput, DateInput, SelectInput


class AddFineDialog(FormDialog):
    """Dialogue pour enregistrer une amende."""

    def __init__(self, members: tuple[MemberInfo, ...], parent: QWidget | None = None) -> None:
        super().__init__("Nouvelle amende", parent)

        options = [("Sélectionner un membre", "")]
        options.extend((f"{member.name} · carnet {member.carnet}", str(member.id))
                       for member in members if member.status == MemberStatus.ACTIF)
        self.member_field = SelectInput("Membre", options, required=True)
        self.add_field(self.member_field)

        self.label_field = TextInput("Libellé de l’amende", required=True,
                                     placeholder="Ex: Retard à une réunion")
        self.add_field(self.label_field)

        self.amount_field = NumberInput("Montant attendu (FCFA)", required=True, min_value=1)
        self.add_field(self.amount_field)

        self.date_field = DateInput("Date", required=True)
        self.date_field.set_value(date.today().strftime("%Y-%m-%d"))
        self.add_field(self.date_field)

    def get_data(self) -> dict:
        label = self.label_field.value()
        return {
            "membre_id": int(self.member_field.value()),
            "nom": label,
            "libelle": label,
            "montant_attendu": int(self.amount_field.value()),
            "date_amende": self.date_field.value(),
        }
