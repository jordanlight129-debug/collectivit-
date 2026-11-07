import unittest
from datetime import date

from app.database.connection import get_connection
from app.database.schema import migrate
from app.models.amende import IMPAYEE, PARTIELLE, PAYEE
from app.models.sexe import Sexe
from app.repositories import utilisateurs
from app.security import audit
from app.security.audit import Action
from app.security.session import CurrentUser, Role, Session
from app.services import amende_service as svc
from app.services import exercice_service, membre_service
from app.services.amende_service import AmendeError

TODAY = date(2026, 8, 31)


class AmendeServiceTest(unittest.TestCase):
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

        self.yawo = mk("Yawo Agbodjan", Sexe.HOMME)        # carnet 001
        self.efua = mk("Efua Dosseh", Sexe.FEMME)
        self.komlan = mk("Komlan Akakpo", Sexe.HOMME)
        self.abla = mk("Abla Tsogbé", Sexe.FEMME)
        self.mina = mk("Mina Gbedemah", Sexe.FEMME, date(2026, 3, 10))
        self.decede = mk("Ancien Décédé", Sexe.HOMME)
        membre_service.declare_deceased(self.conn, self.admin, self.decede.id, date(2026, 2, 1), today=TODAY)

    def _amende(self, membre, nom, attendu, collecte=0, d=date(2026, 5, 20)):
        return svc.creer_amende(self.conn, self.sec, membre.id, nom, "", attendu, d, collecte, today=TODAY)

    def test_creation_par_une_secretaire_journalisee(self):
        a = svc.creer_amende(self.conn, self.sec, self.yawo.id, "Absence AG",
                             "Absence à l'assemblée générale", 5000, date(2026, 5, 1), today=TODAY)
        self.assertEqual((a.nom, a.libelle, a.montant_attendu, a.montant_collecte, a.exercice_id),
                         ("Absence AG", "Absence à l'assemblée générale", 5000, 0, self.ex.id))
        self.assertEqual((a.statut, a.manque_a_gagner), (IMPAYEE, 5000))
        e = audit.list_entries(self.conn)[0]
        self.assertEqual((e["action"], e["objet"], e["identifiant"]), (Action.AMENDE_AJOUT, "Carnet 0001", "yawa"))

    def test_libelle_par_defaut_date_du_jour_et_collecte_initiale(self):
        a = svc.creer_amende(self.conn, self.sec, self.efua.id, "Retard", "", 2000, None, 2000, today=TODAY)
        self.assertEqual((a.libelle, a.date_amende, a.statut), ("Retard", TODAY, PAYEE))

    def test_validations_rien_n_est_ecrit(self):
        cas = [
            dict(membre=999),
            dict(nom=""),
            dict(attendu=0), dict(attendu=-1), dict(attendu=12.5), dict(attendu=True),
            dict(collecte=-1), dict(collecte=6000),
            dict(d=date(2026, 9, 1)),                          # futur
            dict(membre=self.mina.id, d=date(2026, 2, 1)),     # avant l'adhésion
            dict(membre=self.decede.id, d=date(2026, 3, 1)),   # après le décès
            dict(d=date(2020, 1, 1)),                          # aucun exercice
        ]
        for c in cas:
            with self.assertRaises(AmendeError, msg=str(c)):
                svc.creer_amende(self.conn, self.sec, c.get("membre", self.yawo.id), c.get("nom", "Retard"),
                                 "", c.get("attendu", 5000), c.get("d", date(2026, 5, 1)),
                                 c.get("collecte", 0), today=TODAY)
        self.assertEqual(svc.lister(self.conn, self.ex.id).total, 0)

    def test_collecte_partielle_puis_complete(self):
        a = self._amende(self.yawo, "Absence AG", 5000)
        a = svc.collecter(self.conn, self.sec, a.id, 3000)
        self.assertEqual((a.statut, a.montant_collecte, a.manque_a_gagner), (PARTIELLE, 3000, 2000))
        with self.assertRaises(AmendeError):
            svc.collecter(self.conn, self.sec, a.id, 2500)         # dépasse le reste
        a = svc.collecter(self.conn, self.sec, a.id, 2000)
        self.assertEqual((a.statut, a.manque_a_gagner), (PAYEE, 0))
        with self.assertRaises(AmendeError):
            svc.collecter(self.conn, self.sec, a.id, 1)            # déjà encaissée
        e = audit.list_entries(self.conn)[0]
        self.assertEqual((e["action"], e["objet"]), (Action.AMENDE_COLLECTE, "Carnet 0001"))
        self.assertIn("reste 0", e["detail"].replace("\u00A0", " "))

    def test_montants_et_exercice_cloture_pour_la_collecte(self):
        a = self._amende(self.yawo, "Absence AG", 5000)
        for montant in (0, -5, 12.5, True):
            with self.assertRaises(AmendeError, msg=repr(montant)):
                svc.collecter(self.conn, self.sec, a.id, montant)
        with self.assertRaises(AmendeError):
            svc.collecter(self.conn, self.sec, 999, 1000)
        self.conn.execute("UPDATE exercices SET statut = 'cloture' WHERE id = ?", (self.ex.id,))
        with self.assertRaises(AmendeError):
            svc.collecter(self.conn, self.sec, a.id, 1000)
        with self.assertRaises(AmendeError):
            self._amende(self.efua, "Retard", 2000)

    def test_liste_filtres_et_totaux(self):
        self._amende(self.yawo, "Absence AG", 5000, 0, date(2026, 5, 20))
        self._amende(self.efua, "Retard", 2000, 2000, date(2026, 4, 10))
        self._amende(self.komlan, "Téléphone", 1000, 1000, date(2026, 3, 5))
        self._amende(self.yawo, "Retard", 2000, 1000, date(2026, 6, 15))
        self._amende(self.abla, "Absence AG", 5000, 5000, date(2026, 2, 12))

        r = svc.resume(self.conn, self.ex.id)
        self.assertEqual((r.attendu, r.collecte, r.manque), (15000, 9000, 6000))

        p = svc.lister(self.conn, self.ex.id)
        self.assertEqual(p.total, 5)
        self.assertEqual(p.general, r)
        self.assertEqual((p.lignes[0].amende.date_amende, p.lignes[-1].amende.date_amende),
                         (date(2026, 6, 15), date(2026, 2, 12)))        # plus récentes d'abord
        self.assertEqual((p.lignes[0].membre_nom, p.lignes[0].numero_carnet), ("Yawo Agbodjan", "0001"))

        self.assertEqual(svc.lister(self.conn, self.ex.id, statut="impayee").total, 1)
        self.assertEqual(svc.lister(self.conn, self.ex.id, statut="partielle").total, 1)
        self.assertEqual(svc.lister(self.conn, self.ex.id, statut="payee").total, 3)
        yawo = svc.lister(self.conn, self.ex.id, search="yawo")
        self.assertEqual((yawo.total, yawo.general.attendu, yawo.general.collecte, yawo.general.manque),
                         (2, 7000, 1000, 6000))
        self.assertEqual(svc.lister(self.conn, self.ex.id, search="0001").total, 2)     # par carnet
        self.assertEqual(svc.lister(self.conn, self.ex.id, membre_id=self.yawo.id).total, 2)

        page = svc.lister(self.conn, self.ex.id, limit=2, offset=0)
        self.assertEqual((len(page.lignes), page.total, page.general.attendu), (2, 5, 15000))
        self.assertLess(page.page.attendu, page.general.attendu)

        with self.assertRaises(AmendeError):
            svc.lister(self.conn, self.ex.id, statut="inconnu")
        with self.assertRaises(AmendeError):
            svc.lister(self.conn, 999)


if __name__ == "__main__":
    unittest.main()