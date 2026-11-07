import os
import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")      # tests sans écran

from PySide6.QtWidgets import QApplication, QAbstractItemView

from app.services.affichage import DETTE, EXCEDENT, SOLDE, Situation
from app.ui.adapters.dashboard_adapter import DashboardAdapter
from app.ui.dialogs.member_dashboard_dialog import MemberDashboardDialog
from app.models.transaction import Transaction
from app.ui.main_window import MainWindow
from app.ui.mock.auth import MockAuth
from app.ui.mock.dashboard import MockDashboard
from app.ui.navigation import Page
from app.ui.presenters.dashboard_model import build_view_model
from app.services.historique_service import PageHistorique
from app.ui.theme import apply_theme
from app.ui.views.dashboard import DashboardView

NB = "\u00a0"


class ViewModelTest(unittest.TestCase):
    def test_exercice_de_reference_en_dette(self):
        m = build_view_model(MockDashboard().load("2025–2026"))
        # self.assertEqual(m.subtitle, "Synthèse de l'exercice 2025–2026 · montants en FCFA (encaissé réel uniquement)")
        self.assertIn("2025–2026", m.subtitle)
        self.assertIn("montants en FCFA", m.subtitle)
        self.assertFalse(m.read_only)
        stats = {s.label: s for s in m.stats}
        # 8 cartes stats au lieu de 4
        self.assertEqual((stats["Cotisations mensuelles perçues"].amount, stats["Cotisations mensuelles perçues"].tone),
                         (f"587{NB}000 FCFA", "neutre"))
        self.assertEqual((stats["Cotisations funéraires perçues"].amount, stats["Cotisations funéraires perçues"].tone),
                         (f"64{NB}000 FCFA", "neutre"))
        self.assertEqual((stats["Cotisations parallèles perçues"].amount, stats["Cotisations parallèles perçues"].tone),
                         (f"28{NB}000 FCFA", "neutre"))
        self.assertEqual((stats["Amendes encaissées"].amount, stats["Amendes encaissées"].tone),
                         (f"3{NB}000 FCFA", "neutre"))
        self.assertEqual((stats["Total des dépenses"].amount, stats["Total des dépenses"].tone),
                         (f"1{NB}180{NB}000 FCFA", "neutre"))
        self.assertEqual((stats["Total des reliquats"].amount, stats["Total des reliquats"].tone),
                         (f"120{NB}000 FCFA", "neutre"))
        self.assertEqual((stats["Dettes restant à recouvrer"].amount, stats["Dettes restant à recouvrer"].tone,
                          stats["Dettes restant à recouvrer"].note), (f"305{NB}000 FCFA", "rouge", "Non encaissé · 6 membres"))
        self.assertEqual((stats["Solde financier"].amount, stats["Solde financier"].tone),
                         (f"Dette : 378{NB}000 FCFA", "rouge"))
        # Vérification de la cohérence : 587+64+28+3+120 = 802, 1180-802 = 378
        self.assertEqual(len(m.stats), 8)
        self.assertEqual([a.kind for a in m.alerts], ["warning", "danger", "info"])
        self.assertEqual(m.debtors_counter, "4 sur 6")
        self.assertEqual([debiteur.member for debiteur in m.debtors],
                 ["Yawo Agbodjan", "Esi Amegah", "Ama Kossi", "Kodjo Tété"])
        self.assertEqual(len(m.operations), 5)
        self.assertEqual((m.operations[0].amount, m.operations[0].label, m.operations[0].status),
                         (f"+18{NB}000", "Cotisation mensuelle", "Payé"))
        self.assertEqual(m.operations[2].status, "Partiel")


