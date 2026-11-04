"""Fenêtre principale : écran de connexion, puis coquille de l'application."""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from app.config import APP_NAME
from app.database.connection import get_connection
from app.repositories import exercices
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
from app.ui.navigation import Page
from app.ui.ports import AuthPort, DashboardPort, UserInfo
from app.ui.ports_members import MembersPort
from app.ui.ports_monthly import MonthlyPort
from app.ui.ports_funeral import FuneralPort
from app.ui.ports_parallel import ParallelPort
from app.ui.ports_fines import FinesPort
from app.ui.ports_expenses import ExpensesPort
from app.ui.ports_leftovers import LeftoversPort
from app.ui.ports_balance import BalancePort
from app.ui.ports_reports import ReportsPort
from app.ui.ports_backups import BackupsPort
from app.ui.ports_audit import AuditPort
from app.ui.ports_settings import SettingsPort
from app.ui.presenters.dashboard import DashboardPresenter
from app.ui.presenters.login import LoginPresenter
from app.ui.presenters.members import MembersPresenter
from app.ui.presenters.monthly import MonthlyPresenter
from app.ui.presenters.funeral import FuneralPresenter
from app.ui.presenters.parallel import ParallelPresenter
from app.ui.presenters.fines import FinesPresenter
from app.ui.presenters.expenses import ExpensesPresenter
from app.ui.presenters.leftovers import LeftoversPresenter
from app.ui.presenters.balance import BalancePresenter
from app.ui.presenters.reports import ReportsPresenter
from app.ui.presenters.backups import BackupsPresenter
from app.ui.presenters.audit import AuditPresenter
from app.ui.presenters.settings import SettingsPresenter
from app.ui.theme.tokens import Layout
from app.ui.views.dashboard import DashboardView
from app.ui.views.login import LoginView
from app.ui.views.members import MembersView
from app.ui.views.monthly import MonthlyView
from app.ui.views.funeral import FuneralView
from app.ui.views.parallel import ParallelView
from app.ui.views.fines import FinesView
from app.ui.views.expenses import ExpensesView
from app.ui.views.leftovers import LeftoversView
from app.ui.views.balance import BalanceView
from app.ui.views.reports import ReportsView
from app.ui.views.backups import BackupsView
from app.ui.views.audit import AuditView
from app.ui.views.settings import SettingsView
from app.ui.views.shell import Shell
from app.ui.widgets.banner import Toast
from app.ui.dialogs.add_member_dialog import AddMemberDialog
from app.ui.dialogs.add_payment_dialog import AddPaymentDialog
from app.ui.dialogs.add_expense_dialog import AddExpenseDialog


