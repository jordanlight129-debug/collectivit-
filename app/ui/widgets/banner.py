"""Bandeau d'information et message temporaire (toast)."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui import icons
from app.ui.theme import apply_shadow
from app.ui.theme.tokens import Color, Shadow
from app.ui.widgets.base import make_label, repolish_tree, set_property

_BANNER_ICONS = {
    "info": ("info", Color.NAVY_700),
    "warning": ("alert", Color.WARNING_600),
    "danger": ("alert", Color.DANGER_600),
}


class Banner(QFrame):
    """Bandeau inline : `info` (bleu), `warning` (orange) ou `danger` (rouge)."""

    def __init__(self, kind: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Banner")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        self._icon = QLabel()
        self._text = make_label(text, None, wrap=True)
        layout.addWidget(self._icon)
        layout.addWidget(self._text, 1)
        self.set_kind(kind)

    @property
    def kind(self) -> str:
        return str(self.property("kind"))

    def set_kind(self, kind: str) -> None:
        if kind not in _BANNER_ICONS:
            raise ValueError(f"Genre de bandeau inconnu : {kind}")
        nom, couleur = _BANNER_ICONS[kind]
        self._icon.setPixmap(icons.icon(nom, couleur, 18).pixmap(18, 18))
        set_property(self, "kind", kind, tree=True)

    def set_text(self, text: str) -> None:
        self._text.setText(text)


_TOAST_ICONS = {
    "success": ("check", Color.SUCCESS_600),
    "danger": ("alert", Color.DANGER_600),
    "warning": ("alert", Color.WARNING_600),
    "info": ("info", Color.NAVY_700),
}
# « error » est accepté comme synonyme de « danger » (utilisé dans main_window)
_TOAST_ALIAS = {"error": "danger"}
_TOAST_WIDTH = 460
_TOAST_MARGIN = 24


class Toast(QFrame):
    """Message temporaire en bas à droite de la fenêtre parente (succès, erreur, avertissement, info)."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setFixedWidth(_TOAST_WIDTH)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 20, 14)
        layout.setSpacing(12)
        self._icon = QLabel()
        self._icon.setFixedSize(20, 20)
        colonne = QVBoxLayout()
        colonne.setSpacing(2)
        self._title = make_label("", "toast-title", wrap=True)
        self._text = make_label("", "toast-text", wrap=True)
        colonne.addWidget(self._title)
        colonne.addWidget(self._text)
        layout.addWidget(self._icon)
        layout.addLayout(colonne, 1)
        apply_shadow(self, Shadow.POPOVER)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.kind = "success"
        self.hide()

    @property
    def title_text(self) -> str:
        return self._title.text()

    def popup(self, kind: str, title: str, text: str = "", msecs: int | None = None) -> None:
        """Affiche le message puis le masque seul après `msecs` ms (clic pour le fermer avant)."""
        kind = _TOAST_ALIAS.get(kind, kind)
        if kind not in _TOAST_ICONS:
            raise ValueError(f"Genre de message inconnu : {kind}")
        parent = self.parentWidget()
        if parent is not None:
            largeur_disponible = max(parent.width() - 2 * _TOAST_MARGIN, 1)
            self.setFixedWidth(min(_TOAST_WIDTH, largeur_disponible))
        self.kind = kind
        nom, couleur = _TOAST_ICONS[kind]
        self._icon.setPixmap(icons.icon(nom, couleur, 20).pixmap(20, 20))
        self._title.setText(title)
        self._text.setText(text)
        self._text.setVisible(bool(text))
        set_property(self, "kind", kind, tree=True)
        self.layout().activate()
        self.adjustSize()
        self._place()
        self.raise_()
        self.show()
        if msecs is None:
            msecs = min(9000, max(3500, 1800 + 32 * len(title + text)))
        self._timer.start(msecs)

    def _place(self) -> None:
        parent = self.parentWidget()
        x = max(parent.width() - self.width() - _TOAST_MARGIN, 0)
        y = max(parent.height() - self.height() - _TOAST_MARGIN, 0)
        self.move(x, y)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._timer.stop()
        self.hide()