"""Tests d'intégration UI pour les cotisations mensuelles."""
import unittest
from datetime import date

from PySide6.QtWidgets import QApplication

from app.database.connection import get_connection
from app.database.schema import migrate
from app.models.sexe import Sexe
from app.repositories import exercices, utilisateurs
from app.security.session import CurrentUser, Role, Session
from app.services import exercice_service, membre_service, versement_service
from app.ui.presenters.monthly import MonthlyPresenter
from app.ui.views.monthly import MonthlyView
from app.ui.adapters.monthly_adapter import MonthlyAdapter

TODAY = date(2026, 8, 31)


class MonthlyUIIntegrationTest(unittest.TestCase):
    """Tests d'intégration de l'interface des cotisations mensuelles."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.conn = get_connection(":memory:")
        self.addCleanup(self.conn.close)
        migrate(self.conn)
        utilisateurs.create(self.conn, "admin", "Admin", "x", Role.ADMINISTRATEUR)
        self.session = Session()
        self.session.login(CurrentUser(1, "admin", "Admin", Role.ADMINISTRATEUR))
        self.ex = exercice_service.create_exercice(self.conn, self.session, 2025, 18000, 14000)

        # Créer des membres
        self.membre1 = membre_service.create_membre(self.conn, self.session, "Test 1", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        self.membre2 = membre_service.create_membre(self.conn, self.session, "Test 2", Sexe.FEMME, date(2017, 9, 5), today=TODAY)

        # Créer la vue, l'adaptateur et le présentateur
        self.view = MonthlyView()
        self.adapter = MonthlyAdapter(self.conn)
        self.presenter = MonthlyPresenter(self.view, self.adapter)

    def test_grille_s_affiche(self):
        """Test: la grille s'affiche avec tous les membres et les 12 mois."""
        self.presenter.show_exercise(self.ex.libelle)
        # Vérifier que la vue a des lignes
        self.assertGreater(self.view.row_count(), 0)
        # Vérifier qu'il y a des données
        self.assertIsNotNone(self.presenter._data)
        self.assertEqual(len(self.presenter._data.members), 2)

    def test_changement_annee(self):
        """Test: le changement d'année fonctionne."""
        # Créer un deuxième exercice
        ex2 = exercice_service.create_exercice(self.conn, self.session, 2026, 20000, 15000)
        self.presenter.show_exercise(ex2.libelle)
        self.assertEqual(self.presenter._label, ex2.libelle)
        # Revenir au premier exercice
        self.presenter.show_exercise(self.ex.libelle)
        self.assertEqual(self.presenter._label, self.ex.libelle)

    def test_totaux_affiches(self):
        """Test: les totaux affichés correspondent aux données de la base."""
        # Ajouter des versements
        versement_service.enregistrer(self.conn, self.session, self.membre1.id, self.ex.id, versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY)
        versement_service.enregistrer(self.conn, self.session, self.membre2.id, self.ex.id, versement_service.MENSUELLE, 14000, date(2026, 2, 1), today=TODAY)

        self.presenter.show_exercise(self.ex.libelle)
        # Vérifier que les totaux sont calculés
        data = self.presenter._data
        total_paid = sum(m.total_paid for m in data.members)
        self.assertEqual(total_paid, 32000)

    def test_liste_vide_membres(self):
        """Test: aucun plantage si la base est vide (aucun membre)."""
        # Créer une nouvelle connexion vide
        conn_empty = get_connection(":memory:")
        self.addCleanup(conn_empty.close)
        migrate(conn_empty)
        utilisateurs.create(conn_empty, "admin", "Admin", "x", Role.ADMINISTRATEUR)
        session_empty = Session()
        session_empty.login(CurrentUser(1, "admin", "Admin", Role.ADMINISTRATEUR))
        ex_empty = exercice_service.create_exercice(conn_empty, session_empty, 2027, 18000, 14000)

        # Créer un nouvel adaptateur avec la connexion vide
        adapter_empty = MonthlyAdapter(conn_empty)
        view_empty = MonthlyView()
        presenter_empty = MonthlyPresenter(view_empty, adapter_empty)

        # Ne doit pas planter
        presenter_empty.show_exercise(ex_empty.libelle)
        self.assertEqual(len(presenter_empty._data.members), 0)
        self.assertEqual(view_empty.row_count(), 0)

    def test_refresh_apres_versement(self):
        """Test: refresh après un versement met à jour les données."""
        self.presenter.show_exercise(self.ex.libelle)
        total_avant = sum(m.total_paid for m in self.presenter._data.members)

        # Ajouter un versement
        versement_service.enregistrer(self.conn, self.session, self.membre1.id, self.ex.id, versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY)

        # Refresh
        self.presenter.refresh()
        total_apres = sum(m.total_paid for m in self.presenter._data.members)
        self.assertEqual(total_apres, total_avant + 18000)


if __name__ == "__main__":
    unittest.main()
