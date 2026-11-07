"""Présentateur de la page Amendes."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject

from app.ui.ports_fines import FinesData, FinesPort
from app.ui.presenters.fines_model import FinesQuery, build_view_model
from app.ui.views.fines import FinesView


class FinesPresenter(QObject):
    def __init__(self, view: FinesView, port: FinesPort, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        self._port = port
        self._data: FinesData | None = None
        self._query = FinesQuery()
        view.search_changed.connect(lambda t: self._changer(search=t, page=1))
        view.status_changed.connect(lambda status: self._changer(status=status, page=1))
        view.sort_requested.connect(self._trier)
        view.page_requested.connect(lambda p: self._changer(page=p))

    def show_exercise(self, exercise_label: str) -> None:
        self._data = self._port.load(exercise_label)
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
