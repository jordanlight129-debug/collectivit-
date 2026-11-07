import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog

from app.security.session import Role
from app.ui.dialogs.reset_user_password_dialog import ResetUserPasswordDialog
from app.ui.ports_settings import ManagedUser, SettingsData
from app.ui.theme import apply_theme
from app.ui.views.settings import SettingsView
from app.ui.widgets.button import AppButton


class SettingsUserManagementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)

    @staticmethod
    def _view(users):
        view = SettingsView()
        view.set_model(SettingsData("2025-2026", (), users=tuple(users)))
        return view

    def test_creation_confirme_le_mot_de_passe_et_emet_les_donnees(self):
        view = self._view((ManagedUser(1, "admin", "Administrateur", Role.ADMINISTRATEUR, True),))
        self.addCleanup(view.close)
        created = []
        errors = []
        view.create_secretary_requested.connect(lambda *values: created.append(values))
        view.user_input_error.connect(errors.append)
        view.secretary_identifier.setText("awa.dovi")
        view.secretary_name.setText("Awa Dovi")
        view.secretary_password.setText("Secret2026")
        view.secretary_password_confirmation.setText("Different2026")
        view.create_secretary_button.click()
        self.assertEqual(errors, ["Les deux mots de passe ne correspondent pas."])
        self.assertEqual(created, [])

        view.secretary_password_confirmation.setText("Secret2026")
        view.create_secretary_button.click()
        self.assertEqual(created, [("awa.dovi", "Awa Dovi", "Secret2026")])

    def test_liste_actions_et_limite_de_trois_secretaires(self):
        users = [ManagedUser(1, "admin", "Administrateur", Role.ADMINISTRATEUR, True)]
        users.extend(
            ManagedUser(index, f"secretary{index}", f"Secrétaire {index}", Role.SECRETAIRE, True)
            for index in range(2, 5)
        )
        view = self._view(users)
        self.addCleanup(view.close)

        self.assertEqual(view.users_table.rowCount(), 4)
        self.assertEqual(view.active_secretaries_label.text(), "Secrétaires actifs : 3/3")
        self.assertFalse(view.create_secretary_button.isEnabled())
        self.assertEqual(view.users_table.item(1, 2).text(), "Secrétaire")
        buttons = view.users_table.cellWidget(1, 4).findChildren(AppButton)
        self.assertEqual([button.text() for button in buttons],
                         ["Réinitialiser le mot de passe", "Désactiver"])

        reset_ids, active_changes = [], []
        view.reset_user_password_requested.connect(reset_ids.append)
        view.set_user_active_requested.connect(lambda user_id, active: active_changes.append((user_id, active)))
        buttons[0].click()
        buttons[1].click()
        self.assertEqual(reset_ids, [2])
        self.assertEqual(active_changes, [(2, False)])

    def test_dialogue_de_reinitialisation_valide_confirmation_et_politique(self):
        dialog = ResetUserPasswordDialog()
        self.addCleanup(dialog.close)
        dialog.password_field.setText("short")
        dialog.confirmation_field.setText("short")
        dialog._submit()
        self.assertIn("8 caractères", dialog.error_label.text())

        dialog.password_field.setText("Nouveau2026")
        dialog.confirmation_field.setText("Nouveau2026")
        dialog._submit()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(dialog.password(), "Nouveau2026")


if __name__ == "__main__":
    unittest.main()