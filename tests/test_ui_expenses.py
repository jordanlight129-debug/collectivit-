import os
import sqlite3
import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.security.session import CurrentUser, Role, Session
from app.ui.adapters.expenses_adapter import ExpensesAdapter
from app.ui.main_window import MainWindow
from app.ui.mock.auth import MockAuth
from app.ui.ports_expenses import ExpenseRecord, ExpensesData, ExpensesLoadError
from app.ui.presenters.expenses import ExpensesPresenter
from app.ui.presenters.expenses_model import ExpensesQuery, build_view_model
from app.ui.theme import apply_theme
from app.ui.views.expenses import ExpensesView


def _data(count=3, is_open=True):
    records = tuple(
        ExpenseRecord(
            id=index,
            date=(date(2026, 1, 1) + timedelta(days=index - 1)).isoformat(),
            label=f"Dépense {index:02d}",
            beneficiary=f"Bénéficiaire {index:02d}",
            amount_planned=index * 100,
            amount_spent=index * 80,
        )
        for index in range(1, count + 1)
    )
    return ExpensesData(
        exercise_label="2025-2026",
        is_open=is_open,
        records=records,
        total_planned=sum(record.amount_planned for record in records),
        total_spent=sum(record.amount_spent for record in records),
    )


class ExpensesModelTest(unittest.TestCase):
    def test_tous_les_entetes_trient_les_depenses(self):
        data = _data()
        expected = {
            "date": (1, 2, 3),
            "label": (1, 2, 3),
            "beneficiary": (1, 2, 3),
            "planned": (1, 2, 3),
            "spent": (1, 2, 3),
        }
        for sort_key, ids in expected.items():
            with self.subTest(sort_key=sort_key):
                model = build_view_model(data, ExpensesQuery(sort_key=sort_key, ascending=True))
                self.assertEqual(tuple(row.id for row in model.rows), ids)

    def test_pagination_limite_etat_cloture(self):
        model = build_view_model(_data(45, is_open=False), ExpensesQuery(page=3))
        self.assertEqual((model.page, model.page_count, len(model.rows)), (3, 3, 5))
        self.assertTrue(model.read_only)
        clamped = build_view_model(_data(45), ExpensesQuery(page=9))
        self.assertEqual((clamped.page, clamped.counter), (3, "Page 3/3 · 45 résultats"))


class ExpensesViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)

    def test_pager_et_action_ligne(self):
        view = ExpensesView()
        self.addCleanup(view.close)
        view.set_can_delete(True)
        view.set_model(build_view_model(_data(45), ExpensesQuery(page=2)))
        pages = []
        view.page_requested.connect(pages.append)
        view.previous_button.click()
        view.next_button.click()
        self.assertEqual(pages, [1, 3])

        action_view = ExpensesView()
        self.addCleanup(action_view.close)
        action_view.set_can_delete(True)
        action_view.set_model(build_view_model(_data(1), ExpensesQuery()))
        actions = []
        action_view.expense_action_requested.connect(actions.append)
        action_view._grid.itemAtPosition(2, 5).widget().click()
        self.assertEqual(actions, [1])

    def test_exercice_cloture_desactive_ajout_et_suppression(self):
        view = ExpensesView()
        self.addCleanup(view.close)
        view.set_can_delete(True)
        view.set_model(build_view_model(_data(1, is_open=False), ExpensesQuery()))
        action = view._grid.itemAtPosition(2, 5).widget()
        self.assertFalse(view.add_button.isEnabled())
        self.assertFalse(action.isEnabled())