class MainWindow(QMainWindow):
    """Une seule fenêtre : un QStackedWidget [connexion, coquille]. La barre de titre est celle de Windows."""

    def __init__(self, auth: AuthPort, dashboard: DashboardPort | None = None,
                 members: MembersPort | None = None, monthly: MonthlyPort | None = None,
                 funeral: FuneralPort | None = None, parallel: ParallelPort | None = None,
                 fines: FinesPort | None = None, expenses: ExpensesPort | None = None,
                 leftovers: LeftoversPort | None = None, balance: BalancePort | None = None,
                 reports: ReportsPort | None = None, backups: BackupsPort | None = None,
                 audit: AuditPort | None = None, settings: SettingsPort | None = None) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(*Layout.MIN_WINDOW)
        self.resize(1360, 860)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Données réelles depuis la base de données
        conn = get_connection()
        try:
            exercices_list = exercices.list_all(conn)
            from app.ui.ports import ExerciseInfo
            exercises_data = [ExerciseInfo(ex.libelle, ex.statut == "ouvert") for ex in exercices_list]
            conn.close()
        except:
            from app.ui.ports import ExerciseInfo
            exercises_data = [ExerciseInfo("2026-2027", True)]
            conn.close()
        
        brand_name = "Collectivité LANTCHIBLE"
        brand_initials = "CL"
        
        self.login_view = LoginView(brand_name=brand_name, brand_initials=brand_initials,
                                    tagline="Cotisations, décès, amendes et bilan : tout le carnet de votre association.",
                                    features=("Cotisations mensuelles, funéraires et parallèles",
                                               "Bilan financier et clôture d'exercice",
                                               "Sauvegarde automatique de vos données"),
                                    footer="© 2026 Association Collectivité LANTCHIBLE")
        self.shell = Shell(association_name="Collectivité LANTCHIBLE", brand_name=brand_name,
                           brand_sub="Gestion d'association", brand_initials=brand_initials,
                           footer="Version 1.0 · Mode hors ligne")
        self.shell.set_exercises(exercises_data)
        self.shell.set_notifications([])
        self.shell.statusbar.set_database(True, "Base de données locale : connectée")
        self.shell.statusbar.set_last_backup("Dernière sauvegarde : jamais")
        self.shell.statusbar.set_notice("")
        self.stack.addWidget(self.login_view)
        self.stack.addWidget(self.shell)
        self.toast = Toast(self.stack)

        # Tableau de bord
        self.dashboard_view = DashboardView()
        self.shell.set_page(Page.DASHBOARD, self.dashboard_view)
        self.dashboard_presenter = DashboardPresenter(self.dashboard_view, dashboard, self)

        # Membres
        self.members_view = MembersView()
        self.shell.set_page(Page.MEMBERS, self.members_view)
        self.members_presenter = MembersPresenter(self.members_view, members, self)

        # Cotisations mensuelles
        self.monthly_view = MonthlyView()
        self.shell.set_page(Page.MONTHLY, self.monthly_view)
        self.monthly_presenter = MonthlyPresenter(self.monthly_view, monthly, self)

        # Cotisations funéraires
        self.funeral_view = FuneralView()
        self.shell.set_page(Page.FUNERAL, self.funeral_view)
        self.funeral_presenter = FuneralPresenter(self.funeral_view, funeral, self)

        # Cotisations parallèles
        self.parallel_view = ParallelView()
        self.shell.set_page(Page.PARALLEL, self.parallel_view)
        self.parallel_presenter = ParallelPresenter(self.parallel_view, parallel, self)

        # Amendes
        self.fines_view = FinesView()
        self.shell.set_page(Page.FINES, self.fines_view)
        self.fines_presenter = FinesPresenter(self.fines_view, fines, self)

        # Dépenses
        self.expenses_view = ExpensesView()
        self.shell.set_page(Page.EXPENSES, self.expenses_view)
        self.expenses_presenter = ExpensesPresenter(self.expenses_view, expenses, self)

        # Reliquats
        self.leftovers_view = LeftoversView()
        self.shell.set_page(Page.LEFTOVERS, self.leftovers_view)
        self.leftovers_presenter = LeftoversPresenter(self.leftovers_view, leftovers, self)

        # Bilan financier
        self.balance_view = BalanceView()
        self.shell.set_page(Page.BALANCE, self.balance_view)
        self.balance_presenter = BalancePresenter(self.balance_view, balance, self)

        # Rapports et exports
        self.reports_view = ReportsView()
        self.shell.set_page(Page.REPORTS, self.reports_view)
        self.reports_presenter = ReportsPresenter(self.reports_view, reports, self)

        # Sauvegardes
        self.backups_view = BackupsView()
        self.shell.set_page(Page.BACKUPS, self.backups_view)
        self.backups_presenter = BackupsPresenter(self.backups_view, backups, self)

        # Journal d'audit
        self.audit_view = AuditView()
        self.shell.set_page(Page.AUDIT, self.audit_view)
        self.audit_presenter = AuditPresenter(self.audit_view, audit, self)

        # Paramètres
        self.settings_view = SettingsView()
        self.shell.set_page(Page.SETTINGS, self.settings_view)
        self.settings_presenter = SettingsPresenter(self.settings_view, settings, self)

        self.login_presenter = LoginPresenter(self.login_view, auth, self)
        self.login_presenter.authenticated.connect(self._on_authenticated)
        self.shell.logout_requested.connect(self._on_logout)
        self.shell.password_requested.connect(lambda: self.toast.popup("info", "Changement de mot de passe", "Fonctionnalité à implémenter"))
        self.shell.exercise_selected.connect(self.dashboard_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.members_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.monthly_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.funeral_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.parallel_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.fines_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.expenses_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.leftovers_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.balance_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.reports_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.backups_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.audit_presenter.show_exercise)
        self.shell.exercise_selected.connect(self.settings_presenter.show_exercise)

        vue = self.dashboard_view
        vue.payment_requested.connect(self._show_payment_dialog)
        vue.expense_requested.connect(self._show_expense_dialog)
        vue.member_requested.connect(lambda: self.shell.show_page(Page.MEMBERS))
        vue.collecte_requested.connect(lambda: self.toast.popup(
            "info", "Collecte décès", "Utilisez l'écran Cotisations funéraires"))
        vue.export_requested.connect(lambda: self.shell.show_page(Page.REPORTS))
        vue.backup_requested.connect(lambda: self.shell.show_page(Page.BACKUPS))

        membres = self.members_view
        membres.export_requested.connect(lambda: self.shell.show_page(Page.REPORTS))
        membres.add_requested.connect(self._show_add_member_dialog)
        membres.member_action_requested.connect(lambda carnet: self.toast.popup(
            "info", f"Carnet {carnet}", "Menu d'actions à implémenter"))
        self.show_login()

    def _show_add_member_dialog(self) -> None:
        """Affiche le dialogue d'ajout de membre."""
        dialog = AddMemberDialog(self)
        if dialog.exec():
            try:
                data = dialog.get_data()
                membre_id = self.members_presenter._port.add_member(
                    data["nom"],
                    data["sexe"],
                    data["date_adhesion"]
                )
                self.toast.popup("success", "Membre ajouté", f"{data['nom']} a été ajouté avec succès")
                self.members_presenter.show_exercise(self.shell.current_exercise_label)
            except Exception as e:
                self.toast.popup("error", "Erreur", str(e))

    def _show_payment_dialog(self) -> None:
        """Affiche le dialogue d'enregistrement de versement."""
        # Pour l'instant, affiche un message car il faut sélectionner un membre
        self.toast.popup("info", "Versement", "Sélectionnez d'abord un membre dans l'écran Membres")

    def _show_expense_dialog(self) -> None:
        """Affiche le dialogue de nouvelle dépense."""
        dialog = AddExpenseDialog(self)
        if dialog.exec():
            try:
                data = dialog.get_data()
                depense_id = self.expenses_presenter._port.add_expense(
                    self.shell.current_exercise_label,
                    data["libelle"],
                    data["beneficiaire"],
                    data["montant_prevu"],
                    data["montant_depense"],
                    data["date_depense"]
                )
                self.toast.popup("success", "Dépense enregistrée", f"{data['libelle']} : {data['montant_depense']} FCFA")
                self.expenses_presenter.show_exercise(self.shell.current_exercise_label)
            except Exception as e:
                self.toast.popup("error", "Erreur", str(e))

    def show_login(self) -> None:
        self.login_view.reset()
        self.stack.setCurrentWidget(self.login_view)
        self.login_view.focus_identifier()

    def _on_authenticated(self, user: UserInfo) -> None:
        self.shell.start(user)
        self.dashboard_presenter.show_exercise(self.shell.current_exercise_label)
        self.members_presenter.show_exercise(self.shell.current_exercise_label)
        self.monthly_presenter.show_exercise(self.shell.current_exercise_label)
        self.funeral_presenter.show_exercise(self.shell.current_exercise_label)
        self.parallel_presenter.show_exercise(self.shell.current_exercise_label)
        self.fines_presenter.show_exercise(self.shell.current_exercise_label)
        self.expenses_presenter.show_exercise(self.shell.current_exercise_label)
        self.leftovers_presenter.show_exercise(self.shell.current_exercise_label)
        self.balance_presenter.show_exercise(self.shell.current_exercise_label)
        self.reports_presenter.show_exercise(self.shell.current_exercise_label)
        self.backups_presenter.show_exercise(self.shell.current_exercise_label)
        self.audit_presenter.show_exercise(self.shell.current_exercise_label)
        self.settings_presenter.show_exercise(self.shell.current_exercise_label)
        self.stack.setCurrentWidget(self.shell)
        self.toast.popup("success", f"Bienvenue, {user.full_name}", user.role_label)

    def _on_logout(self) -> None:
        self.shell.close_popover()
        self.show_login()
