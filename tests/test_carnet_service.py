import sqlite3
import unittest
from datetime import date

from app.database.schema import migrate
from app.models.sexe import Sexe
from app.repositories import membres
from app.security import audit
from app.security.audit import Action
from app.security.session import CurrentUser, PermissionDenied, Role, Session
from app.services import carnet_service as carnets
from app.services import membre_service
from app.services.carnet_service import CarnetError

TODAY = date(2026, 10, 21)


class CarnetServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.conn.row_factory = sqlite3.Row
        migrate(self.conn)
        self.admin = Session()
        self.admin.login(CurrentUser(1, "ama", "Ama K.", Role.ADMINISTRATEUR))

    def test_format_par_defaut(self):
        self.assertEqual(carnets.preview(self.conn), "0001")

    def test_format_personnalise_admin_seulement(self):
        carnets.set_format(self.conn, self.admin, "lt-", 4, 43)
        self.assertEqual(carnets.preview(self.conn), "LT-0043")
        m = membre_service.create_membre(self.conn, self.admin, "Yawo Agbodjan", Sexe.HOMME, today=TODAY)
        self.assertEqual(m.numero_carnet, "LT-0043")
        self.assertEqual(carnets.preview(self.conn), "LT-0044")
        self.assertEqual(audit.list_entries(self.conn, action=Action.CARNET_FORMAT)[0]["objet"], "Numéros de carnet")
        sec = Session()
        sec.login(CurrentUser(2, "yawa", "Yawa D.", Role.SECRETAIRE))
        with self.assertRaises(PermissionDenied):
            carnets.set_format(self.conn, sec, "", 3, 1)

    def test_numero_deja_pris_est_saute(self):
        membres.create(self.conn, "0002", "Reprise Existante", Sexe.FEMME, date(2017, 9, 5))
        self.assertEqual(carnets.preview(self.conn), "0001")
        a = membre_service.create_membre(self.conn, self.admin, "Premier Nouveau", Sexe.HOMME, today=TODAY)
        b = membre_service.create_membre(self.conn, self.admin, "Second Nouveau", Sexe.HOMME, today=TODAY)
        self.assertEqual((a.numero_carnet, b.numero_carnet), ("0001", "0003"))

    def test_formatage_et_validation_centralisees_4_chiffres(self):
        self.assertEqual(carnets.formater_carnet(42), "0042")
        self.assertEqual(carnets.formater_carnet(42, prefix="LT-"), "LT-0042")
        self.assertEqual(carnets.valider_carnet("0042"), "0042")
        with self.assertRaises(CarnetError):
            carnets.valider_carnet("42")
        with self.assertRaises(CarnetError):
            carnets.valider_carnet("0042A")

    def test_format_invalide(self):
        for prefix, width, nxt in (("a b", 3, 1), ("ABCDEFGHIJK", 3, 1), ("", 0, 1), ("", 9, 1), ("", 3, 0)):
            with self.assertRaises(CarnetError, msg=str((prefix, width, nxt))):
                carnets.set_format(self.conn, self.admin, prefix, width, nxt)
        self.assertEqual(carnets.preview(self.conn), "0001")


if __name__ == "__main__":
    unittest.main()