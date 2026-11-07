"""Page Sauvegardes : état du stockage local et historique des copies disponibles."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHeaderView, QHBoxLayout, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from app.ui.ports_backups import BackupsData
from app.ui.theme.tokens import Layout
from app.ui.widgets.banner import Banner
from app.ui.widgets.base import make_label
from app.ui.widgets.button import AppButton, Variant
from app.ui.widgets.card import Card, StatCard
from app.ui.widgets.page_header import PageHeader


class BackupsView(QWidget):
    backup_requested = Signal()
    restore_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        corps = QVBoxLayout(self)
        corps.setContentsMargins(*Layout.PAGE_MARGINS)
        corps.setSpacing(Layout.SECTION_GAP)

        self.header = PageHeader("Sauvegardes et restauration", "")
        self.backup_button = AppButton("Sauvegarder maintenant", Variant.PRIMARY, "database")
        self.header.add_action(self.backup_button)
        corps.addWidget(self.header)

        self.notice = Banner("info", "Sauvegarde locale · copie automatique à la fermeture du logiciel")
        corps.addWidget(self.notice)

        resume = QHBoxLayout()
        resume.setSpacing(Layout.CARD_GAP)
        self.backup_count = StatCard()
        self.last_backup = StatCard()
        self.last_size = StatCard()
        for card in (self.backup_count, self.last_backup, self.last_size):
            resume.addWidget(card, 1)
        corps.addLayout(resume)

        historique = Card(padding=0, spacing=0)
        historique.body.addWidget(self._label("Historique des sauvegardes"), 0)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(("DATE ET HEURE", "TYPE", "FICHIER", "TAILLE", "STATUT", "ACTION"))
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setMinimumHeight(300)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        historique.body.addWidget(self.table)
        self.empty_history = make_label("Aucune sauvegarde disponible.", "caption")
        self.empty_history.setAlignment(Qt.AlignmentFlag.AlignCenter)
        historique.body.addWidget(self.empty_history)
        corps.addWidget(historique)
        corps.addWidget(Banner(
            "warning",
            "Restaurer remplace les données actuelles. Une copie de sécurité est créée automatiquement avant le remplacement.",
        ))
        corps.addStretch(1)
        self.backup_button.clicked.connect(self.backup_requested.emit)

    @staticmethod
    def _label(text: str):
        from app.ui.widgets.base import make_label

        return make_label(text, "card-title")

    def set_model(self, model: BackupsData) -> None:
        self.header.set_subtitle("Sauvegardes locales de l’association")
        backups = model.backups
        latest = backups[0] if backups else None
        self.backup_count.set_content("Sauvegardes disponibles", str(len(backups)), "Stockage local")
        self.last_backup.set_content("Dernière sauvegarde", latest.date if latest else "Aucune", "Date du fichier")
        self.last_size.set_content("Taille de la base", model.database_size, "Base actuelle")
        self.empty_history.setVisible(not backups)
        self.table.setRowCount(len(backups))
        for row, backup in enumerate(backups):
            for column, value in enumerate((backup.date, backup.kind, backup.filename,
                                            backup.size, backup.status)):
                self.table.setItem(row, column, QTableWidgetItem(value))
            action = AppButton("Restaurer", Variant.SECONDARY)
            action.setEnabled(backup.status == "Vérifiée")
            action.setToolTip("Restaurer cette sauvegarde vérifiée")
            action.clicked.connect(lambda _=False, name=backup.filename: self.restore_requested.emit(name))
            self.table.setCellWidget(row, 5, action)
