import unittest
from datetime import date

from app.database.connection import get_connection
from app.database.schema import migrate
from app.models.sexe import Sexe
from app.repositories import utilisateurs, versements
from app.security import audit
from app.security.audit import Action
from app.security.session import CurrentUser, PermissionDenied, Role, Session
from app.services import cotisation_mensuelle as cm
from app.services import exercice_service, membre_service
from app.services import versement_service as svc
from app.services.versement_service import VersementError

TODAY = date(2026, 8, 31)


class VersementServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.addCleanup(self.conn.close)
        migrate(self.conn)
        utilisateurs.create(self.conn, "ama", "Ama K.", "x", Role.ADMINISTRATEUR)    # id 1
        utilisateurs.create(self.conn, "yawa", "Yawa D.", "x", Role.SECRETAIRE)      # id 2
        self.admin, self.sec = Session(), Session()
        self.admin.login(CurrentUser(1, "ama", "Ama K.", Role.ADMINISTRATEUR))
        self.sec.login(CurrentUser(2, "yawa", "Yawa D.", Role.SECRETAIRE))
        self.ex = exercice_service.create_exercice(self.conn, self.admin, 2025, 18000, 14000)
        mk = lambda nom, sexe: membre_service.create_membre(
            self.conn, self.admin, nom, sexe, date(2017, 9, 5), today=TODAY)
        self.yawo = mk("Yawo Agbodjan", Sexe.HOMME)
        self.abla = mk("Abla Tsogbé", Sexe.FEMME)

    def _pay(self, membre, montant, d=date(2026, 4, 15), rubrique=svc.MENSUELLE, session=None):
        return svc.enregistrer(self.conn, session or self.sec, membre.id, self.ex.id,
                               rubrique, montant, d, today=TODAY)

    def test_enregistrement_par_une_secretaire(self):
        v = svc.enregistrer(self.conn, self.sec, self.yawo.id, self.ex.id, svc.MENSUELLE, 5000, today=TODAY)
        self.assertEqual((v.montant, v.date_versement, v.rubrique, v.cree_par), (5000, TODAY, "mensuelle", 2))
        e = audit.list_entries(self.conn)[0]
        self.assertEqual((e["action"], e["objet"], e["identifiant"]), (Action.VERSEMENT_AJOUT, "Carnet 0001", "yawa"))

    def test_releve_de_yawo_dette_de_85000(self):
        self._pay(self.yawo, 100000)
        self._pay(self.yawo, 31000, date(2026, 5, 2))
        s = svc.releve_mensuel(self.conn, self.yawo.id, self.ex.id)
        self.assertEqual([c.status for c in s.cells], [cm.PAYE] * 7 + [cm.PARTIEL] + [cm.IMPAYE] * 4)
        self.assertEqual((s.total_due, s.total_paid, s.debt, s.advance), (216000, 131000, 85000, 0))

    def test_releve_d_abla_avance_de_12000(self):
        self._pay(self.abla, 180000)
        s = svc.releve_mensuel(self.conn, self.abla.id, self.ex.id)
        self.assertEqual((s.total_due, s.debt, s.advance), (168000, 0, 12000))

    def test_validations_et_rien_n_est_ecrit(self):
        for montant in (0, -5, 12.5, True, "5000"):
            with self.assertRaises(VersementError, msg=repr(montant)):
                self._pay(self.yawo, montant)
        with self.assertRaises(VersementError):
            self._pay(self.yawo, 5000, date(2026, 9, 1))          # futur
        with self.assertRaises(VersementError):
            self._pay(self.yawo, 5000, date(2017, 9, 4))          # avant l'adhésion
        with self.assertRaises(VersementError):
            svc.enregistrer(self.conn, self.sec, 999, self.ex.id, svc.MENSUELLE, 5000, today=TODAY)
        with self.assertRaises(VersementError):
            svc.enregistrer(self.conn, self.sec, self.yawo.id, 999, svc.MENSUELLE, 5000, today=TODAY)
        for rubrique in ("parallele", "autre"):
            with self.assertRaises(VersementError):
                self._pay(self.yawo, 5000, rubrique=rubrique)
        self.assertEqual(versements.list_for_member(self.conn, self.yawo.id), [])

    def test_exercice_cloture_refuse_tout_changement(self):
        v = self._pay(self.yawo, 5000)
        self.conn.execute("UPDATE exercices SET statut = 'cloture' WHERE id = ?", (self.ex.id,))
        with self.assertRaises(VersementError):
            self._pay(self.yawo, 5000)
        with self.assertRaises(VersementError):
            svc.modifier(self.conn, self.admin, v.id, 6000, v.date_versement, today=TODAY)
        with self.assertRaises(VersementError):
            svc.supprimer(self.conn, self.admin, v.id)

    def test_seul_l_administrateur_modifie_et_supprime(self):
        v = self._pay(self.yawo, 5000)
        with self.assertRaises(PermissionDenied):
            svc.modifier(self.conn, self.sec, v.id, 6000, v.date_versement, today=TODAY)
        with self.assertRaises(PermissionDenied):
            svc.supprimer(self.conn, self.sec, v.id)

        svc.modifier(self.conn, self.admin, v.id, 6000, v.date_versement, "correction", today=TODAY)
        e = audit.list_entries(self.conn)[0]
        self.assertEqual(e["action"], Action.VERSEMENT_MODIF)
        self.assertIn("→", e["detail"])
        self.assertEqual(svc.releve_mensuel(self.conn, self.yawo.id, self.ex.id).total_paid, 6000)

        svc.supprimer(self.conn, self.admin, v.id)
        self.assertEqual(audit.list_entries(self.conn)[0]["action"], Action.VERSEMENT_SUPPR)
        self.assertEqual(svc.releve_mensuel(self.conn, self.yawo.id, self.ex.id).total_paid, 0)

    def test_le_funeraire_ne_compte_pas_dans_le_mensuel(self):
        self._pay(self.yawo, 20000, rubrique=svc.FUNERAIRE)
        self.assertEqual(svc.releve_mensuel(self.conn, self.yawo.id, self.ex.id).total_paid, 0)
        self.assertEqual(len(svc.list_versements(self.conn, self.yawo.id, rubrique=svc.FUNERAIRE)), 1)

    def test_liste_du_plus_recent_au_plus_ancien(self):
        self._pay(self.yawo, 1000, date(2026, 1, 10))
        self._pay(self.yawo, 2000, date(2026, 3, 5))
        self._pay(self.yawo, 3000, date(2026, 2, 1))
        montants = [v.montant for v in svc.list_versements(self.conn, self.yawo.id)]
        self.assertEqual(montants, [2000, 3000, 1000])


if __name__ == "__main__":
    unittest.main()