"""Fenêtre principale : écran de connexion, puis coquille de l'application."""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from app.config import APP_NAME, ASSOCIATION_NAME, BRAND_INITIALS
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
from app.security.session import Permission
from app.ui.navigation import Page
from app.ui.ports import AuthPort, DashboardPort, ExerciseInfo, NotificationInfo, UserInfo
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
from app.ui.presenters.setup import SetupPresenter
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
from app.ui.views.setup import SetupView
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
from app.ui.dialogs.add_payment_dialog import PaymentsDialog
from app.ui.dialogs.add_expense_dialog import AddExpenseDialog
from app.ui.dialogs.add_funeral_dialog import AddFuneralDialog
from app.ui.dialogs.add_parallel_dialog import AddParallelDialog
from app.ui.dialogs.add_fine_dialog import AddFineDialog
from app.ui.dialogs.member_dashboard_dialog import MemberDashboardDialog
from app.ui.dialogs.reset_user_password_dialog import ResetUserPasswordDialog
from app.ui.dialogs.change_password_dialog import ChangePasswordDialog
from app.ui.dialogs.collect_payment_dialog import CollectFineDialog, CollectPaymentDialog
from PySide6.QtCore import Signal

class MainWindow(QMainWindow):
    """Une seule fenêtre : un QStackedWidget [setup, connexion, coquille]. La barre de titre est celle de Windows."""

    setup_completed = Signal()

    def __init__(self, auth: AuthPort, dashboard: DashboardPort | None = None,
                 members: MembersPort | None = None, monthly: MonthlyPort | None = None,
                 funeral: FuneralPort | None = None, parallel: ParallelPort | None = None,
                 fines: FinesPort | None = None, expenses: ExpensesPort | None = None,
                 leftovers: LeftoversPort | None = None, balance: BalancePort | None = None,
                 reports: ReportsPort | None = None, backups: BackupsPort | None = None,
                 audit: AuditPort | None = None, settings: SettingsPort | None = None) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        available = self.screen().availableGeometry()
        width = min(1360, available.width())
        height = min(860, available.height())
        self.setMinimumSize(min(Layout.MIN_WINDOW[0], width), min(Layout.MIN_WINDOW[1], height))
        self.resize(width, height)
        self.move(
            available.x() + max((available.width() - width) // 2, 0),
            available.y() + max((available.height() - height) // 2, 0),
        )

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Conserver les adaptateurs pour les utiliser après authentification
        self._auth = auth
        self._dashboard = dashboard
        self._members = members
        self._monthly = monthly
        self._funeral = funeral
        self._parallel = parallel
        self._fines = fines
        self._expenses = expenses
        self._leftovers = leftovers
        self._balance = balance
        self._reports = reports
        self._backups = backups
        self._audit = audit
        self._settings = settings

        brand_name = ASSOCIATION_NAME
        brand_initials = BRAND_INITIALS

        # Créer uniquement les vues de setup et login au démarrage
        self.setup_view = SetupView(brand_name=brand_name, brand_initials=brand_initials,
                                    tagline="Cotisations, dépenses et bilan de l’exercice, en toute transparence.",
                                    features=("Fonctionne sans connexion Internet",
                                               "Données enregistrées localement sur cet ordinateur",
                                               "Chaque action est consignée dans le journal d’audit"),
                                    footer="Version 1.0 · Windows 10 / 11")
        self.login_view = LoginView(brand_name=brand_name, brand_initials=brand_initials,
                                    tagline="Cotisations, dépenses et bilan de l’exercice, en toute transparence.",
                                    features=("Fonctionne sans connexion Internet",
                                               "Données enregistrées localement sur cet ordinateur",
                                               "Chaque action est consignée dans le journal d’audit"),
                                    footer="Version 1.0 · Windows 10 / 11")
        self.stack.addWidget(self.setup_view)
        self.stack.addWidget(self.login_view)
        self.toast = Toast(self.stack)

        self.setup_presenter = SetupPresenter(self.setup_view, self)
        self.setup_presenter.setup_completed.connect(self._on_setup_completed)

        self.login_presenter = LoginPresenter(self.login_view, auth, self)
        self.login_presenter.authenticated.connect(self._on_authenticated)

        # Vérifier si un admin existe au démarrage
        self._check_first_launch()

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

    def _members_for_dialog(self):
        data = getattr(self.members_presenter, "_data", None)
        return data.members if data is not None else ()

    def _show_add_funeral_dialog(self) -> None:
        dialog = AddFuneralDialog(self._members_for_dialog(), self)
        if not dialog.exec():
            return
        try:
            data = dialog.get_data()
            self.funeral_presenter._port.create_collection(**data)
            exercise = self.shell.current_exercise_label
            self.funeral_presenter.show_exercise(exercise)
            self.members_presenter.show_exercise(exercise)
            self.monthly_presenter.show_exercise(exercise)
            self.dashboard_presenter.show_exercise(exercise)
            self.toast.popup("success", "Collecte créée", data["nom_defunt"] or "Décès enregistré")
        except Exception as error:
            self.toast.popup("error", "Erreur", str(error))

    def _show_add_parallel_dialog(self) -> None:
        dialog = AddParallelDialog(self)
        if not dialog.exec():
            return
        try:
            data = dialog.get_data()
            self.parallel_presenter._port.add_subscription(**data)
            exercise = self.shell.current_exercise_label
            self.parallel_presenter.show_exercise(exercise)
            self.dashboard_presenter.show_exercise(exercise)
            self.toast.popup("success", "Cotisation créée", data["nom"])
        except Exception as error:
            self.toast.popup("error", "Erreur", str(error))

    def _show_add_fine_dialog(self) -> None:
        dialog = AddFineDialog(self._members_for_dialog(), self)
        if not dialog.exec():
            return
        try:
            data = dialog.get_data()
            self.fines_presenter._port.add_fine(**data)
            exercise = self.shell.current_exercise_label
            self.fines_presenter.show_exercise(exercise)
            self.dashboard_presenter.show_exercise(exercise)
            self.toast.popup("success", "Amende enregistrée", data["libelle"])
        except Exception as error:
            self.toast.popup("error", "Erreur", str(error))

    def _show_collection_payment(self, membre_id: int, rubrique: str,
                                 cotisation_id: int | None = None) -> None:
        member = next((item for item in self._members_for_dialog() if item.id == membre_id), None)
        if member is None:
            self.toast.popup("error", "Membre introuvable", "Recharge la page et réessaie.")
            return
        cotisation_name = ""
        if rubrique == "parallele":
            subscription = next((item for item in self.parallel_presenter._data.subscriptions
                                 if item.id == cotisation_id), None)
            if subscription is None:
                self.toast.popup("error", "Cotisation introuvable", "Recharge la page et réessaie.")
                return
            cotisation_name = subscription.name
        rubrique_label = "Cotisation funéraire" if rubrique == "funeraire" else "Cotisation parallèle"
        dialog = CollectPaymentDialog(
            member_id=membre_id,
            member_name=member.name,
            rubrique=rubrique,
            rubrique_label=rubrique_label,
            cotisation_id=cotisation_id,
            cotisation_name=cotisation_name,
            parent=self,
        )
        if not dialog.exec():
            return

        from PySide6.QtWidgets import QMessageBox
        from app.services.reglement_service import ExcedentError

        data = dialog.get_data()
        amount = int(data["montant"])

        def enregistrer(confirmer_excedent: bool = False) -> int:
            if rubrique == "funeraire":
                return self.funeral_presenter._port.record_payment(
                    self.shell.current_exercise_label, membre_id, amount,
                    str(data["date_versement"]), str(data["mode"]), str(data["note"]),
                    confirmer_excedent,
                )
            return self.parallel_presenter._port.record_payment(
                self.shell.current_exercise_label, membre_id, int(cotisation_id), amount,
                str(data["date_versement"]), str(data["mode"]), str(data["note"]),
                confirmer_excedent,
            )

        try:
            try:
                receipt = enregistrer()
            except ExcedentError as error:
                answer = QMessageBox.question(
                    self, "Confirmer l’avance", str(error),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
                receipt = enregistrer(confirmer_excedent=True)
            exercise = self.shell.current_exercise_label
            if rubrique == "funeraire":
                self.funeral_presenter.show_exercise(exercise)
            else:
                self.parallel_presenter.show_exercise(exercise)
            self.dashboard_presenter.show_exercise(exercise)
            self.toast.popup("success", "Versement enregistré", f"Reçu n° {receipt}")
        except Exception as error:
            self.toast.popup("error", "Échec du versement", str(error))

    def _show_collect_fine_dialog(self, amende_id: int) -> None:
        data = getattr(self.fines_presenter, "_data", None)
        fine = next((record for record in data.records if record.id == amende_id), None) if data else None
        if fine is None:
            self.toast.popup("error", "Amende introuvable", "Recharge la page et réessaie.")
            return
        dialog = CollectFineDialog(fine, self)
        if not dialog.exec():
            return
        try:
            values = dialog.get_data()
            self.fines_presenter._port.collect_fine(**values)
            exercise = self.shell.current_exercise_label
            self.fines_presenter.show_exercise(exercise)
            self.dashboard_presenter.show_exercise(exercise)
            self.toast.popup("success", "Encaissement enregistré", fine.member_name)
        except Exception as error:
            self.toast.popup("error", "Échec de l’encaissement", str(error))

    def _show_member_actions(self, membre_id: int, carnet: str) -> None:
        """Affiche le menu d'actions pour un membre."""
        from PySide6.QtWidgets import QMessageBox
        from app.ui.dialogs.edit_member_dialog import EditMemberDialog

        # Boîte de dialogue avec les actions possibles
        msg = QMessageBox(self)
        msg.setWindowTitle(f"Actions - Carnet {carnet}")
        msg.setText(f"Que souhaitez-vous faire pour le membre n°{carnet} ?")
        msg.setIcon(QMessageBox.Icon.Question)

        btn_view = msg.addButton("Voir la fiche", QMessageBox.ButtonRole.ActionRole)
        btn_edit = msg.addButton("Modifier", QMessageBox.ButtonRole.ActionRole)
        btn_delete = msg.addButton("Supprimer", QMessageBox.ButtonRole.ActionRole)
        btn_deceased = msg.addButton("Déclarer décédé", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)

        session = self._auth.session
        btn_edit.setVisible(session.can(Permission.MEMBER_EDIT))
        btn_delete.setVisible(session.can(Permission.DELETE))

        msg.exec()

        if msg.clickedButton() == btn_view:
            self._show_member_dashboard(membre_id)
        elif msg.clickedButton() == btn_edit:
            if not session.can(Permission.MEMBER_EDIT):
                self.toast.popup("error", "Accès refusé", "La modification d'un membre est réservée à l'administrateur.")
                return
            self._show_edit_member_dialog(membre_id, carnet)
        elif msg.clickedButton() == btn_delete:
            if not session.can(Permission.DELETE):
                self.toast.popup("error", "Accès refusé", "La suppression d'un membre est réservée à l'administrateur.")
                return
            self._confirm_delete_member(membre_id, carnet)
        elif msg.clickedButton() == btn_deceased:
            self._declare_member_deceased(membre_id, carnet)

    def _show_member_dashboard(self, membre_id: int) -> None:
        """Affiche la synthèse et l'historique du membre sélectionné."""
        from app.repositories import exercices, membres
        from app.services import historique_service

        conn = get_connection()
        try:
            membre = membres.get(conn, membre_id)
            if membre is None:
                self.toast.popup("error", "Membre introuvable", "Cette fiche membre n'existe plus.")
                return
            exercise_label = self.shell.current_exercise_label
            exercice = exercices.get_by_libelle(conn, exercise_label)
            exercice_id = exercice.id if exercice is not None else None
            exercice_historique = historique_service.historique_membre(
                conn, membre_id, exercice_id=exercice_id)
            historique = historique_service.historique_membre(conn, membre_id)
        except Exception as error:
            self.toast.popup("error", "Fiche membre indisponible", str(error))
            return
        finally:
            conn.close()

        dialog = MemberDashboardDialog(
            membre,
            exercise_label or "tous exercices",
            exercice_historique,
            historique,
            self,
        )
        dialog.exec()

    def _show_edit_member_dialog(self, membre_id: int, carnet: str) -> None:
        """Affiche le dialogue de modification de membre."""
        from app.ui.dialogs.edit_member_dialog import EditMemberDialog
        from app.database.connection import get_connection
        from app.repositories import membres

        conn = get_connection()
        try:
            membre = membres.get(conn, membre_id)
            conn.close()

            if not membre:
                self.toast.popup("error", "Erreur", "Membre introuvable")
                return

            dialog = EditMemberDialog(self)
            dialog.set_data(
                carnet=membre.numero_carnet,
                nom=membre.nom,
                sexe=membre.sexe.value,
                date_adhesion=membre.date_adhesion.strftime("%Y-%m-%d")
            )

            if dialog.exec():
                try:
                    data = dialog.get_data()
                    self.members_presenter._port.update_member(
                        membre_id,
                        data["nom"],
                        data["date_adhesion"]
                    )
                    self.toast.popup("success", "Membre modifié", f"Les modifications ont été enregistrées")
                    self.members_presenter.show_exercise(self.shell.current_exercise_label)
                except Exception as e:
                    self.toast.popup("error", "Erreur", str(e))
        except Exception as e:
            conn.close()
            self.toast.popup("error", "Erreur", str(e))

    def _confirm_delete_member(self, membre_id: int, carnet: str) -> None:
        """Confirme la suppression d'un membre."""
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Êtes-vous sûr de vouloir supprimer le membre n°{carnet} ?\n\n"
            "Cette action est irréversible si le membre n'a pas d'historique.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.members_presenter._port.delete_member(membre_id)
                self.toast.popup("success", "Membre supprimé", f"Le membre n°{carnet} a été supprimé")
                self.members_presenter.show_exercise(self.shell.current_exercise_label)
            except Exception as e:
                self.toast.popup("error", "Erreur", str(e))

    def _declare_member_deceased(self, membre_id: int, carnet: str) -> None:
        """Déclare un membre décédé."""
        from PySide6.QtWidgets import QMessageBox, QInputDialog
        from datetime import date

        reply = QMessageBox.question(
            self,
            "Confirmer le décès",
            f"Êtes-vous sûr de vouloir déclarer le membre n°{carnet} comme décédé ?\n\n"
            "Cela arrêtera ses cotisations et passera son statut à 'décédé'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Demander la date du décès (par défaut : aujourd'hui)
            today = date.today().strftime("%Y-%m-%d")
            date_input, ok = QInputDialog.getText(
                self,
                "Date du décès",
                "Date du décès (YYYY-MM-DD) :",
                text=today
            )

            if ok and date_input:
                try:
                    self.members_presenter._port.declare_deceased(membre_id, date_input)
                    self.toast.popup("success", "Décès enregistré", f"Le membre n°{carnet} a été déclaré décédé")
                    self.members_presenter.show_exercise(self.shell.current_exercise_label)
                except Exception as e:
                    self.toast.popup("error", "Erreur", str(e))

    def _show_payment_dialog(self, carnet: str = "") -> None:
        """Affiche le dialogue d'enregistrement de versement.

        Args:
            carnet: Numéro de carnet du membre (optionnel, vide pour laisser choisir)
        """
        dialog = PaymentsDialog(
            members=self.monthly_presenter.members_for_dialog(),
            carnet=carnet,
            month_index=-1,  # Pas de mois spécifique depuis le bouton principal
            exercise_label=self.shell.current_exercise_label,
            session=self.login_presenter._auth.session,
            parent=self
        )
        if dialog.exec():
            if dialog.a_change():
                self.monthly_presenter.refresh()
                self.toast.popup("success", "Versement enregistré", "Les versements ont été mis à jour")

    def _on_monthly_cell_clicked(self, carnet: str, month_index: int) -> None:
        """Affiche le dialogue de versement pour un membre et un mois spécifique.

        Args:
            carnet: Numéro de carnet du membre
            month_index: Index du mois (0 = septembre, 11 = août)
        """
        dialog = PaymentsDialog(
            members=self.monthly_presenter.members_for_dialog(),
            carnet=carnet,
            month_index=month_index,
            exercise_label=self.shell.current_exercise_label,
            session=self.login_presenter._auth.session,
            parent=self
        )
        if dialog.exec():
            if dialog.a_change():
                self.monthly_presenter.refresh()
                self.toast.popup("success", "Versement enregistré", "Les versements ont été mis à jour")

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

    def _show_expense_actions(self, expense_id: int) -> None:
        from PySide6.QtWidgets import QMessageBox

        if not self._auth.session.can(Permission.DELETE):
            self.toast.popup("error", "Accès refusé", "La suppression d'une dépense est réservée à l'administrateur.")
            return
        answer = QMessageBox.question(
            self,
            "Supprimer la dépense",
            "Supprimer cette dépense ? Le reliquat éventuel associé sera également supprimé.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.expenses_presenter._port.delete_expense(expense_id)
            self.expenses_presenter.show_exercise(self.shell.current_exercise_label)
            self.toast.popup("success", "Dépense supprimée", "La dépense a été supprimée.")
        except Exception as error:
            self.toast.popup("error", "Échec de la suppression", str(error))

    def show_login(self) -> None:
        self.login_view.reset()
        self.stack.setCurrentWidget(self.login_view)
        self.login_view.focus_identifier()

    def show_setup(self) -> None:
        self.setup_view.focus_identifier()
        self.stack.setCurrentWidget(self.setup_view)

    def _check_first_launch(self) -> None:
        """Vérifie si c'est le premier lancement (pas d'admin)."""
        from app.ui.adapters.init_adapter import ensure_first_admin
        if not ensure_first_admin():
            self.show_setup()
        else:
            self.show_login()

    def _on_setup_completed(self) -> None:
        """Appelé après la création réussie de l'administrateur."""
        # Créer l'exercice courant
        from app.ui.adapters.init_adapter import ensure_current_exercise
        ensure_current_exercise()
        # Passer à l'écran de connexion
        self.show_login()
        self.toast.popup("success", "Administrateur créé", "Vous pouvez maintenant vous connecter.")

    def _initialize_main_application(self) -> None:
        """Initialise la coquille et tous les présentateurs après authentification réussie."""
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

        brand_name = ASSOCIATION_NAME
        brand_initials = BRAND_INITIALS

        # Créer la coquille
        self.shell = Shell(association_name=f"Association {ASSOCIATION_NAME}", brand_name=brand_name,
               brand_sub="Gestion d’association", brand_initials=brand_initials,
                   footer="Version 1.0 · Mode hors ligne")
        self.shell.set_exercises(exercises_data)
        self.shell.statusbar.set_database(True, "Base de données locale : connectée")
        self.shell.statusbar.set_last_backup("Dernière sauvegarde : jamais")
        self.shell.statusbar.set_notice("")
        self.stack.addWidget(self.shell)

        # Initialiser les adaptateurs si nécessaire
        if self._dashboard is None:
            self._dashboard = DashboardAdapter()
        if self._members is None:
            self._members = MembersAdapter()
        if self._monthly is None:
            self._monthly = MonthlyAdapter()
        if self._funeral is None:
            self._funeral = FuneralAdapter()
        if self._parallel is None:
            self._parallel = ParallelAdapter()
        if self._fines is None:
            self._fines = FinesAdapter()
        if self._expenses is None:
            self._expenses = ExpensesAdapter()
        if self._leftovers is None:
            self._leftovers = LeftoversAdapter()
        if self._balance is None:
            self._balance = BalanceAdapter()
        if self._reports is None:
            self._reports = ReportsAdapter(self._auth.session)
        if self._backups is None:
            self._backups = BackupsAdapter()
        if self._audit is None:
            self._audit = AuditAdapter()
        if self._settings is None:
            self._settings = SettingsAdapter()

        # Tableau de bord
        self.dashboard_view = DashboardView()
        self.shell.set_page(Page.DASHBOARD, self.dashboard_view)
        self.dashboard_presenter = DashboardPresenter(self.dashboard_view, self._dashboard, self)
        self._refresh_dashboard_notifications(self.shell.current_exercise_label)

        # Membres
        self.members_view = MembersView()
        self.shell.set_page(Page.MEMBERS, self.members_view)
        self.members_presenter = MembersPresenter(self.members_view, self._members, self)

        # Cotisations mensuelles
        self.monthly_view = MonthlyView()
        self.shell.set_page(Page.MONTHLY, self.monthly_view)
        self.monthly_presenter = MonthlyPresenter(self.monthly_view, self._monthly, self)

        # Cotisations funéraires
        self.funeral_view = FuneralView()
        self.shell.set_page(Page.FUNERAL, self.funeral_view)
        self.funeral_presenter = FuneralPresenter(self.funeral_view, self._funeral, self)
        self.funeral_view.add_requested.connect(self._show_add_funeral_dialog)
        self.funeral_view.record_action_requested.connect(
            lambda member_id: self._show_collection_payment(member_id, "funeraire"))

        # Cotisations parallèles
        self.parallel_view = ParallelView()
        self.shell.set_page(Page.PARALLEL, self.parallel_view)
        self.parallel_presenter = ParallelPresenter(self.parallel_view, self._parallel, self)
        self.parallel_view.add_requested.connect(self._show_add_parallel_dialog)
        self.parallel_view.record_payment_requested.connect(
            lambda member_id, subscription_id: self._show_collection_payment(
                member_id, "parallele", subscription_id))

        # Amendes
        self.fines_view = FinesView()
        self.shell.set_page(Page.FINES, self.fines_view)
        self.fines_presenter = FinesPresenter(self.fines_view, self._fines, self)
        self.fines_view.add_requested.connect(self._show_add_fine_dialog)
        self.fines_view.fine_action_requested.connect(self._show_collect_fine_dialog)

        # Dépenses
        self.expenses_view = ExpensesView()
        self.shell.set_page(Page.EXPENSES, self.expenses_view)
        self.expenses_presenter = ExpensesPresenter(self.expenses_view, self._expenses, self)
        self.expenses_presenter.load_failed.connect(
            lambda message: self.toast.popup("error", "Chargement des dépenses", message))
        self.expenses_view.add_requested.connect(self._show_expense_dialog)
        self.expenses_view.expense_action_requested.connect(self._show_expense_actions)

        # Reliquats
        self.leftovers_view = LeftoversView()
        self.shell.set_page(Page.LEFTOVERS, self.leftovers_view)
        self.leftovers_presenter = LeftoversPresenter(self.leftovers_view, self._leftovers, self)

        # Bilan financier
        self.balance_view = BalanceView()
        self.shell.set_page(Page.BALANCE, self.balance_view)
        self.balance_presenter = BalancePresenter(self.balance_view, self._balance, self)

        # Rapports et exports
        self.reports_view = ReportsView()
        self.shell.set_page(Page.REPORTS, self.reports_view)
        self.reports_presenter = ReportsPresenter(self.reports_view, self._reports, self)
        self.reports_view.export_requested.connect(self.reports_presenter.export_report)
        self.reports_presenter.export_completed.connect(self._on_export_completed)
        self.reports_presenter.export_failed.connect(
            lambda message: self.toast.popup("error", "Échec de l’export", message))

        # Sauvegardes
        self.backups_view = BackupsView()
        self.shell.set_page(Page.BACKUPS, self.backups_view)
        self.backups_presenter = BackupsPresenter(self.backups_view, self._backups, self)
        self.backups_view.backup_requested.connect(self.backups_presenter.create_backup)
        self.backups_view.restore_requested.connect(self._confirm_restore_backup)
        self.backups_presenter.backup_created.connect(
            lambda message: self.toast.popup("success", "Sauvegarde terminée", message))
        self.backups_presenter.backup_failed.connect(
            lambda message: self.toast.popup("error", "Échec de la sauvegarde", message))
        self.backups_presenter.backup_restored.connect(self._on_backup_restored)
        self.backups_presenter.restore_failed.connect(
            lambda message: self.toast.popup("error", "Échec de la restauration", message))

        # Journal d'audit
        self.audit_view = AuditView()
        self.shell.set_page(Page.AUDIT, self.audit_view)
        self.audit_presenter = AuditPresenter(self.audit_view, self._audit, self)
        self.audit_view.export_requested.connect(
            lambda: self.reports_presenter.export_report("audit", "pdf"))

        # Paramètres
        self.settings_view = SettingsView()
        self.shell.set_page(Page.SETTINGS, self.settings_view)
        self.settings_presenter = SettingsPresenter(self.settings_view, self._settings, self)
        self.settings_view.save_requested.connect(self.settings_presenter.save_tariffs)
        self.settings_view.create_secretary_requested.connect(self.settings_presenter.create_secretary)
        self.settings_view.set_user_active_requested.connect(self._confirm_set_user_active)
        self.settings_view.reset_user_password_requested.connect(self._show_reset_user_password)
        self.settings_view.user_input_error.connect(
            lambda message: self.toast.popup("error", "Formulaire invalide", message))
        self.settings_presenter.user_operation_completed.connect(
            lambda message: self.toast.popup("success", "Utilisateurs", message))
        self.settings_presenter.saved.connect(
            lambda: self.toast.popup("success", "Paramètres enregistrés", "Les tarifs ont été mis à jour."))
        self.settings_presenter.save_failed.connect(
            lambda message: self.toast.popup("error", "Échec de l’enregistrement", message))

        # Connecter les signaux de la coquille
        self.shell.logout_requested.connect(self._on_logout)
        self.shell.password_requested.connect(self._show_change_password_dialog)
        self.shell.exercise_selected.connect(self._refresh_dashboard_notifications)
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

        # Connecter les signaux des vues
        vue = self.dashboard_view
        vue.payment_requested.connect(self._show_payment_dialog)
        vue.expense_requested.connect(self._show_expense_dialog)
        vue.member_requested.connect(lambda: self.shell.show_page(Page.MEMBERS))
        vue.collecte_requested.connect(lambda: self.toast.popup(
            "info", "Collecte décès", "Utilisez l'écran Cotisations funéraires"))
        vue.export_requested.connect(lambda: self.reports_presenter.export_report("balance", "pdf"))
        vue.export_excel_requested.connect(
            lambda: self.reports_presenter.export_report("balance", "excel"))
        vue.backup_requested.connect(lambda: self.shell.show_page(Page.BACKUPS))

        membres = self.members_view
        membres.export_requested.connect(
            lambda: self.reports_presenter.export_report("members", "pdf"))
        membres.export_excel_requested.connect(
            lambda: self.reports_presenter.export_report("members", "excel"))
        membres.add_requested.connect(self._show_add_member_dialog)
        membres.member_action_requested.connect(self._show_member_actions)

        # Cotisations mensuelles
        monthly = self.monthly_view
        monthly.export_requested.connect(
            lambda: self.reports_presenter.export_report("monthly", "pdf"))
        monthly.export_excel_requested.connect(
            lambda: self.reports_presenter.export_report("monthly", "excel"))
        monthly.record_payment_requested.connect(lambda c: self._show_payment_dialog(c))
        monthly.cell_clicked.connect(self._on_monthly_cell_clicked)

    def _refresh_dashboard_notifications(self, exercise_label: str) -> None:
        """Met à jour les alertes visibles dans la cloche depuis les alertes du dashboard."""
        if not hasattr(self, 'shell') or not hasattr(self, '_dashboard'):
            return
        try:
            alerts = self._dashboard.load(exercise_label).alerts
            notifications = [
                NotificationInfo(
                    {"danger": "Alerte", "warning": "Attention", "info": "Information"}.get(alert.kind, "Information"),
                    alert.text,
                    "Aujourd’hui",
                )
                for alert in alerts
            ]
            self.shell.set_notifications(notifications)
        except Exception:
            self.shell.set_notifications([])

    def _show_reset_user_password(self, user_id: int) -> None:
        dialog = ResetUserPasswordDialog(self)
        if dialog.exec():
            self.settings_presenter.reset_user_password(user_id, dialog.password())

    def _show_change_password_dialog(self) -> None:
        dialog = ChangePasswordDialog(self)
        if not dialog.exec():
            return
        current_password, new_password = dialog.passwords()
        try:
            self._auth.change_password(current_password, new_password)
        except Exception as error:
            self.toast.popup("error", "Mot de passe inchangé", str(error))
            return
        self.toast.popup("success", "Mot de passe modifié", "Ton mot de passe a été mis à jour.")

    def _confirm_set_user_active(self, user_id: int, actif: bool) -> None:
        if not actif:
            from PySide6.QtWidgets import QMessageBox

            answer = QMessageBox.question(
                self,
                "Désactiver le compte",
                "Cette personne ne pourra plus se connecter. Désactiver ce compte ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.settings_presenter.set_user_active(user_id, actif)

    def _on_export_completed(self, path: str) -> None:
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        detail = f"Fichier ouvert : {path}" if opened else f"Fichier enregistré : {path}"
        self.toast.popup("success", "Export généré", detail, msecs=7000)

    def _confirm_restore_backup(self, filename: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        answer = QMessageBox.warning(
            self,
            "Restaurer une sauvegarde",
            f"Restaurer {filename} remplacera toutes les données actuelles. "
            "Une copie de sécurité de l’état actuel sera créée avant la restauration. Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.backups_presenter.restore_backup(filename)

    def _on_backup_restored(self, message: str) -> None:
        conn = get_connection()
        try:
            exercices_list = exercices.list_all(conn)
            exercise_items = [ExerciseInfo(item.libelle, item.statut == "ouvert")
                              for item in exercices_list]
        finally:
            conn.close()
        self.shell.set_exercises(exercise_items)
        self.login_presenter._auth.session.logout()
        self.show_login()
        self.toast.popup(
            "success", "Sauvegarde restaurée",
            f"{message} Connecte-toi à nouveau avec un compte présent dans cette sauvegarde.",
            msecs=9000,
        )

    def _on_authenticated(self, user: UserInfo) -> None:
        # Initialiser l'application principale après authentification réussie
        shell_exists = hasattr(self, 'shell') and self.stack.indexOf(self.shell) >= 0
        previous_page = self.shell.current_key if shell_exists else None
        if not shell_exists:
            self._initialize_main_application()

        # Partager la session avec les adaptateurs
        session = self.login_presenter._auth.session
        self.members_presenter._port._session = session
        self.monthly_presenter._port._session = session
        self.funeral_presenter._port._session = session
        self.parallel_presenter._port._session = session
        self.fines_presenter._port._session = session
        self.expenses_presenter._port._session = session
        self.expenses_view.set_can_delete(session.can(Permission.DELETE))
        if isinstance(self.reports_presenter._port, ReportsAdapter):
            self.reports_presenter._port.set_session(session)
        if isinstance(self.backups_presenter._port, BackupsAdapter):
            self.backups_presenter._port.set_session(session)
        if isinstance(self.settings_presenter._port, SettingsAdapter):
            self.settings_presenter._port.set_session(session)

        self.shell.start(user)
        if previous_page is not None:
            self.shell.show_page(previous_page)
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
        self.toast.popup(
            "success", "Connexion réussie",
            f"Bienvenue, {user.full_name} · {user.role_label}", msecs=5000,
        )

    def _on_logout(self) -> None:
        self.shell.close_popover()
        # Déconnecter via l'adaptateur d'authentification
        if hasattr(self, '_auth') and self._auth:
            self._auth.logout()
        self.show_login()
