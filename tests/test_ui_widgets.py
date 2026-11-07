import os
import unittest
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")      # tests sans écran

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QWidget

from app.services.affichage import DETTE, EXCEDENT, SOLDE, Situation
from app.ui.format import format_date, format_fcfa
from app.ui.navigation import ADMIN_ONLY, NAV_ITEMS, Page, allowed_keys
from app.ui.theme import apply_theme
from app.ui.widgets.badge import Badge, status_badge
from app.ui.widgets.banner import Banner, Toast
from app.ui.widgets.button import AppButton, IconButton, Variant
from app.ui.widgets.card import StatCard
from app.ui.widgets.dialog import FormDialog
from app.ui.widgets.field import FormField
from app.ui.widgets.form import NumberInput, TextInput
from app.ui.widgets.labels import SituationLabel
from app.ui.widgets.page_header import PageHeader
from app.ui.widgets.sidebar import Sidebar
from app.ui.widgets.statusbar import AppStatusBar
from app.ui.widgets.topbar import TopBar


class FormatTest(unittest.TestCase):
    def test_montants_et_dates(self):
        self.assertEqual(format_fcfa(1250000), "1\u00a0250\u00a0000 FCFA")
        self.assertEqual(format_fcfa(0), "0 FCFA")
        self.assertEqual(format_fcfa(5000, unite=False), "5\u00a0000")
        self.assertEqual(format_date(date(2026, 6, 5)), "05/06/2026")
        with self.assertRaises(ValueError):
            format_fcfa(-1)


class WidgetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)

    def test_boutons(self):
        b = AppButton("Enregistrer", Variant.PRIMARY, "plus")
        self.assertEqual((b.variant, b.height(), b.text()), ("primary", 36, "Enregistrer"))
        self.assertFalse(b.icon().isNull())
        clics = []
        b.clicked.connect(lambda: clics.append(1))
        b.click()
        self.assertEqual(clics, [1])
        b.set_variant(Variant.DANGER)
        self.assertEqual(b.property("variant"), "danger")
        with self.assertRaises(ValueError):
            b.set_variant("inconnue")
        self.assertEqual((IconButton("bell", "Notifications").width(), AppButton("Voir", Variant.LINK).variant), (36, "link"))

    def test_badges_et_statuts(self):
        impaye = status_badge("impaye")
        self.assertEqual((impaye.text(), impaye.kind), ("Dette", "danger"))
        self.assertEqual((status_badge("paye").text(), status_badge("decede").kind), ("Payé", "neutral"))
        with self.assertRaises(ValueError):
            Badge("x", "inconnu")
        with self.assertRaises(ValueError):
            status_badge("inconnu")

    def test_cartes_statistiques(self):
        carte = StatCard("Dettes restant à recouvrer", "1\u00a0430\u00a0000 FCFA", "Non encaissé", "rouge")
        self.assertEqual((carte.tone, carte.amount_label.property("tone")), ("rouge", "rouge"))
        carte.set_content("Solde financier", "Excédent : 122\u00a0000 FCFA", "", "vert")
        self.assertEqual((carte.amount_label.text(), carte.note_label.isHidden(), carte.tone),
                         ("Excédent : 122\u00a0000 FCFA", True, "vert"))
        with self.assertRaises(ValueError):
            carte.set_tone("bleu")

    def test_etiquette_de_situation(self):
        etiquette = SituationLabel()
        etiquette.set_situation(Situation(DETTE, 378000))
        self.assertEqual((etiquette.text(), etiquette.property("tone")), ("Dette : 378\u00a0000 FCFA", "rouge"))
        etiquette.set_situation(Situation(EXCEDENT, 122000))
        self.assertEqual(etiquette.property("tone"), "vert")
        etiquette.set_situation(Situation(SOLDE, 0))
        self.assertEqual((etiquette.text(), etiquette.property("tone")), ("Soldé : 0 FCFA", "neutre"))

    def test_champ_avec_erreur(self):
        champ = FormField("N° de carnet", QLineEdit(), hint="Attribué automatiquement", required=True)
        self.assertFalse(champ.has_error)
        self.assertEqual(champ._message.text(), "Attribué automatiquement")
        champ.set_error("Ce numéro est déjà attribué.")
        self.assertTrue(champ.has_error)
        self.assertEqual((champ.widget.property("error"), champ._message.text(), champ._message.property("role")),
                         (True, "Ce numéro est déjà attribué.", "field-error"))
        champ.set_error(None)
        self.assertEqual((champ.has_error, champ._message.property("role")), (False, "caption"))

    def test_bandeaux_et_messages(self):
        bandeau = Banner("warning", "Attention")
        self.assertEqual(bandeau.kind, "warning")
        bandeau.set_kind("danger")
        self.assertEqual(bandeau.property("kind"), "danger")
        with self.assertRaises(ValueError):
            Banner("autre", "x")
        parent = QWidget()
        parent.resize(900, 600)
        toast = Toast(parent)
        self.assertTrue(toast.isHidden())
        toast.popup("success", "Versement enregistré", "18 000 FCFA imputés.", msecs=50)
        self.assertFalse(toast.isHidden())
        self.assertEqual((toast.kind, toast.title_text), ("success", "Versement enregistré"))
        self.assertLessEqual(toast.geometry().right(), parent.width())
        self.assertLessEqual(toast.geometry().bottom(), parent.height())

        parent.resize(360, 400)
        parent.show()
        title = "Confirmation d’une opération financière terminée avec succès"
        message = "Le versement a été enregistré et son reçu est disponible dans l’historique du membre."
        toast.popup("success", title, message)
        self.app.processEvents()
        self.assertTrue(toast._title.wordWrap())
        self.assertGreater(toast._title.height(), toast._title.fontMetrics().height())
        self.assertEqual(toast.width(), parent.width() - 48)
        self.assertGreaterEqual(toast._timer.interval(), 3500)
        self.assertLessEqual(toast.geometry().right() + 1, parent.width())
        self.assertLessEqual(toast.geometry().bottom() + 1, parent.height())
        with self.assertRaises(ValueError):
            toast.popup("autre", "x")

    def test_barre_laterale(self):
        sidebar = Sidebar(brand_name="Collectivité LANTCHIBLE", brand_sub="Gestion d’association",
                          brand_initials="CL", footer="Version 1.0")
        sidebar.set_active(Page.DASHBOARD)
        sidebar.show()
        self.assertEqual((len(NAV_ITEMS), sidebar.active_key, sidebar.item(Page.DASHBOARD).active), (13, "dashboard", True))
        recu = []
        sidebar.navigate.connect(recu.append)
        QTest.mouseClick(sidebar.item(Page.MEMBERS), Qt.MouseButton.LeftButton)
        self.assertEqual(recu, ["members"])
        self.assertEqual((sidebar.active_key, sidebar.item(Page.MEMBERS).active, sidebar.item(Page.DASHBOARD).active),
                         ("members", True, False))
        sidebar.set_allowed(allowed_keys(False))                      # vue secrétaire
        for cle in ADMIN_ONLY:
            self.assertTrue(sidebar.item(cle).isHidden(), cle)
        self.assertFalse(sidebar.item(Page.MEMBERS).isHidden())
        sidebar.set_allowed(None)
        self.assertFalse(sidebar.item(Page.AUDIT).isHidden())
        with self.assertRaises(KeyError):
            sidebar.set_active("inconnue")

    def test_barre_superieure(self):
        barre = TopBar("Collectivité LANTCHIBLE")
        barre.set_exercise("Exercice 2025–2026 (sept. → août)")
        barre.set_user("Ama Kpodar", "Administrateur")
        barre.show()
        self.assertEqual((barre._avatar.text(), barre._user_name.text(), barre._user_role.text()),
                         ("AK", "Ama Kpodar", "Administrateur"))
        ancres = []
        barre.exercise_requested.connect(lambda w: ancres.append(("exercice", w)))
        barre.notifications_requested.connect(lambda w: ancres.append(("notifications", w)))
        barre.user_requested.connect(lambda w: ancres.append(("utilisateur", w)))
        QTest.mouseClick(barre.exercise_select, Qt.MouseButton.LeftButton)
        barre.bell_button.click()
        QTest.mouseClick(barre.user_chip, Qt.MouseButton.LeftButton)
        self.assertEqual([nom for nom, _ in ancres], ["exercice", "notifications", "utilisateur"])
        self.assertIs(ancres[1][1], barre.bell_button)
        barre.user_chip.setFocus()
        QTest.keyClick(barre.user_chip, Qt.Key.Key_Return)
        self.assertEqual(len(ancres), 4)

    def test_barre_d_etat_et_en_tete(self):
        etat = AppStatusBar()
        etat.set_database(True, "Base de données locale : connectée")
        self.assertEqual(etat._dot.property("state"), "ok")
        etat.set_database(False, "Base inaccessible")
        self.assertEqual(etat._dot.property("state"), "error")
        etat.set_notice("Données fictives de démonstration")
        self.assertFalse(etat._notice.isHidden())
        etat.set_notice(None)
        self.assertTrue(etat._notice.isHidden())
        en_tete = PageHeader("Membres", "42 membres")
        en_tete.add_action(AppButton("Ajouter un membre", Variant.PRIMARY, "plus"))
        en_tete.set_subtitle("")
        self.assertEqual((en_tete.action_count(), en_tete._subtitle.isHidden()), (1, True))

    def test_previsualisation_d_un_formulaire_avec_montant(self):
        class PreviewDialog(FormDialog):
            def __init__(self):
                super().__init__("Aperçu de la saisie")
                self.libelle = TextInput("Libellé", required=True)
                self.montant = NumberInput("Montant reçu (FCFA)", required=True, min_value=1)
                self.add_field(self.libelle)
                self.add_field(self.montant)
                self.libelle.set_value("Cotisation mensuelle")
                self.montant.input_widget.setValue(18000)

            def get_data(self):
                return {"libelle": self.libelle.value(), "montant": int(self.montant.value())}

        dialog = PreviewDialog()
        preview = dialog.preview_text()
        self.assertIn("Cotisation mensuelle", preview)
        self.assertIn("Montant reçu", preview)
        self.assertIn("18 000 FCFA", preview)


if __name__ == "__main__":
    unittest.main()