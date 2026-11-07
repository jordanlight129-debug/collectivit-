"""Dialogue de règlement des cotisations funéraires et parallèles."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QWidget

from app.ui.ports_fines import FineRecord
from app.ui.widgets.dialog import FormDialog
from app.ui.widgets.form import DateInput, NumberInput, ReadOnlyInput, SelectInput, TextInput


class CollectPaymentDialog(FormDialog):
    def __init__(self, *, member_id: int, member_name: str, rubrique: str,
                 rubrique_label: str, cotisation_id: int | None = None,
                 cotisation_name: str = "", parent: QWidget | None = None) -> None:
        super().__init__("Enregistrer un versement", parent)
        self.member_id = member_id
        self.rubrique = rubrique
        self.cotisation_id = cotisation_id

        member = ReadOnlyInput("Membre")
        member.set_value(member_name)
        self.add_field(member)
        category = ReadOnlyInput("Rubrique")
        category.set_value(rubrique_label)
        self.add_field(category)
        if cotisation_id is not None:
            subscription = ReadOnlyInput("Cotisation parallèle")
            subscription.set_value(cotisation_name)
            self.add_field(subscription)

        self.amount_field = NumberInput("Montant reçu (FCFA)", required=True, min_value=1)
        self.add_field(self.amount_field)
        self.mode_field = SelectInput("Imputation", [
            ("Cotisation en cours puis arriérés", "global"),
            ("Arriérés seulement", "arrieres"),
        ], required=True)
        self.add_field(self.mode_field)
        self.date_field = DateInput("Date du paiement", required=True)
        self.date_field.set_value(date.today().strftime("%Y-%m-%d"))
        self.add_field(self.date_field)
        self.note_field = TextInput("Note", placeholder="Facultatif")
        self.add_field(self.note_field)

    def get_data(self) -> dict[str, object]:
        return {
            "membre_id": self.member_id,
            "rubrique": self.rubrique,
            "montant": self.amount_field.value(),
            "mode": self.mode_field.value(),
            "date_versement": self.date_field.value(),
            "note": self.note_field.value(),
            "cotisation_id": self.cotisation_id,
        }


class CollectFineDialog(FormDialog):
    def __init__(self, fine: FineRecord, parent: QWidget | None = None) -> None:
        super().__init__("Encaisser une amende", parent)
        self.fine_id = fine.id
        for label, value in (("Membre", f"{fine.member_name} · carnet {fine.member_carnet}"),
                             ("Libellé", fine.label),
                             ("Reste à encaisser", f"{fine.remaining:,} FCFA".replace(",", " "))):
            field = ReadOnlyInput(label)
            field.set_value(value)
            self.add_field(field)

        self.amount_field = NumberInput("Montant reçu (FCFA)", required=True, min_value=1,
                                        max_value=max(fine.remaining, 1))
        self.add_field(self.amount_field)
        self.date_field = DateInput("Date de paiement", required=True)
        self.date_field.set_value(date.today().strftime("%Y-%m-%d"))
        self.add_field(self.date_field)

    def get_data(self) -> dict[str, int | str]:
        return {
            "amende_id": self.fine_id,
            "montant": int(self.amount_field.value()),
            "date_encaissement": self.date_field.value(),
        }