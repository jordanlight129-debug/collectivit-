"""Présentateur de la page Cotisations parallèles."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject

from app.ui.ports_parallel import ParallelData, ParallelPort
from app.ui.presenters.parallel_model import ParallelQuery, build_view_model
from app.ui.views.parallel import ParallelView


class ParallelPresenter(QObject):
    def __init__(self, view: ParallelView, port: ParallelPort, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        self._port = port
        self._data: ParallelData | None = None
        self._query = ParallelQuery()
        view.search_changed.connect(lambda t: self._changer(search=t, page=1))
        view.sort_requested.connect(self._trier)
        view.page_requested.connect(lambda p: self._changer(page=p))
        view.subscription_action_requested.connect(
            lambda subscription_id: self._changer(selected_subscription_id=subscription_id))

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
