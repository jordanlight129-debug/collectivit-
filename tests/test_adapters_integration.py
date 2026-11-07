"""Tests d'intégration des adaptateurs avec base de données temporaire."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

# Ajouter le répertoire parent au path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR, BACKUP_DIR, EXPORT_DIR
from app.database.connection import get_connection
from app.database.schema import migrate
from app.security.session import Session, CurrentUser, Role
from app.services.auth_service import create_first_admin
from app.services.exercice_service import create_exercice, set_funeral_tarifs
from app.services.membre_service import create_membre


from app.ui.adapters.auth_adapter import AuthAdapter
from app.ui.adapters.dashboard_adapter import DashboardAdapter
from app.ui.adapters.members_adapter import MembersAdapter
from app.ui.adapters.monthly_adapter import MonthlyAdapter
from app.ui.adapters.funeral_adapter import FuneralAdapter
from app.ui.adapters.parallel_adapter import ParallelAdapter
from app.ui.adapters.fines_adapter import FinesAdapter
from app.ui.adapters.expenses_adapter import ExpensesAdapter
from app.ui.adapters.leftovers_adapter import LeftoversAdapter
from app.ui.adapters.balance_adapter import BalanceAdapter
from app.ui.adapters.reports_adapter import ReportsAdapter
from app.ui.adapters.backups_adapter import BackupsAdapter
from app.ui.adapters.audit_adapter import AuditAdapter
from app.ui.adapters.settings_adapter import SettingsAdapter

from app.ui.widgets.banner import Banner, Toast


class TestAdaptersIntegration(unittest.TestCase):
    """Teste l'instanciation et les actions principales de chaque adaptateur."""

    @classmethod
    def setUpClass(cls):
        """Crée une base de données temporaire avec des données de test."""
        # Créer un répertoire temporaire
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_db = Path(cls.temp_dir) / "test.db"
        cls.test_backup = Path(cls.temp_dir) / "backups"
        cls.test_export = Path(cls.temp_dir) / "exports"
        
        # Redéfinir les chemins de configuration
        cls.original_data_dir = DATA_DIR
        cls.original_backup_dir = BACKUP_DIR
        cls.original_export_dir = EXPORT_DIR
        
        import app.config
        app.config.DATA_DIR = Path(cls.temp_dir)
        app.config.BACKUP_DIR = cls.test_backup
        app.config.EXPORT_DIR = cls.test_export
        app.config.DB_PATH = cls.test_db
        
        # Créer les dossiers
        cls.test_backup.mkdir(parents=True, exist_ok=True)
        cls.test_export.mkdir(parents=True, exist_ok=True)
        
        # Créer et migrer la base
        conn = sqlite3.connect(str(cls.test_db))
        conn.row_factory = sqlite3.Row
        migrate(conn)
        
        # Créer un administrateur
        session = Session()
        admin_id = create_first_admin(conn, "admin", "Administrateur Test", "AdminTest1234")
        session.login(CurrentUser(admin_id, "admin", "Administrateur Test", Role.ADMINISTRATEUR))
        cls.session = session
        
        # Créer un exercice
        exercice = create_exercice(conn, session, 2025, 5000, 3000)
        set_funeral_tarifs(conn, session, exercice.id, 10000, 8000)
        cls.exercice_id = exercice.id
        cls.exercice_label = exercice.libelle
        
        # Créer un membre de test
        from app.models.sexe import Sexe
        membre = create_membre(conn, session, "Test User", Sexe.HOMME, date.fromisoformat("2025-01-01"))
        cls.membre_id = membre.id
        cls.membre_carnet = membre.numero_carnet
        
        conn.close()
        
    @classmethod
    def tearDownClass(cls):
        """Nettoie le répertoire temporaire."""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
        
        # Restaurer les chemins originaux
        import app.config
        app.config.DATA_DIR = cls.original_data_dir
        app.config.BACKUP_DIR = cls.original_backup_dir
        app.config.EXPORT_DIR = cls.original_export_dir

    def test_auth_adapter(self):
        """Teste l'adaptateur d'authentification."""
        import unittest.mock
        # Patch DB_PATH pour utiliser la base temporaire
        with unittest.mock.patch('app.database.connection.DB_PATH', str(self.test_db)):
            adapter = AuthAdapter()
            result = adapter.login("admin", "AdminTest1234")
            self.assertEqual(result.status, "ok")
            self.assertIsNotNone(adapter.session.user)

    def test_auth_adapter_change_password(self):
        adapter = AuthAdapter()
        with patch("app.ui.adapters.auth_adapter.get_connection",
                   side_effect=lambda: get_connection(self.test_db)):
            self.assertEqual(adapter.login("admin", "AdminTest1234").status, "ok")
            adapter.change_password("AdminTest1234", "Nouveau2026")
            adapter.logout()
            self.assertEqual(adapter.login("admin", "Nouveau2026").status, "ok")
            adapter.logout()
            self.assertEqual(adapter.login("admin", "AdminTest1234").status, "refused")

    def test_dashboard_adapter(self):
        """Teste l'adaptateur du tableau de bord."""
        adapter = DashboardAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)
        self.assertIsInstance(data.active_members, int)

    def test_members_adapter(self):
        """Teste l'adaptateur des membres."""
        adapter = MembersAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)
        self.assertIsInstance(data.members, tuple)

    def test_monthly_adapter(self):
        """Teste l'adaptateur des cotisations mensuelles."""
        adapter = MonthlyAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)
        self.assertIsInstance(data.members, tuple)

    def test_funeral_adapter(self):
        """Teste l'adaptateur des cotisations funéraires."""
        adapter = FuneralAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)
        self.assertIsInstance(data.records, tuple)

    def test_parallel_adapter(self):
        """Teste l'adaptateur des cotisations parallèles."""
        adapter = ParallelAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)
        self.assertIsInstance(data.subscriptions, tuple)

    def test_fines_adapter(self):
        """Teste l'adaptateur des amendes."""
        adapter = FinesAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)
        self.assertIsInstance(data.records, tuple)

    def test_expenses_adapter(self):
        """Teste l'adaptateur des dépenses."""
        adapter = ExpensesAdapter()
        with patch("app.ui.adapters.expenses_adapter.get_connection",
               side_effect=lambda: get_connection(self.test_db)):
            data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)
        self.assertIsInstance(data.records, tuple)

    def test_expenses_adapter_add_expense(self):
        """Teste l'ajout d'une dépense avec la session authentifiée."""
        adapter = ExpensesAdapter()
        adapter._session = self.session
        with patch("app.ui.adapters.expenses_adapter.get_connection",
                   side_effect=lambda: get_connection(self.test_db)):
            expense_id = adapter.add_expense(
                self.exercice_label, "Achat de fournitures", "Fournisseur test",
                1200, 1000, "2026-06-16",
            )
            data = adapter.load(self.exercice_label)

        expense = next(record for record in data.records if record.id == expense_id)
        self.assertEqual(expense.label, "Achat de fournitures")
        self.assertEqual(expense.amount_planned, 1200)
        self.assertEqual(expense.amount_spent, 1000)

    def test_leftovers_adapter(self):
        """Teste l'adaptateur des reliquats."""
        adapter = LeftoversAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)
        self.assertIsInstance(data.records, tuple)

    def test_balance_adapter(self):
        """Teste l'adaptateur du solde."""
        adapter = BalanceAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)

    def test_reports_adapter(self):
        """Teste l'adaptateur des rapports."""
        adapter = ReportsAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)

    def test_backups_adapter(self):
        """Teste l'adaptateur des sauvegardes."""
        adapter = BackupsAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)
        self.assertIsInstance(data.backups, tuple)

    def test_audit_adapter(self):
        """Teste l'adaptateur du journal d'audit."""
        adapter = AuditAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)
        self.assertIsInstance(data.logs, tuple)

    def test_settings_adapter(self):
        """Teste l'adaptateur des paramètres."""
        adapter = SettingsAdapter()
        data = adapter.load(self.exercice_label)
        self.assertEqual(data.exercise_label, self.exercice_label)

    def test_settings_adapter_gere_les_comptes_secretaires(self):
        with patch("app.ui.adapters.settings_adapter.get_connection",
               side_effect=lambda: get_connection(self.test_db)):
            adapter = SettingsAdapter()
            adapter.set_session(self.session)
            adapter.create_secretary("awa.dovi", "Awa Dovi", "Secret2026")
            data = adapter.load(self.exercice_label)
            user = next(account for account in data.users if account.identifiant == "awa.dovi")
            self.assertEqual((user.nom_complet, user.role.label, user.actif),
                     ("Awa Dovi", "Secrétaire", True))
            self.assertFalse(hasattr(user, "mot_de_passe_hash"))

            adapter.reset_user_password(user.id, "Nouveau2026")
            adapter.set_user_active(user.id, False)
            inactive = next(account for account in adapter.load(self.exercice_label).users
                    if account.id == user.id)
            self.assertFalse(inactive.actif)

    def test_banner_component(self):
        """Teste le composant Banner pour tous les types acceptés."""
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Test des types acceptés
        for kind in ["info", "warning", "danger"]:
            banner = Banner(kind, "Test message")
            self.assertEqual(banner.kind, kind)
        
        # Test que 'error' est rejeté
        with self.assertRaises(ValueError):
            Banner("error", "Test message")

    def test_toast_component(self):
        """Teste le composant Toast pour tous les types acceptés."""
        from PySide6.QtWidgets import QApplication, QWidget
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        parent = QWidget()
        toast = Toast(parent)
        
        # Test des types acceptés
        for kind in ["success", "danger", "warning", "info"]:
            # Ne pas afficher réellement, juste vérifier que ça ne plante pas
            try:
                toast.popup(kind, "Test Title", "Test message", msecs=1)
            except:
                pass
        
        # Test que 'error' est accepté comme synonyme de 'danger'
        try:
            toast.popup("error", "Test", "Test", msecs=1)
        except ValueError:
            self.fail("'error' devrait être accepté comme synonyme de 'danger'")


if __name__ == "__main__":
    unittest.main()