class ExpensesAdapterTest(unittest.TestCase):
    def setUp(self):
        self.connection = Mock()
        self.session = Session()
        self.session.login(CurrentUser(7, "admin", "Administrateur", Role.ADMINISTRATEUR))
        self.adapter = ExpensesAdapter()
        self.adapter._session = self.session

    def test_creation_transmet_le_montant_prevu_et_la_session(self):
        depense = SimpleNamespace(id=31)
        with patch("app.ui.adapters.expenses_adapter.get_connection", return_value=self.connection), \
             patch("app.ui.adapters.expenses_adapter.exercices.get_by_libelle",
                   return_value=SimpleNamespace(id=2)), \
             patch("app.ui.adapters.expenses_adapter.enregistrer_depense", return_value=depense) as save:
            result = self.adapter.add_expense(
                "2025-2026", "Papier", "Boutique", 10000, 7500, date.today().isoformat())

        self.assertEqual(result, 31)
        save.assert_called_once_with(
            self.connection, self.session, "Papier", 7500, "Boutique", 10000,
            date.today(), today=date.today())
        self.connection.close.assert_called_once()

    def test_erreur_sql_creation_est_remplacee_par_un_message_clair(self):
        with patch("app.ui.adapters.expenses_adapter.get_connection", return_value=self.connection), \
             patch("app.ui.adapters.expenses_adapter.exercices.get_by_libelle",
                   return_value=SimpleNamespace(id=2)), \
             patch("app.ui.adapters.expenses_adapter.enregistrer_depense",
                   side_effect=sqlite3.OperationalError("SQLITE_CONSTRAINT_PRIVATE")):
            with self.assertRaisesRegex(RuntimeError, "Impossible d’enregistrer la dépense") as raised:
                self.adapter.add_expense(
                    "2025-2026", "Papier", "Boutique", 10000, 7500, date.today().isoformat())

        self.assertNotIn("SQLITE_CONSTRAINT_PRIVATE", str(raised.exception))
        self.connection.close.assert_called_once()

    def test_suppression_transmet_la_session_au_service(self):
        with patch("app.ui.adapters.expenses_adapter.get_connection", return_value=self.connection), \
             patch("app.ui.adapters.expenses_adapter.supprimer_depense") as delete:
            self.adapter.delete_expense(31)

        delete.assert_called_once_with(self.connection, self.session, 31)
        self.connection.close.assert_called_once()

    def test_erreur_de_chargement_ne_devient_pas_une_liste_vide(self):
        with patch("app.ui.adapters.expenses_adapter.get_connection", return_value=self.connection), \
             patch("app.ui.adapters.expenses_adapter.exercices.get_by_libelle",
                   side_effect=sqlite3.OperationalError("table missing")):
            with self.assertRaisesRegex(RuntimeError, "Impossible de charger les dépenses"):
                self.adapter.load("2025-2026")

        self.connection.close.assert_called_once()

    def test_chargement_convertit_la_date_en_chaine_iso(self):
        expense = SimpleNamespace(
            id=9,
            date_depense=date(2026, 6, 16),
            libelle="Achat",
            beneficiaire=None,
            montant_prevu=100,
            montant_depense=80,
        )
        with patch("app.ui.adapters.expenses_adapter.get_connection", return_value=self.connection), \
             patch("app.ui.adapters.expenses_adapter.exercices.get_by_libelle",
                   return_value=SimpleNamespace(id=2, statut="ouvert")), \
             patch("app.ui.adapters.expenses_adapter.depenses.list_",
                   return_value=[SimpleNamespace(depense=expense, reliquat=None)]), \
             patch("app.ui.adapters.expenses_adapter.resume",
                   return_value=SimpleNamespace(prevu=100, depense=80)):
            data = self.adapter.load("2025-2026")

        self.assertEqual(data.records[0].date, "2026-06-16")


class ExpensesPresenterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_erreur_de_chargement_est_visible_sans_detail_technique(self):
        message = "Impossible de charger les dépenses. Vérifiez la base de données puis réessayez."

        class FailingPort:
            def load(self, exercise_label):
                raise ExpensesLoadError(message)

        view = ExpensesView()
        self.addCleanup(view.close)
        presenter = ExpensesPresenter(view, FailingPort())
        errors = []
        presenter.load_failed.connect(errors.append)

        presenter.show_exercise("2025-2026")

        self.assertEqual(errors, [message])
        self.assertEqual(view.error_label.text(), message)
        self.assertEqual(view.row_count(), 0)
        self.assertFalse(view.add_button.isEnabled())


class ExpensesNavigationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_bouton_ajout_depuis_la_page_ouvre_le_dialogue(self):
        connection = Mock()
        with patch("app.ui.adapters.init_adapter.ensure_first_admin", return_value=True):
            window = MainWindow(MockAuth())
        self.addCleanup(window.close)

        with patch("app.ui.main_window.get_connection", return_value=connection), \
             patch("app.ui.main_window.exercices.list_all", return_value=[]), \
             patch.object(window, "_refresh_dashboard_notifications"):
            window._initialize_main_application()

        dialog = Mock()
        dialog.exec.return_value = 0
        with patch("app.ui.main_window.AddExpenseDialog", return_value=dialog) as create_dialog:
            window.expenses_view.add_button.click()

        create_dialog.assert_called_once()


if __name__ == "__main__":
    unittest.main()