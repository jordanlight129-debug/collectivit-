import unittest
from datetime import date

from app.database.connection import get_connection
from app.database.schema import migrate
from app.models.sexe import Sexe
from app.models.versement import MENSUELLE, PARALLELE
from app.repositories import utilisateurs
from app.security import audit
from app.security.audit import Action
from app.security.session import CurrentUser, PermissionDenied, Role, Session
from app.services import exercice_service, membre_service, versement_service
from app.services import parallele_service as svc
from app.services import tableau_parallele as tp
from app.services.cotisation_mensuelle import IMPAYE, NON_APPLICABLE, PARTIEL, PAYE
from app.services.parallele_service import ParalleleError
from app.services.tableau_parallele import TableauParalleleError
from app.services.versement_service import VersementError

TODAY = date(2026, 8, 31)


class ParalleleServiceTest(unittest.TestCase):
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

        def mk(nom, sexe, adhesion=date(2017, 9, 5)):
            return membre_service.create_membre(self.conn, self.admin, nom, sexe, adhesion, today=TODAY)

        self.komlan = mk("Komlan Akakpo", Sexe.HOMME)
        self.abla = mk("Abla Tsogbé", Sexe.FEMME)
        self.efua = mk("Efua Dosseh", Sexe.FEMME)
        self.yawo = mk("Yawo Agbodjan", Sexe.HOMME)
        self.mina = mk("Mina Gbedemah", Sexe.FEMME, date(2026, 3, 10))
        self.tard = mk("Arrivé Tard", Sexe.HOMME, date(2026, 7, 1))
        self.ancien = mk("Ancien Décédé", Sexe.HOMME)
        membre_service.declare_deceased(self.conn, self.admin, self.ancien.id, date(2025, 12, 31), today=TODAY)
        self.cot = self._cot()

    def _cot(self, nom="Projet salle des fêtes", debut=date(2026, 1, 1), fin=date(2026, 6, 30),
             h=12000, f=10000, session=None):
        return svc.creer_cotisation(self.conn, session or self.admin, nom, debut, fin, h, f)

    def _pay(self, membre, montant, cot=None, exercice_id=None):
        return versement_service.enregistrer(
            self.conn, self.sec, membre.id, exercice_id or self.ex.id, PARALLELE, montant,
            date(2026, 4, 1), today=TODAY, cotisation_id=(cot or self.cot).id)

    def _maquette(self):
        self._pay(self.komlan, 12000)
        self._pay(self.abla, 10000)
        self._pay(self.efua, 6000)

    def test_creation_journalisee(self):
        c = self.cot
        self.assertEqual((c.nom, c.exercice_id, c.montant_homme, c.montant_femme), ("Projet salle des fêtes", self.ex.id, 12000, 10000))
        e = audit.list_entries(self.conn)[0]
        self.assertEqual((e["action"], e["identifiant"]), (Action.COTISATION_PARALLELE, "ama"))
        self.assertEqual(len(svc.list_cotisations(self.conn, self.ex.id)), 1)

    def test_secretaire_peut_creer_une_cotisation(self):
        cotisation = self._cot(nom="Autre cotisation", session=self.sec)
        self.assertEqual(cotisation.nom, "Autre cotisation")

    def test_validations_rien_n_est_ecrit(self):
        d1, d2 = date(2026, 1, 1), date(2026, 6, 30)
        cas = [
            dict(nom=""),
            dict(nom="X Y", debut=d2, fin=d1),                    # fin avant début
            dict(nom="X Y", h=-1),
            dict(nom="X Y", f=12.5),
            dict(nom="X Y", h=True),
            dict(nom="X Y", debut=date(2026, 6, 1), fin=date(2026, 9, 30)),   # deux exercices
            dict(nom="X Y", debut=date(2020, 1, 1), fin=date(2020, 2, 1)),    # aucun exercice
            dict(nom="projet SALLE des fêtes"),                   # doublon, casse ignorée
        ]
        for c in cas:
            with self.assertRaises(ParalleleError, msg=str(c)):
                self._cot(nom=c["nom"], debut=c.get("debut", d1), fin=c.get("fin", d2),
                          h=c.get("h", 12000), f=c.get("f", 10000))
        self.assertEqual(len(svc.list_cotisations(self.conn, self.ex.id)), 1)      # seulement celle de setUp
        self.conn.execute("UPDATE exercices SET statut = 'cloture' WHERE id = ?", (self.ex.id,))
        with self.assertRaises(ParalleleError):
            self._cot(nom="Autre cotisation")

    def test_paiement_et_releve_ne_touchent_pas_le_mensuel(self):
        v = self._pay(self.efua, 6000)
        self.assertEqual((v.rubrique, v.cotisation_parallele_id), (PARALLELE, self.cot.id))
        s = svc.releve_parallele(self.conn, self.efua.id, self.cot.id)
        self.assertEqual((s.status, s.due, s.paid, s.debt), (PARTIEL, 10000, 6000, 4000))
        self.assertEqual(versement_service.releve_mensuel(self.conn, self.efua.id, self.ex.id).total_paid, 0)
        self.assertIn("Projet salle des fêtes", audit.list_entries(self.conn)[0]["detail"])

    def test_membre_non_concerne_ne_peut_pas_payer(self):
        for membre in (self.tard, self.ancien):
            with self.assertRaises(VersementError, msg=membre.nom):
                self._pay(membre, 5000)

    def test_cotisation_d_un_autre_exercice_ou_mauvaise_rubrique(self):
        autre_ex = exercice_service.create_exercice(self.conn, self.admin, 2026, 18000, 14000)
        autre = self._cot(nom="Fête de rentrée", debut=date(2026, 9, 1), fin=date(2026, 10, 31))
        self.assertEqual(autre.exercice_id, autre_ex.id)
        with self.assertRaises(VersementError):
            self._pay(self.komlan, 5000, cot=autre)               # exercice 2025 + cotisation 2026
        with self.assertRaises(VersementError):                   # cotisation sur une rubrique mensuelle
            versement_service.enregistrer(self.conn, self.sec, self.komlan.id, self.ex.id, MENSUELLE,
                                          5000, date(2026, 4, 1), today=TODAY, cotisation_id=self.cot.id)
        with self.assertRaises(VersementError):                   # parallèle sans cotisation
            versement_service.enregistrer(self.conn, self.sec, self.komlan.id, self.ex.id, PARALLELE,
                                          5000, date(2026, 4, 1), today=TODAY)

    def test_tableau_de_la_maquette(self):
        self._maquette()
        p = tp.tableau(self.conn, self.cot.id)
        noms = {l.membre.nom for l in p.lignes}
        self.assertEqual(noms, {"Komlan Akakpo", "Abla Tsogbé", "Efua Dosseh", "Yawo Agbodjan", "Mina Gbedemah"})
        self.assertNotIn("Arrivé Tard", noms)
        self.assertNotIn("Ancien Décédé", noms)
        g = p.general
        self.assertEqual((p.total, g.du, g.percu, g.dette, g.avance), (5, 54000, 28000, 26000, 0))
        par = {l.membre.nom: l.releve.status for l in p.lignes}
        self.assertEqual(par["Komlan Akakpo"], PAYE)
        self.assertEqual(par["Efua Dosseh"], PARTIEL)
        self.assertEqual(par["Yawo Agbodjan"], IMPAYE)
        self.assertEqual(par["Mina Gbedemah"], IMPAYE)           # adhésion en mars : montant entier

    def test_filtre_tri_pagination(self):
        self._maquette()
        dette = tp.tableau(self.conn, self.cot.id, situation="dette")
        self.assertEqual({l.membre.nom for l in dette.lignes}, {"Efua Dosseh", "Yawo Agbodjan", "Mina Gbedemah"})
        self.assertEqual(dette.general.dette, 26000)
        tri = tp.tableau(self.conn, self.cot.id, sort="dette", descending=True)
        self.assertEqual(tri.lignes[0].membre.nom, "Yawo Agbodjan")
        page = tp.tableau(self.conn, self.cot.id, limit=2, offset=0)
        self.assertEqual((len(page.lignes), page.total, page.general.du), (2, 5, 54000))
        self.assertLess(page.page.du, page.general.du)
        self.assertEqual([l.membre.nom for l in tp.tableau(self.conn, self.cot.id, search="dosseh").lignes],
                         ["Efua Dosseh"])
        with self.assertRaises(TableauParalleleError):
            tp.tableau(self.conn, self.cot.id, situation="inconnue")
        with self.assertRaises(TableauParalleleError):
            tp.tableau(self.conn, 999)

    def test_resumes_par_cotisation(self):
        self._maquette()
        gratuite = self._cot(nom="Fête de fin d'année", debut=date(2025, 12, 1), fin=date(2025, 12, 31), h=5000, f=5000)
        resumes = svc.list_cotisations(self.conn, self.ex.id)
        self.assertEqual([c.nom for c in resumes], ["Fête de fin d'année", "Projet salle des fêtes"])
        par_id = {c.id: t for c, t in tp.list_resumes(self.conn, self.ex.id)}
        self.assertEqual((par_id[self.cot.id].du, par_id[self.cot.id].percu, par_id[self.cot.id].dette), (54000, 28000, 26000))
        # Fête de fin d'année (déc. 2025) : Mina (adhésion mars 2026) et Arrivé Tard n'y sont pas ; l'ancien décédé non plus
        self.assertEqual((par_id[gratuite.id].membres, par_id[gratuite.id].du), (5, 25000))


if __name__ == "__main__":
    unittest.main()
