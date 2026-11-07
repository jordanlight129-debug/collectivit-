import unittest
from datetime import date
from decimal import Decimal

from app.database.connection import get_connection
from app.database.schema import migrate
from app.repositories import utilisateurs
from app.security import audit
from app.security.audit import Action
from app.security.session import CurrentUser, PermissionDenied, Role, Session
from app.services import depense_service as svc
from app.services import exercice_service
from app.services.depense_service import DepenseError

TODAY = date(2026, 8, 31)

DEPENSES = [   # libellé, bénéficiaire, prévu, dépensé, date
    ("Achat de chaises", "Ets Kokou", 120000, 105000, date(2026, 6, 16)),
    ("Location salle assemblée", "Salle Le Baobab", 150000, 150000, date(2026, 6, 2)),
    ("Aide funérailles — Kossi Ayité", "Famille Ayité", 300000, 255000, date(2026, 5, 20)),
    ("Sonorisation fête", "Studio Éclair", 200000, 200000, date(2026, 4, 12)),
    ("Tenues de l’association", "Atelier Mawu", 450000, 390000, date(2026, 3, 3)),
    ("Frais de gestion", None, 80000, 80000, date(2026, 2, 10)),
]


class DepenseServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.addCleanup(self.conn.close)
        migrate(self.conn)
        utilisateurs.create(self.conn, "ama", "Ama K.", "x", Role.ADMINISTRATEUR)
        utilisateurs.create(self.conn, "yawa", "Yawa D.", "x", Role.SECRETAIRE)
        self.admin, self.sec = Session(), Session()
        self.admin.login(CurrentUser(1, "ama", "Ama K.", Role.ADMINISTRATEUR))
        self.sec.login(CurrentUser(2, "yawa", "Yawa D.", Role.SECRETAIRE))
        self.ex = exercice_service.create_exercice(self.conn, self.admin, 2025, 18000, 14000)

    def _dep(self, libelle, depense, prevu=None, beneficiaire=None, d=date(2026, 6, 16), session=None):
        return svc.enregistrer_depense(self.conn, session or self.sec, libelle, depense, beneficiaire,
                                       prevu, d, today=TODAY)

    def _maquette(self):
        for libelle, bene, prevu, depense, d in DEPENSES:
            self._dep(libelle, depense, prevu, bene, d)

    def test_depense_avec_reliquat_lie_a_sa_depense(self):
        d = self._dep("Achat de chaises", 105000, 120000, "Ets Kokou")
        self.assertEqual((d.montant_prevu, d.montant_depense, d.reliquat_montant), (120000, 105000, 15000))
        lignes, total = svc.list_reliquats(self.conn, self.ex.id)
        self.assertEqual((len(lignes), total), (1, 15000))
        r = lignes[0].reliquat
        self.assertEqual((r.nom, r.montant, r.depense_id, r.date_reliquat),
                         ("Reliquat — Achat de chaises", 15000, d.id, date(2026, 6, 16)))
        self.assertEqual(lignes[0].depense_libelle, "Achat de chaises")
        e = audit.list_entries(self.conn)[0]
        self.assertEqual((e["action"], e["identifiant"]), (Action.DEPENSE_AJOUT, "yawa"))
        self.assertIn("reliquat", e["detail"])

    def test_montants_de_depense_sont_des_decimal(self):
        depense = self._dep("Achat précis", Decimal("105000"), Decimal("120000"))

        self.assertIsInstance(depense.montant_prevu, Decimal)
        self.assertIsInstance(depense.montant_depense, Decimal)
        self.assertIsInstance(depense.reliquat_montant, Decimal)
        self.assertEqual(depense.reliquat_montant, Decimal("15000"))
        self.assertIsInstance(svc.resume(self.conn, self.ex.id).depense, Decimal)

    def test_sans_reliquat_prevu_omis_et_depassement(self):
        egal = self._dep("Location salle", 150000, 150000)
        omis = self._dep("Sonorisation", 200000)
        self.assertEqual((egal.reliquat_montant, omis.montant_prevu), (0, 200000))
        depasse = self._dep("Réparation toiture", 120000, 100000)
        self.assertEqual((depasse.reliquat_montant, depasse.depassement), (0, 20000))
        lignes, total = svc.list_reliquats(self.conn, self.ex.id)
        self.assertEqual((lignes, total), ([], 0))

    def test_validations_rien_n_est_ecrit(self):
        ok = date(2026, 6, 16)
        cas = [
            dict(libelle=""),
            dict(depense=-1), dict(depense=12.5), dict(depense=Decimal("12.5")), dict(depense=True),
            dict(prevu=-1), dict(prevu=12.5),
            dict(depense=0, prevu=0),
            dict(d=date(2026, 9, 1)),                        # futur
            dict(d=date(2020, 1, 1)),                        # aucun exercice
        ]
        for c in cas:
            with self.assertRaises(DepenseError, msg=str(c)):
                svc.enregistrer_depense(self.conn, self.sec, c.get("libelle", "Achat"), c.get("depense", 1000),
                                        None, c.get("prevu"), c.get("d", ok), today=TODAY)
        self.assertEqual(svc.lister_depenses(self.conn, self.ex.id).total, 0)
        self.conn.execute("UPDATE exercices SET statut = 'cloture' WHERE id = ?", (self.ex.id,))
        with self.assertRaises(DepenseError):
            self._dep("Achat", 1000)

    def test_suppression_administrateur_seulement_avec_son_reliquat(self):
        d = self._dep("Achat de chaises", 105000, 120000)
        with self.assertRaises(PermissionDenied):
            svc.supprimer_depense(self.conn, self.sec, d.id)
        svc.supprimer_depense(self.conn, self.admin, d.id)
        self.assertEqual(svc.lister_depenses(self.conn, self.ex.id).total, 0)
        self.assertEqual(svc.list_reliquats(self.conn, self.ex.id), ([], 0))      # reliquat supprimé avec elle
        e = audit.list_entries(self.conn)[0]
        self.assertEqual(e["action"], Action.DEPENSE_SUPPR)
        self.assertIn("reliquat", e["detail"])
        with self.assertRaises(DepenseError):
            svc.supprimer_depense(self.conn, self.admin, d.id)
        autre = self._dep("Autre", 5000)
        self.conn.execute("UPDATE exercices SET statut = 'cloture' WHERE id = ?", (self.ex.id,))
        with self.assertRaises(DepenseError):
            svc.supprimer_depense(self.conn, self.admin, autre.id)

    def test_liste_filtres_et_totaux_de_la_maquette(self):
        self._maquette()
        p = svc.lister_depenses(self.conn, self.ex.id)
        self.assertEqual(p.total, 6)
        g = p.general
        self.assertEqual((g.prevu, g.depense, g.reliquat), (1300000, 1180000, 120000))
        self.assertEqual(g.prevu - g.depense, g.reliquat)
        self.assertEqual((p.lignes[0].depense.libelle, p.lignes[-1].depense.libelle),
                         ("Achat de chaises", "Frais de gestion"))               # plus récentes d'abord
        self.assertEqual(p.lignes[0].reliquat.montant, 15000)
        self.assertIsNone(p.lignes[1].reliquat)

        avec = svc.lister_depenses(self.conn, self.ex.id, avec_reliquat=True)
        self.assertEqual((avec.total, avec.general.prevu, avec.general.depense, avec.general.reliquat),
                         (3, 870000, 750000, 120000))
        sans = svc.lister_depenses(self.conn, self.ex.id, avec_reliquat=False)
        self.assertEqual((sans.total, sans.general.reliquat), (3, 0))

        periode = svc.lister_depenses(self.conn, self.ex.id, date_debut=date(2026, 4, 1), date_fin=date(2026, 6, 30))
        self.assertEqual((periode.total, periode.general.prevu, periode.general.depense, periode.general.reliquat),
                         (4, 770000, 710000, 60000))
        self.assertEqual(svc.lister_depenses(self.conn, self.ex.id, search="chaises").total, 1)
        self.assertEqual(svc.lister_depenses(self.conn, self.ex.id, search="kokou").total, 1)    # bénéficiaire

        page = svc.lister_depenses(self.conn, self.ex.id, limit=2, offset=0)
        self.assertEqual((len(page.lignes), page.total, page.page.depense, page.general.depense),
                         (2, 6, 255000, 1180000))
        with self.assertRaises(DepenseError):
            svc.lister_depenses(self.conn, 999)

        r = svc.resume(self.conn, self.ex.id)
        self.assertEqual((r.prevu, r.depense, r.reliquat), (1300000, 1180000, 120000))

    def test_reliquats_de_la_maquette(self):
        self._maquette()
        lignes, total = svc.list_reliquats(self.conn, self.ex.id)
        self.assertEqual(total, 120000)
        self.assertEqual([l.depense_libelle for l in lignes],
                         ["Achat de chaises", "Aide funérailles — Kossi Ayité", "Tenues de l’association"])
        self.assertEqual([l.reliquat.montant for l in lignes], [15000, 45000, 60000])
        with self.assertRaises(DepenseError):
            svc.list_reliquats(self.conn, 999)


if __name__ == "__main__":
    unittest.main()