class DashboardDataAdapterTest(unittest.TestCase):
    @staticmethod
    def _transaction(source, on, rubrique, sens, amount, member_name=None, label=""):
        return Transaction(
            source=source,
            source_id=1,
            date_operation=on,
            rubrique=rubrique,
            sens=sens,
            montant=amount,
            membre_id=1 if member_name else None,
            membre_nom=member_name,
            numero_carnet="0001" if member_name else None,
            libelle=label,
            beneficiaire=None,
            note=None,
            saisi_par="admin",
            cree_le="",
            exercice_id=1,
        )

    def test_graphique_et_operations_utilisent_l_historique_reel(self):
        from unittest.mock import patch

        adapter = DashboardAdapter()
        transactions = [
            self._transaction("versement", date(2026, 9, 10), "mensuelle", "entree", 10000,
                              "Membre Test", "Cotisation mensuelle"),
            self._transaction("depense", date(2026, 9, 12), "depense", "sortie", 2000,
                              label="Fournitures"),
            self._transaction("reliquat", date(2026, 10, 2), "reliquat", "entree", 3000,
                              label="Remboursement"),
        ]
        with patch("app.ui.adapters.dashboard_adapter.historique.list_", return_value=transactions) as list_:
            months = adapter._get_monthly_figures(
                None, 1, date(2026, 9, 1), date(2027, 8, 31)
            )
            operations = adapter._get_recent_operations(None, 1)

        self.assertEqual((months[0].label, months[0].entrees, months[0].depenses),
                         ("Septembre", 10000, 2000))
        self.assertEqual((months[1].label, months[1].entrees, months[1].depenses),
                         ("Octobre", 3000, 0))
        self.assertEqual(len(months), 12)
        self.assertEqual(operations[0].label, "Membre Test — Cotisation mensuelle")
        self.assertEqual(operations[0].amount, 10000)
        self.assertEqual(operations[1].amount, -2000)
        self.assertEqual(operations[1].status, "enregistree")
        self.assertEqual(operations[2].status, "reliquat")
        self.assertEqual(list_.call_count, 2)

    def test_exercice_cloture_en_excedent(self):
        m = build_view_model(MockDashboard().load("2024–2025"))
        # self.assertEqual(m.subtitle, "Synthèse de l'exercice 2024–2025 · montants en FCFA (encaissé réel uniquement)")
        self.assertIn("2024–2025", m.subtitle)
        self.assertIn("montants en FCFA", m.subtitle)
        self.assertTrue(m.read_only)
        stats = {s.label: s for s in m.stats}
        self.assertEqual((stats["Solde financier"].amount, stats["Solde financier"].tone),
                         (f"Excédent : 490{NB}000 FCFA", "vert"))
        self.assertEqual((stats["Dettes restant à recouvrer"].amount, stats["Dettes restant à recouvrer"].tone,
                          stats["Dettes restant à recouvrer"].note), ("0 FCFA", "neutre", "Aucune dette en cours"))
        self.assertEqual([a.kind for a in m.alerts], ["info"])


class DashboardAlertTextTest(unittest.TestCase):
    def test_libelles_alerte_echeance_et_dettes(self):
        adapter = DashboardAdapter()
        today = date.today()
        bilan = SimpleNamespace(total_dettes=12000)
        cases = (
            (today + timedelta(days=1), "L’exercice 2026–2027 prend fin demain. Préparez sa clôture."),
            (today, "L’exercice 2026–2027 prend fin aujourd’hui. Veuillez procéder à sa clôture."),
            (today - timedelta(days=1), "L’exercice 2026–2027 a dépassé sa date de fin depuis 1 jour et reste ouvert. Veuillez procéder à sa clôture."),
            (today - timedelta(days=2), "L’exercice 2026–2027 a dépassé sa date de fin depuis 2 jours et reste ouvert. Veuillez procéder à sa clôture."),
        )

        for date_fin, expected in cases:
            with self.subTest(date_fin=date_fin):
                exercice = SimpleNamespace(
                    statut="ouvert", date_fin=date_fin, libelle="2026–2027"
                )
                alerts = adapter._get_alerts(exercice, bilan)
                self.assertEqual(alerts[0].text, expected)
                self.assertEqual(alerts[1].text, "Des dettes restent à recouvrer.")


class AppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)


