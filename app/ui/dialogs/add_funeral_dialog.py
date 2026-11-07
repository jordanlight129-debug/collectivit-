"""Dialogue de collecte décès."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QCheckBox, QWidget

from app.models.deces import BEAU_PARENT, MEMBRE, AUTRE, PARENT
from app.ui.ports_members import MemberInfo, MemberStatus
from app.ui.widgets.dialog import FormDialog
from app.ui.widgets.form import TextInput, DateInput, SelectInput


class AddFuneralDialog(FormDialog):
    """Dialogue pour enregistrer une collecte décès."""

    def __init__(self, members: tuple[MemberInfo, ...], parent: QWidget | None = None) -> None:
        super().__init__("Nouvelle collecte funéraire", parent)

        self.type_field = SelectInput("Type de décès", [
            ("Sélectionner", ""),
            ("Parent", PARENT),
            ("Membre de l’association", MEMBRE),
            ("Beau-parent", BEAU_PARENT),
            ("Autre", AUTRE),
        ], required=True)
        self.add_field(self.type_field)

        self.name_field = TextInput("Nom du défunt", placeholder="Ex. Mme Kuwonu")
        self.add_field(self.name_field)

        options = [("Sélectionner un membre", "")]
        options.extend((f"{member.name} · carnet {member.carnet}", str(member.id))
                       for member in members)
        self.deceased_member_field = SelectInput("Membre décédé", options)
        self.add_field(self.deceased_member_field)

        active_members = [member for member in members if member.status == MemberStatus.ACTIF]
        bereaved_options = [("Aucun membre endeuillé", "")]
        bereaved_options.extend((f"{member.name} · carnet {member.carnet}", str(member.id))
                                for member in active_members)
        self.bereaved_member_field = SelectInput("Membre endeuillé (optionnel)", bereaved_options)
        self.add_field(self.bereaved_member_field)

        self.exempt_checkbox = QCheckBox("Exempter le membre endeuillé de cette collecte")
        self.add_field(self.exempt_checkbox)

        self.date_field = DateInput("Date du décès", required=True)
        self.date_field.set_value(date.today().strftime("%Y-%m-%d"))
        self.add_field(self.date_field)

    def get_data(self) -> dict:
        death_type = self.type_field.value()
        bereaved_id = self.bereaved_member_field.value()
        return {
            "nom_defunt": self.name_field.value(),
            "type_deces": death_type,
            "date_deces": self.date_field.value(),
            "membre_defunt_id": (int(self.deceased_member_field.value())
                                  if death_type == MEMBRE and self.deceased_member_field.value() else None),
            "membre_endeuille_id": int(bereaved_id) if bereaved_id else None,
            "exempter_endeuille": self.exempt_checkbox.isChecked(),
        }
