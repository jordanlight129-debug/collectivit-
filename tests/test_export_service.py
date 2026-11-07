from datetime import date
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from openpyxl import load_workbook

from app.database.connection import get_connection
from app.database.schema import migrate
from app.security import audit
from app.security.session import CurrentUser, NotAuthenticated, Role, Session
from app.services import exercice_service, export_service, membre_service
from app.models.sexe import Sexe
from app.ui.adapters.reports_adapter import ReportsAdapter


class ExportServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.addCleanup(self.conn.close)
        migrate(self.conn)
        self.session = Session()
        self.session.login(CurrentUser(1, "admin", "Administrateur", Role.ADMINISTRATEUR))
        self.exercise = exercice_service.create_exercice(
            self.conn, self.session, 2025, 18000, 14000)
        membre_service.create_membre(
            self.conn, self.session, "Test Membre", Sexe.HOMME,
            date(2025, 9, 1), today=date(2026, 8, 31))

    def test_tous_les_rapports_se_generent_en_excel_et_pdf(self):
        keys = ("balance", "funeral", "members", "debts", "monthly", "expenses", "audit")
        with TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            for key in keys:
                with self.subTest(report=key, format="excel"):
                    path = export_service.export_report(
                        self.conn, self.exercise.libelle, key, "excel", output_dir)
                    workbook = load_workbook(path, read_only=True)
                    self.assertTrue(workbook.active.cell(1, 1).value)
                    self.assertGreaterEqual(workbook.active.max_row, 4)
                    workbook.close()
                with self.subTest(report=key, format="pdf"):
                    path = export_service.export_report(
                        self.conn, self.exercise.libelle, key, "pdf", output_dir)
                    self.assertTrue(path.read_bytes().startswith(b"%PDF-"))
                    self.assertGreater(path.stat().st_size, 500)

    def test_format_inconnu_est_refuse(self):
        with self.assertRaises(ValueError):
            export_service.export_report(
                self.conn, self.exercise.libelle, "members", "docx")

    def test_adaptateur_exporte_et_journalise(self):
        with TemporaryDirectory() as temporary_directory:
            with patch("app.ui.adapters.reports_adapter.get_connection", return_value=self.conn), \
                    patch("app.ui.adapters.reports_adapter.closing", side_effect=nullcontext), \
                    patch("app.config.EXPORT_DIR", Path(temporary_directory)):
                path = ReportsAdapter(self.session).export_report(
                    self.exercise.libelle, "members", "excel")
            self.assertTrue(path.is_file())
            entries = audit.list_entries(self.conn, limit=5)
            self.assertEqual(entries[0]["action"], "Export de rapport")

    def test_export_requiert_une_session_authentifiee(self):
        with patch("app.ui.adapters.reports_adapter.get_connection") as get_conn:
            with self.assertRaises(NotAuthenticated):
                ReportsAdapter().export_report(self.exercise.libelle, "members", "excel")
            get_conn.assert_not_called()


if __name__ == "__main__":
    unittest.main()