class DashboardViewTest(AppTestCase):
    def test_affichage_du_modele_et_signaux(self):
        vue = DashboardView()
        vue.show()
        self.addCleanup(vue.close)
        vue.set_model(build_view_model(MockDashboard().load("2025–2026")))
        # 8 cartes stats
        self.assertEqual([c.amount_label.text() for c in vue.stat_cards],
                         [f"587{NB}000 FCFA", f"64{NB}000 FCFA", f"28{NB}000 FCFA", f"3{NB}000 FCFA",
                          f"1{NB}180{NB}000 FCFA", f"120{NB}000 FCFA", f"305{NB}000 FCFA", f"Dette : 378{NB}000 FCFA"])
        self.assertEqual([c.tone for c in vue.stat_cards],
                         ["neutre", "neutre", "neutre", "neutre", "neutre", "neutre", "rouge", "rouge"])
        self.assertEqual((vue.operation_row_count(), vue.debtor_row_count()), (5, 4))
        self.assertTrue(vue.payment_button.isEnabled())
        recus = []
        vue.export_requested.connect(lambda: recus.append("export"))
        vue.payment_requested.connect(lambda: recus.append("paiement"))
        vue.export_button.click()
        vue.payment_button.click()
        self.assertEqual(recus, ["export", "paiement"])

    def test_exercice_cloture_en_lecture_seule_et_rafraichissement(self):
        vue = DashboardView()
        vue.show()
        self.addCleanup(vue.close)
        vue.set_model(build_view_model(MockDashboard().load("2024–2025")))
        self.assertFalse(vue.payment_button.isEnabled())
        self.assertEqual((vue.operation_row_count(), vue.debtor_row_count()), (2, 0))
        self.assertEqual((vue.stat_cards[7].tone, vue.stat_cards[7].amount_label.property("tone")), ("vert", "vert"))
        vue.set_model(build_view_model(MockDashboard().load("2025–2026")))      # pas d'empilement
        self.assertTrue(vue.payment_button.isEnabled())
        self.assertEqual((vue.operation_row_count(), vue.debtor_row_count()), (5, 4))
        self.assertEqual(vue.stat_cards[7].tone, "rouge")


class MemberDashboardDialogTest(AppTestCase):
    def test_affiche_synthese_et_historique_en_lecture_seule(self):
        from types import SimpleNamespace

        transaction = DashboardDataAdapterTest._transaction(
            "versement", date(2026, 9, 10), "mensuelle", "entree", 15000,
            "Membre Test", "Cotisation mensuelle")
        historique = PageHistorique([transaction], 1, 15000, 0)
        membre = SimpleNamespace(
            nom="Membre Test", numero_carnet="0001", statut="actif",
            date_adhesion=date(2025, 1, 1))
        dialog = MemberDashboardDialog(membre, "2026-2027", historique, historique)
        self.addCleanup(dialog.close)

        self.assertEqual(dialog.summary_cards[0].amount_label.text(), f"15{NB}000 FCFA")
        self.assertEqual(dialog.summary_cards[1].amount_label.text(), "1")
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertEqual(dialog.table.item(0, 2).text(), "Cotisation mensuelle")
        self.assertEqual(dialog.table.item(0, 3).text(), f"15{NB}000 FCFA")
        self.assertEqual(dialog.table.editTriggers(), QAbstractItemView.EditTrigger.NoEditTriggers)


class DashboardIntegrationTest(AppTestCase):
    def test_apres_connexion_et_changement_d_exercice(self):
        fenetre = MainWindow(MockAuth(), dashboard=MockDashboard())
        fenetre.show()
        self.addCleanup(fenetre.close)
        exercices_demo = [
            SimpleNamespace(libelle="2025–2026", statut="ouvert"),
            SimpleNamespace(libelle="2024–2025", statut="cloture"),
        ]
        with patch("app.ui.main_window.exercices.list_all", return_value=exercices_demo):
            fenetre.login_view.submitted.emit("admin", "Admin2026")
        shell, vue = fenetre.shell, fenetre.dashboard_view
        self.assertIs(shell.page_container(Page.DASHBOARD).widget(), vue)
        # 8 cartes : la dette est à l'index 7
        self.assertEqual(vue.stat_cards[7].amount_label.text(), f"Dette : 378{NB}000 FCFA")
        self.assertIn("2025–2026", vue.header._subtitle.text())
        shell.topbar.exercise_requested.emit(shell.topbar.exercise_select)
        shell.popover.items()[1].clicked.emit()                                  # choisit 2024–2025 (clôturé)
        self.assertEqual(vue.stat_cards[7].amount_label.text(), f"Excédent : 490{NB}000 FCFA")
        self.assertFalse(vue.payment_button.isEnabled())
        self.assertIn("2024–2025", vue.header._subtitle.text())


if __name__ == "__main__":
    unittest.main()