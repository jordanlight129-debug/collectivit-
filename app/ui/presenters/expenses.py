"""Présentateur de la page Dépenses."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, Signal

from app.ui.ports_expenses import ExpensesData, ExpensesLoadError, ExpensesPort
from app.ui.presenters.expenses_model import ExpensesQuery, build_view_model
from app.ui.views.expenses import ExpensesView


class ExpensesPresenter(QObject):
    load_failed = Signal(str)

    def __init__(self, view: ExpensesView, port: ExpensesPort, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        self._port = port
        self._data: ExpensesData | None = None
        self._query = ExpensesQuery()
        view.search_changed.connect(lambda t: self._changer(search=t, page=1))
        view.sort_requested.connect(self._trier)
        view.page_requested.connect(lambda p: self._changer(page=p))

    def show_exercise(self, exercise_label: str) -> None:
        try:
            self._data = self._port.load(exercise_label)
        except ExpensesLoadError as exc:
            self._data = None
            self._view.set_error(str(exc))
            self.load_failed.emit(str(exc))
            return
        self._changer(page=1)

    def _trier(self, cle: str) -> None:
        if cle == self._query.sort_key:
            self._changer(ascending=not self._query.ascending, page=1)
        else:
            self._changer(sort_key=cle, ascending=True, page=1)

    def _changer(self, **champs) -> None:
        self._query = self._query._replace(**champs)
        if self._data is None:
            return
        modele = build_view_model(self._data, self._query)
        self._query = self._query._replace(page=modele.page if hasattr(modele, 'page') else self._query.page)
        self._view.set_model(modele)
