"""Point d'entrée de l'application Gestion d'association."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from app.config import APP_NAME
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme
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
from app.ui.adapters.init_adapter import initialize_application
from app.database.schema import migrate


def _identifiant_windows() -> None:
    """Regroupe correctement l'application dans la barre des tâches de Windows."""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("collectivite.gestion.association")


def _sauvegarder_a_la_fermeture() -> None:
    from app.database.connection import get_connection
    from app.services.backup_service import sauvegarder_automatique

    conn = get_connection()
    try:
        sauvegarder_automatique(conn)
    except Exception as error:
        print(f"AVERTISSEMENT: sauvegarde automatique impossible: {error}")
    finally:
        conn.close()


def main() -> int:
    _identifiant_windows()
    # Échelles fractionnaires de Windows (125 %, 150 %) respectées au lieu d'être arrondies.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_theme(app)

    # Migrer la base de données si nécessaire
    from app.database.connection import get_connection
    from app.services.backup_service import verifier_integrite
    conn = get_connection()
    migrate(conn)

    # Vérifier l'intégrité de la base de données
    integrity_ok, integrity_msg = verifier_integrite(conn)
    if not integrity_ok:
        print(f"AVERTISSEMENT: Intégrité de la base de données: {integrity_msg}")
    conn.close()

    # Initialiser l'application (admin + exercice)
    initialize_application()
    app.aboutToQuit.connect(_sauvegarder_a_la_fermeture)

    # Utiliser uniquement l'adaptateur d'authentification au démarrage
    # Les autres adaptateurs seront chargés après authentification réussie
    auth = AuthAdapter()

    fenetre = MainWindow(auth)
    fenetre.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())