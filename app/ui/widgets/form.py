"""Widgets de formulaire pour les dialogues de saisie."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDateEdit, QFormLayout, QFrame, QLabel,
                               QLineEdit, QSpinBox, QTextEdit, QWidget)

from app.ui.theme.tokens import Color, Layout
from app.ui.widgets.base import make_label


class FormField(QFrame):
    """Champ de formulaire avec label et input."""
    
    value_changed = Signal()
    
    def __init__(self, label: str, required: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FormField")
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.label_widget = make_label(label + (" *" if required else ""), "form-label")
        layout.addRow(self.label_widget)
        
        self._input = None
        self._required = required
    
    def set_input(self, widget: QWidget) -> None:
        """Définit le widget d'input."""
        if self._input:
            self.layout().removeWidget(self._input)
        self.layout().addRow(widget)
        self._input = widget
        
        # Connecter le signal de changement si disponible
        if hasattr(widget, 'textChanged'):
         widget.textChanged.connect(lambda *_: self.value_changed.emit())
        elif hasattr(widget, 'currentIndexChanged'):
         widget.currentIndexChanged.connect(lambda *_: self.value_changed.emit())
        elif hasattr(widget, 'dateChanged'):
          widget.dateChanged.connect(lambda *_: self.value_changed.emit())
        elif hasattr(widget, 'valueChanged'):
          widget.valueChanged.connect(lambda *_: self.value_changed.emit())
    
    def input_widget(self) -> QWidget | None:
        return self._input
    
    def value(self) -> str:
        """Retourne la valeur du champ."""
        if self._input is None:
            return ""
        
        if isinstance(self._input, QLineEdit):
            return self._input.text().strip()
        elif isinstance(self._input, QComboBox):
            return self._input.currentData()
        elif isinstance(self._input, QDateEdit):
            return self._input.date().toString("yyyy-MM-dd")
        elif isinstance(self._input, QSpinBox):
            return str(self._input.value())
        elif isinstance(self._input, QTextEdit):
            return self._input.toPlainText().strip()
        return ""
    
    def set_value(self, value: str) -> None:
        """Définit la valeur du champ."""
        if self._input is None:
            return
        
        if isinstance(self._input, QLineEdit):
            self._input.setText(value)
        elif isinstance(self._input, QComboBox):
            index = self._input.findData(value)
            if index >= 0:
                self._input.setCurrentIndex(index)
        elif isinstance(self._input, QDateEdit):
            from datetime import datetime
            try:
                date = datetime.strptime(value, "%Y-%m-%d")
                self._input.setDate(date)
            except Exception:
                pass
        elif isinstance(self._input, QSpinBox):
            try:
                self._input.setValue(int(value))
            except Exception:
                pass
        elif isinstance(self._input, QTextEdit):
            self._input.setPlainText(value)
    
    def is_valid(self) -> bool:
        """Vérifie si le champ est valide."""
        if not self._required:
            return True
        return bool(self.value())
    
    def mark_invalid(self, invalid: bool = True) -> None:
        """Marque le champ comme invalide."""
        if invalid:
            self.label_widget.setStyleSheet(f"color: {Color.DANGER_600};")
        else:
            self.label_widget.setStyleSheet(f"color: {Color.GRAY_900};")


class TextInput(FormField):
    """Champ de texte."""
    
    def __init__(self, label: str, required: bool = False, placeholder: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(label, required, parent)
        self.input_widget = QLineEdit()
        self.input_widget.setPlaceholderText(placeholder)
        self.input_widget.setFixedHeight(Layout.INPUT_HEIGHT)
        self.set_input(self.input_widget)


class NumberInput(FormField):
    """Champ numérique."""
    
    def __init__(self, label: str, required: bool = False, min_value: int = 0,
                 max_value: int = 999999, parent: QWidget | None = None) -> None:
        super().__init__(label, required, parent)
        self.input_widget = QSpinBox()
        self.input_widget.setMinimum(min_value)
        self.input_widget.setMaximum(max_value)
        self.input_widget.setFixedHeight(Layout.INPUT_HEIGHT)
        self.set_input(self.input_widget)


class DateInput(FormField):
    """Champ de date."""
    
    def __init__(self, label: str, required: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(label, required, parent)
        self.input_widget = QDateEdit()
        self.input_widget.setCalendarPopup(True)
        self.input_widget.setDisplayFormat("dd/MM/yyyy")
        self.input_widget.setFixedHeight(Layout.INPUT_HEIGHT)
        self.set_input(self.input_widget)


class SelectInput(FormField):
    """Champ de sélection."""
    
    def __init__(self, label: str, options: list[tuple[str, str]], required: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(label, required, parent)
        self.input_widget = QComboBox()
        for text, value in options:
            self.input_widget.addItem(text, value)
        self.input_widget.setFixedHeight(Layout.INPUT_HEIGHT)
        self.set_input(self.input_widget)


class TextArea(FormField):
    """Zone de texte multiligne."""

    def __init__(self, label: str, required: bool = False, placeholder: str = "",
                 max_length: int = 500, parent: QWidget | None = None) -> None:
        super().__init__(label, required, parent)
        self.input_widget = QTextEdit()
        self.input_widget.setPlaceholderText(placeholder)
        self.input_widget.setMaximumHeight(100)
        self.set_input(self.input_widget)


class ReadOnlyInput(FormField):
    """Champ en lecture seule (non modifiable)."""

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(label, required=False, parent=parent)
        self.input_widget = QLineEdit()
        self.input_widget.setReadOnly(True)
        self.input_widget.setFixedHeight(Layout.INPUT_HEIGHT)
        self.input_widget.setStyleSheet(f"background: {Color.GRAY_100};")
        self.set_input(self.input_widget)
