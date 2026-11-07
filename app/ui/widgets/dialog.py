"""Boîtes de dialogue modales pour les formulaires."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from app.ui.format import format_fcfa
from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant


class FormDialog(QDialog):
    """Dialogue de formulaire générique."""
    
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*Layout.PAGE_MARGINS)
        layout.setSpacing(Layout.SECTION_GAP)
        
        # Container pour le formulaire
        self.form_container = QWidget()
        self.form_layout = QVBoxLayout(self.form_container)
        self.form_layout.setSpacing(12)
        layout.addWidget(self.form_container)
        
        # Boutons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        self._fields = []
    
    def add_field(self, field: QWidget) -> None:
        """Ajoute un champ au formulaire."""
        self.form_layout.addWidget(field)
        self._fields.append(field)
    
    def validate(self) -> bool:
        """Valide tous les champs requis."""
        for field in self._fields:
            if hasattr(field, 'is_valid') and not field.is_valid():
                if hasattr(field, 'mark_invalid'):
                    field.mark_invalid(True)
                return False
        return True
    
    def _field_label(self, field: QWidget) -> str:
        label_widget = getattr(field, "label_widget", None)
        text = label_widget.text() if label_widget is not None else ""
        return text.replace(" *", "") if text else ""

    def _field_value(self, field: QWidget) -> str:
        if hasattr(field, "value"):
            value = field.value()
            if isinstance(value, (int, float)):
                return str(value)
            if isinstance(value, str):
                return value.strip()

        widget = getattr(field, "input_widget", None)
        if widget is None:
            return ""
        if hasattr(widget, "currentText"):
            return widget.currentText().strip()
        if hasattr(widget, "text"):
            return widget.text().strip()
        return ""

    def preview_text(self) -> str:
        """Génère le résumé lisible des données saisies."""
        lines = []
        for field in self._fields:
            label = self._field_label(field)
            value = self._field_value(field)
            if not label or not value:
                continue
            if "montant" in label.lower():
                try:
                    value = format_fcfa(int(value)).replace("\u00a0", " ")
                except (TypeError, ValueError):
                    pass
            lines.append(f"{label} : {value}")
        return "\n".join(lines) if lines else "Aucune donnée saisie."

    def accept(self) -> None:
        """Accepte le dialogue après validation avec aperçu avant enregistrement."""
        if not self.validate():
            return

        preview = self.preview_text()
        if preview == "Aucune donnée saisie.":
            super().accept()
            return

        reply = QMessageBox.question(
            self,
            "Prévisualisation avant enregistrement",
            f"Vérifiez les informations avant d'enregistrer :\n\n{preview}",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            super().accept()
