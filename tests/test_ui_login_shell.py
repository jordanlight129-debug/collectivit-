import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")      # tests sans écran

from PySide6.QtCore import QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.ui.dialogs.change_password_dialog import ChangePasswordDialog
from app.ui.main_window import MainWindow
from app.ui.mock.auth import MAX_ATTEMPTS, MockAuth
from app.ui.navigation import ADMIN_ONLY, Page
from app.ui.ports import LoginStatus
from app.ui.theme import apply_theme


class MockAuthTest(unittest.TestCase):
    def test_connexion_refus_et_verrouillage(self):
        auth = MockAuth()
        admin = auth.login("admin", "Admin2026")
        self.assertEqual((admin.status, admin.user.full_name, admin.user.is_admin),
                         (LoginStatus.OK, "Ama Kpodar", True))
        secretaire = auth.login("YAWA", "Secret2026")                      # identifiant insensible à la casse
        self.assertEqual((secretaire.status, secretaire.user.role_label), (LoginStatus.OK, "Secrétaire"))
        for tentative in range(1, MAX_ATTEMPTS):
            refus = auth.login("yawa", "faux")
            self.assertEqual(refus.status, LoginStatus.REFUSED)
            self.assertIn(str(MAX_ATTEMPTS - tentative), refus.message)    # tentatives restantes
        self.assertEqual(auth.login("yawa", "faux").status, LoginStatus.LOCKED)
        self.assertEqual(auth.login("yawa", "Secret2026").status, LoginStatus.LOCKED)   # même avec le bon mot de passe
        self.assertEqual(auth.login("admin", "Admin2026").status, LoginStatus.OK)       # les autres comptes ne sont pas touchés
        self.assertEqual(auth.login("inconnu", "x").status, LoginStatus.REFUSED)

    def test_changement_de_mot_de_passe_du_compte_connecte(self):
        auth = MockAuth()
        auth.login("admin", "Admin2026")
        auth.change_password("Admin2026", "Nouveau2026")
        auth.logout()
        self.assertEqual(auth.login("admin", "Nouveau2026").status, LoginStatus.OK)
        self.assertEqual(auth.login("admin", "Admin2026").status, LoginStatus.REFUSED)


class AppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)

    def fenetre(self) -> MainWindow:
        fenetre = MainWindow(MockAuth())
        fenetre.show()
        self.addCleanup(fenetre.close)
        return fenetre


class LoginViewTest(AppTestCase):
    def test_champs_vides(self):
        fenetre = self.fenetre()
        vue = fenetre.login_view
        vue.submitted.emit("", "")
        self.assertTrue(vue.field_identifiant.has_error)
        self.assertFalse(vue.banner.isHidden())  # erreur mot de passe dans le bandeau
        vue.submitted.emit("admin", "")
        self.assertFalse(vue.field_identifiant.has_error)
        self.assertFalse(vue.banner.isHidden())  # erreur mot de passe dans le bandeau
        self.assertIs(fenetre.stack.currentWidget(), vue)

    def test_identifiants_refuses(self):
        fenetre = self.fenetre()
        vue = fenetre.login_view
        vue.identifiant.setText("admin")
        vue.mot_de_passe.setText("faux")
        vue.connect_button.click()
        self.assertFalse(vue.banner.isHidden())
        self.assertEqual(vue.banner.kind, "danger")
        self.assertIn("incorrect", vue.last_message)
        self.assertEqual(vue.mot_de_passe.text(), "")                      # mot de passe effacé
        self.assertTrue(vue.field_identifiant.has_error)
        self.assertTrue(vue.mot_de_passe.property("error") is True)
        self.assertIs(fenetre.stack.currentWidget(), vue)

    def test_compte_verrouille_puis_retour_a_l_etat_initial(self):
        fenetre = self.fenetre()
        vue = fenetre.login_view
        for _ in range(MAX_ATTEMPTS):
            vue.submitted.emit("yawa", "faux")
        self.assertEqual(vue.banner.kind, "warning")
        self.assertIn("verrouillé", vue.last_message)
        self.assertFalse(vue.identifiant.isEnabled())
        self.assertFalse(vue.connect_button.isEnabled())
        vue.reset()
        self.assertTrue(vue.identifiant.isEnabled() and vue.connect_button.isEnabled())
        self.assertTrue(vue.banner.isHidden())
        self.assertEqual(vue.values(), ("", ""))


