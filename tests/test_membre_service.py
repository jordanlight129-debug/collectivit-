import sqlite3
import unittest
from datetime import date

from app.database.schema import migrate
from app.models.sexe import Sexe
from app.security import audit
from app.security.audit import Action
from app.security.session import CurrentUser, PermissionDenied, Role, Session
from app.services import membre_service as svc
from app.services.membre_service import MembreError

TODAY = date(2026, 10, 21)


class MembreServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        migrate(self.conn)
        self.admin = Session()
        self.admin.login(CurrentUser(1, "ama", "Ama K.", Role.ADMINISTRATEUR))
        self.sec = Session()
        self.sec.login(CurrentUser(2, "yawa", "Yawa D.", Role.SECRETAIRE))

    def _add(self, nom, sexe=Sexe.HOMME, adhesion=None, session=None):
        return svc.create_membre(self.conn, session or self.admin, nom, sexe, adhesion, today=TODAY)

    def test_creation_carnet_automatique_et_adhesion_du_jour(self):
        m = self._add("  Yawo   Agbodjan ")
        self.assertEqual((m.numero_carnet, m.nom, m.statut), ("0001", "Yawo Agbodjan", "actif"))
        self.assertEqual(m.date_adhesion, TODAY)
        e = audit.list_entries(self.conn)[0]
        self.assertEqual((e["action"], e["objet"]), (Action.MEMBRE_AJOUT, "Carnet 0001"))

    def test_carnets_sequentiels_et_uniques(self):
        numeros = [self._add(f"Membre Numéro{i}").numero_carnet for i in range(3)]
        self.assertEqual(numeros, ["0001", "0002", "0003"])

    def test_adhesion_passee_admise_future_refusee(self):
        m = self._add("Komlan Akakpo", adhesion=date(2017, 9, 5))
        self.assertEqual(m.date_adhesion, date(2017, 9, 5))
        with self.assertRaises(MembreError):
            self._add("Abla Tsogbé", adhesion=date(2026, 11, 1))

    def test_champs_invalides_ne_consomment_pas_de_numero(self):
        for nom, sexe in ((" ", Sexe.HOMME), ("A B", "X")):
            with self.assertRaises(MembreError):
                self._add(nom, sexe)
        self.assertEqual(svc.list_membres(self.conn)[1], 0)
        self.assertEqual(self._add("Premier Membre").numero_carnet, "0001")

    def test_secretaire_cree_mais_ne_supprime_pas(self):
        m = self._add("Sika Amouzou", Sexe.FEMME, session=self.sec)
        with self.assertRaises(PermissionDenied):
            svc.delete_membre(self.conn, self.sec, m.id)

    def test_modification_journalise_les_changements_sans_toucher_au_carnet(self):
        m = self._add("Abla Tsogbe", Sexe.FEMME)
        with self.assertRaises(PermissionDenied):
            svc.update_membre(self.conn, self.sec, m.id, "Abla Tsogbé", Sexe.FEMME, TODAY, today=TODAY)
        svc.update_membre(self.conn, self.admin, m.id, "Abla Tsogbé", Sexe.FEMME, TODAY, today=TODAY)
        e = audit.list_entries(self.conn)[0]
        self.assertEqual(e["action"], Action.MEMBRE_MODIF)
        self.assertIn("Abla Tsogbe → Abla Tsogbé", e["detail"])
        self.assertEqual(svc.get_membre(self.conn, m.id).numero_carnet, "0001")

    def test_liste_recherche_filtre_tri_pagination(self):
        for nom, sexe in (("Komlan Akakpo", Sexe.HOMME), ("Abla Tsogbé", Sexe.FEMME),
                          ("Koffi Dzakpasu", Sexe.HOMME), ("Sika Amouzou", Sexe.FEMME)):
            self._add(nom, sexe)
        rows, _ = svc.list_membres(self.conn)
        self.assertEqual([m.numero_carnet for m in rows], ["0001", "0002", "0003", "0004"])
        self.assertEqual(svc.list_membres(self.conn, search="ko")[1], 2)
        self.assertEqual(svc.list_membres(self.conn, search="0004")[1], 1)
        self.assertEqual(svc.list_membres(self.conn, sexe=Sexe.FEMME)[1], 2)
        rows, _ = svc.list_membres(self.conn, sort="nom", descending=True)
        self.assertEqual(rows[0].nom, "Sika Amouzou")
        rows, total = svc.list_membres(self.conn, limit=2, offset=2)
        self.assertEqual((len(rows), total), (2, 4))

    def test_deces_rend_le_membre_inactif(self):
        m = self._add("Kossi Ayité", adhesion=date(2017, 9, 5))
        d = svc.declare_deceased(self.conn, self.sec, m.id, date(2026, 3, 14), today=TODAY)
        self.assertEqual((d.statut, d.date_deces), ("decede", date(2026, 3, 14)))
        self.assertFalse(d.is_active)
        self.assertEqual(audit.list_entries(self.conn)[0]["action"], Action.MEMBRE_DECES)
        self.assertEqual(svc.list_membres(self.conn, statut="decede")[1], 1)
        with self.assertRaises(MembreError):
            svc.declare_deceased(self.conn, self.sec, m.id, date(2026, 4, 1), today=TODAY)

    def test_deces_date_par_defaut_et_dates_invalides(self):
        m = self._add("Efua Dosseh", adhesion=date(2020, 1, 10))
        with self.assertRaises(MembreError):
            svc.declare_deceased(self.conn, self.admin, m.id, date(2019, 12, 1), today=TODAY)
        with self.assertRaises(MembreError):
            svc.declare_deceased(self.conn, self.admin, m.id, date(2026, 12, 1), today=TODAY)
        self.assertEqual(svc.declare_deceased(self.conn, self.admin, m.id, today=TODAY).date_deces, TODAY)

    def test_suppression_refusee_si_historique(self):
        m = self._add("Yawo Agbodjan")
        self.conn.execute("INSERT INTO exercices (libelle, date_debut, date_fin) VALUES ('2025-2026', '2025-09-01', '2026-08-31')")
        self.conn.execute(
            "INSERT INTO versements (membre_id, exercice_id, rubrique, date_versement, montant) "
            "VALUES (?, 1, 'mensuelle', '2025-10-01', 5000)", (m.id,))
        with self.assertRaises(MembreError):
            svc.delete_membre(self.conn, self.admin, m.id)
        self.assertIsNotNone(svc.get_membre(self.conn, m.id))

    def test_suppression_membre_sans_historique(self):
        m = self._add("Dzifa Kuwonu", Sexe.FEMME)
        svc.delete_membre(self.conn, self.admin, m.id)
        self.assertIsNone(svc.get_membre(self.conn, m.id))
        self.assertEqual(audit.list_entries(self.conn)[0]["action"], Action.MEMBRE_SUPPR)


if __name__ == "__main__":
    unittest.main()