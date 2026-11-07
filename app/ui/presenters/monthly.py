"""Présentateur de la page Cotisations mensuelles : garde l'état et met la vue à jour."""
from __future__ import annotations

from PySide6.QtCore import QObject

from app.ui.ports_monthly import MonthlyData, MonthlyPort
from app.ui.presenters.monthly_model import MonthlyQuery, build_view_model
from app.ui.views.monthly import MonthlyView


class MonthlyPresenter(QObject):
    def __init__(self, view: MonthlyView, port: MonthlyPort, parent: QObject | None = None) -> None:
        super().__init__(parent or view)
        self._view = view
        self._port = port
        self._data: MonthlyData | None = None
        self._label = ""
        self._query = MonthlyQuery()
        view.search_changed.connect(lambda t: self._changer(search=t, page=1))
        view.status_changed.connect(lambda s: self._changer(status=s, page=1))
        view.sex_changed.connect(lambda s: self._changer(sex=s, page=1))
        view.sort_requested.connect(self._trier)
        view.page_requested.connect(lambda p: self._changer(page=p))

    def show_exercise(self, exercise_label: str) -> None:
        """Charge l'exercice et revient à la première page (filtres conservés)."""
        self._label = exercise_label
        self._data = self._port.load(exercise_label)
        self._changer(page=1)

    def refresh(self) -> None:
        """Recharge les données (après un versement) en gardant la page et les filtres."""
        if not self._label:
            return
        self._data = self._port.load(self._label)
        self._changer()

    def members_for_dialog(self) -> list[tuple[str, str]]:
        """Liste (carnet, nom) de tous les membres de l'exercice, pour la boîte de versements."""
        if self._data is None:
            return []
        return [(m.carnet, m.name) for m in self._data.members]

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
        if modele.page != self._query.page:
            self._query = self._query._replace(page=modele.page)
        self._view.set_model(modele)