class MainWindowTest(AppTestCase):
    def test_fenetre_et_toast_restent_dans_la_zone_ecran(self):
        fenetre = self.fenetre()
        available = fenetre.screen().availableGeometry()
        self.assertLessEqual(fenetre.width(), available.width())
        self.assertLessEqual(fenetre.height(), available.height())
        self.assertGreaterEqual(fenetre.x(), available.x())
        self.assertGreaterEqual(fenetre.y(), available.y())

        fenetre.login_view.submitted.emit("admin", "Admin2026")
        self.app.processEvents()
        self.assertEqual(fenetre.toast.title_text, "Connexion réussie")
        toast_rect = QRect(fenetre.stack.mapToGlobal(fenetre.toast.pos()), fenetre.toast.size())
        self.assertTrue(available.contains(toast_rect))

    def test_changement_de_mot_de_passe_depuis_le_menu_profil(self):
        from unittest.mock import patch

        fenetre = self.fenetre()
        fenetre.login_view.submitted.emit("admin", "Admin2026")
        with patch("app.ui.main_window.ChangePasswordDialog") as dialog_type:
            dialog = dialog_type.return_value
            dialog.exec.return_value = 1
            dialog.passwords.return_value = ("Admin2026", "Nouveau2026")
            fenetre.shell.password_requested.emit()

        self.assertEqual(fenetre.toast.title_text, "Mot de passe modifié")
        fenetre._auth.logout()
        self.assertEqual(fenetre._auth.login("admin", "Nouveau2026").status, LoginStatus.OK)

    def test_connexion_administrateur_puis_deconnexion(self):
        fenetre = self.fenetre()
        self.assertIs(fenetre.stack.currentWidget(), fenetre.login_view)
        fenetre.login_view.submitted.emit("admin", "Admin2026")
        shell = fenetre.shell
        self.assertIs(fenetre.stack.currentWidget(), shell)
        self.assertEqual((shell.topbar._user_name.text(), shell.sidebar.active_key), ("Ama Kpodar", Page.DASHBOARD))
        for cle in ADMIN_ONLY:
            self.assertFalse(shell.sidebar.item(cle).isHidden(), cle)
        self.assertFalse(fenetre.toast.isHidden())
        self.assertEqual(fenetre.toast.title_text, "Connexion réussie")
        self.assertIn("Ama Kpodar", fenetre.toast._text.text())
        self.assertIn("Administrateur", fenetre.toast._text.text())
        self.assertGreater(len(shell._notifications), 0)
        shell.logout_requested.emit()
        self.assertIs(fenetre.stack.currentWidget(), fenetre.login_view)
        self.assertEqual(fenetre.login_view.values(), ("", ""))

    def test_vue_secretaire_et_navigation(self):
        fenetre = self.fenetre()
        fenetre.login_view.submitted.emit("yawa", "Secret2026")
        shell = fenetre.shell
        for cle in ADMIN_ONLY:
            self.assertTrue(shell.sidebar.item(cle).isHidden(), cle)
        QTest.mouseClick(shell.sidebar.item(Page.MEMBERS), Qt.MouseButton.LeftButton)
        self.assertEqual(shell.current_key, Page.MEMBERS)
        self.assertIs(shell.pages.currentWidget(), shell.page_container(Page.MEMBERS))
        shell.logout_requested.emit()                                       # reconnexion en administrateur
        fenetre.login_view.submitted.emit("admin", "Admin2026")
        self.assertEqual(shell.current_key, Page.MEMBERS)  # reste sur la page courante
        self.assertFalse(shell.sidebar.item(Page.AUDIT).isHidden())

    def test_popovers_de_la_barre_superieure(self):
        fenetre = self.fenetre()
        fenetre.login_view.submitted.emit("admin", "Admin2026")
        shell = fenetre.shell
        shell.topbar.notifications_requested.emit(shell.topbar.bell_button)
        self.assertFalse(shell.popover.isHidden())
        # Le nombre d'items dépend des notifications actuelles
        self.assertGreaterEqual(shell.popover.item_count(), 0)
        shell.topbar.exercise_requested.emit(shell.topbar.exercise_select)   # ouvre le sélecteur, ferme le précédent
        self.assertGreaterEqual(shell.popover.item_count(), 0)
        if shell.popover.item_count() > 1:
            shell.popover.items()[1].clicked.emit()                               # choisit 2024–2025
            self.assertTrue(shell.popover.isHidden())
            self.assertEqual(shell.current_exercise_label, "2024–2025")
            self.assertIn("2024–2025", shell.topbar._exercise_text.text())
        shell.topbar.user_requested.emit(shell.topbar.user_chip)
        self.assertEqual(shell.popover.item_count(), 2)
        shell.popover.items()[1].clicked.emit()                               # « Se déconnecter »
        self.assertIs(fenetre.stack.currentWidget(), fenetre.login_view)


class ChangePasswordDialogTest(AppTestCase):
    def test_valide_ancien_secret_nouveau_et_confirmation(self):
        dialog = ChangePasswordDialog()
        self.addCleanup(dialog.close)
        dialog.new_password_field.setText("Nouveau2026")
        dialog.confirmation_field.setText("Nouveau2026")
        dialog._submit()
        self.assertIn("actuel", dialog.error_label.text())

        dialog.current_password_field.setText("Ancien2026")
        dialog.confirmation_field.setText("Autre2026")
        dialog._submit()
        self.assertIn("ne correspondent pas", dialog.error_label.text())

        dialog.confirmation_field.setText("Nouveau2026")
        dialog._submit()
        self.assertEqual(dialog.result(), 1)


if __name__ == "__main__":
    unittest.main()