"""Page Journal d’audit : consultation et recherche des actions enregistrées."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QHeaderView, QHBoxLayout, QLineEdit, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from app.ui.ports_audit import AuditData, AuditLog
from app.ui.theme.tokens import Layout
from app.ui.widgets.banner import Banner
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card
from app.ui.widgets.page_header import PageHeader
from app.ui.widgets.base import make_label


class AuditView(QWidget):
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Journal d’audit", "")
        self.export_button = AppButton("Exporter en PDF", Variant.SECONDARY)
        self.export_button.clicked.connect(self.export_requested.emit)
        self.header.add_action(self.export_button)
        corps.addWidget(self.header)

        self.notice = Banner(
            "warning",
            "Lecture seule : le journal ne peut être ni modifié ni supprimé depuis l’application.",
        )
        corps.addWidget(self.notice)

        filtre = Card(padding=14, spacing=0)
        ligne = QHBoxLayout()
        ligne.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher une action ou un membre…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(Layout.INPUT_HEIGHT)
        ligne.addWidget(self.search, 1)
        self.user_filter = QComboBox()
        self.user_filter.setFixedHeight(Layout.INPUT_HEIGHT)
        self.user_filter.setMinimumWidth(190)
        ligne.addWidget(self.user_filter)
        filtre.body.addLayout(ligne)
        corps.addWidget(filtre)

        tableau = Card(padding=0, spacing=0)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(("DATE ET HEURE", "UTILISATEUR", "ACTION", "OBJET", "DÉTAIL"))
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.setMinimumHeight(340)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        tableau.body.addWidget(self.table)
        pied = QHBoxLayout()
        self.counter = make_label("", "caption")
        pied.addWidget(self.counter)
        pied.addStretch(1)
        tableau.body.addLayout(pied)
        corps.addWidget(tableau)
        corps.addStretch(1)

        self._logs: tuple[AuditLog, ...] = ()
        self.search.textChanged.connect(self._apply_filters)
        self.user_filter.currentIndexChanged.connect(self._apply_filters)

    def set_model(self, model: AuditData) -> None:
        self.header.set_subtitle("Historique des actions réalisées dans le logiciel · consultation uniquement")
        self._logs = model.logs
        self.user_filter.blockSignals(True)
        self.user_filter.clear()
        self.user_filter.addItem("Utilisateur : Tous", "")
        for user in sorted({log.user for log in model.logs}):
            self.user_filter.addItem(user, user)
        self.user_filter.blockSignals(False)
        self._apply_filters()

    def _apply_filters(self) -> None:
        query = self.search.text().strip().casefold()
        user = str(self.user_filter.currentData() or "")
        logs = [log for log in self._logs if (not user or log.user == user)
                and (not query or query in " ".join((log.date, log.user, log.action,
                                                       log.entity, log.details)).casefold())]
        self.table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            for column, value in enumerate((log.date, log.user, log.action, log.entity, log.details)):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, log.id)
                self.table.setItem(row, column, item)
        self.counter.setText(f"Affichage {len(logs)} sur {len(self._logs)} événements · lecture seule")