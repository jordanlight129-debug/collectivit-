import unittest
from datetime import date

from app.database import schema
from app.database.connection import get_connection
from app.database.schema import migrate
from app.models.deces import BEAU_PARENT, MEMBRE, PARENT
from app.models.sexe import Sexe
from app.models.versement import FUNERAIRE, MENSUELLE, PARALLELE
from app.repositories import encaissements_amendes, utilisateurs
from app.security.session import CurrentUser, Role, Session
from app.services import (
    amende_service, deces_service, depense_service, exercice_service, membre_service,
    parallele_service, versement_service,
)
from app.services import historique_service as svc
from app.services.affichage import DETTE, Situation
from app.services.amende_service import AmendeError
from app.services.historique_service import HistoriqueError

TODAY = date(2026, 8, 31)


class HistoriqueServiceTest(unittest.TestCase):
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
        exercice_service.set_funeral_tarifs(self.conn, self.admin, self.ex.id, 10000, 8000)

        def mk(nom, sexe, adhesion=date(2017, 9, 5)):
            return membre_service.create_membre(self.conn, self.admin, nom, sexe, adhesion, today=TODAY)

        self.yawo = mk("Yawo Agbodjan", Sexe.HOMME)        # carnet 0001
        self.efua = mk("Efua Dosseh", Sexe.FEMME)
        self.abla = mk("Abla Tsogbé", Sexe.FEMME)
        self.kossi = mk("Kossi Ayité", Sexe.HOMME)
        self.mina = mk("Mina Gbedemah", Sexe.FEMME, date(2026, 1, 10))

    def _pay(self, membre, montant, rubrique, d=date(2026, 2, 1), cotisation=None):
        versement_service.enregistrer(
            self.conn, self.sec, membre.id, self.ex.id, rubrique, montant, d, today=TODAY,
            cotisation_id=cotisation.id if cotisation else None)

    def _scenario(self):
        for membre, montant in ((self.yawo, 131000), (self.efua, 150000),
                                (self.abla, 180000), (self.kossi, 126000)):
            self._pay(membre, montant, MENSUELLE)
        c = lambda *a, **k: deces_service.creer_collecte(self.conn, self.sec, *a, today=TODAY, **k)
        c("Mme Lawson", PARENT, date(2025, 12, 10))
        c("", MEMBRE, date(2026, 3, 14), membre_defunt_id=self.kossi.id)
        c("M. Dosseh", BEAU_PARENT, date(2026, 5, 2), membre_endeuille_id=self.efua.id, exempter_endeuille=True)
        c("Mme Tsogbé", PARENT, date(2026, 6, 20), membre_endeuille_id=self.abla.id, exempter_endeuille=True)
        for membre, montant in ((self.yawo, 10000), (self.efua, 20000),
                                (self.abla, 24000), (self.kossi, 10000)):
            self._pay(membre, montant, FUNERAIRE)
        cot = parallele_service.creer_cotisation(
            self.conn, self.admin, "Projet salle des fêtes", date(2026, 1, 1), date(2026, 6, 30), 12000, 10000)
        for membre, montant in ((self.yawo, 12000), (self.abla, 10000), (self.efua, 6000)):
            self._pay(membre, montant, PARALLELE, date(2026, 4, 1), cot)
        a = lambda membre, nom, attendu, collecte, d: amende_service.creer_amende(
            self.conn, self.sec, membre.id, nom, "", attendu, d, collecte, today=TODAY)
        a(self.yawo, "Absence AG", 5000, 0, date(2026, 5, 20))
        a(self.efua, "Retard", 2000, 2000, date(2026, 4, 10))
        a(self.yawo, "Retard", 2000, 1000, date(2026, 6, 15))
        for libelle, bene, prevu, depense, d in (
                ("Achat de chaises", "Ets Kokou", 120000, 105000, date(2026, 6, 16)),
                ("Location salle assemblée", "Salle Le Baobab", 150000, 150000, date(2026, 6, 2)),
                ("Aide funérailles — Kossi Ayité", "Famille Ayité", 300000, 255000, date(2026, 5, 20)),
                ("Sonorisation fête", "Studio Éclair", 200000, 200000, date(2026, 4, 12)),
                ("Tenues de l’association", "Atelier Mawu", 450000, 390000, date(2026, 3, 3)),
                ("Frais de gestion", None, 80000, 80000, date(2026, 2, 10))):
            depense_service.enregistrer_depense(self.conn, self.sec, libelle, depense, bene, prevu, d, today=TODAY)

    def test_historique_complet_de_l_exercice(self):
        self._scenario()
        p = svc.lister(self.conn, exercice_id=self.ex.id)
        self.assertEqual((p.total, len(p.lignes)), (22, 22))        # 4 + 4 + 3 + 2 amendes + 3 reliquats + 6 dépenses
        self.assertEqual((p.entrees, p.sorties), (802000, 1180000))
        self.assertEqual(p.situation, Situation(DETTE, 378000))
        dates = [l.date_operation for l in p.lignes]
        self.assertEqual(dates, sorted(dates, reverse=True))          # les plus récentes d'abord
        self.assertTrue(all(l.montant > 0 for l in p.lignes))
        self.assertEqual({l.sens for l in p.lignes}, {"entree", "sortie"})

    def test_filtres_par_rubrique_et_par_sens(self):
        self._scenario()
        mensuelle = svc.lister(self.conn, exercice_id=self.ex.id, rubrique="mensuelle")
        self.assertEqual((mensuelle.total, mensuelle.entrees, mensuelle.sorties), (4, 587000, 0))
        parallele = svc.lister(self.conn, exercice_id=self.ex.id, rubrique="parallele")
        self.assertEqual((parallele.total, parallele.entrees), (3, 28000))
        self.assertTrue(all("Projet salle des fêtes" in l.libelle for l in parallele.lignes))
        amendes = svc.lister(self.conn, exercice_id=self.ex.id, rubrique="amende")
        self.assertEqual((amendes.total, amendes.entrees), (2, 3000))
        reliquats = svc.lister(self.conn, exercice_id=self.ex.id, rubrique="reliquat")
        self.assertEqual((reliquats.total, reliquats.entrees), (3, 120000))
        self.assertTrue(all(l.libelle.startswith("Reliquat — ") for l in reliquats.lignes))
        sorties = svc.lister(self.conn, exercice_id=self.ex.id, sens="sortie")
        self.assertEqual((sorties.total, sorties.sorties, sorties.entrees), (6, 1180000, 0))
        self.assertEqual(svc.lister(self.conn, exercice_id=self.ex.id, sens="entree").total, 16)

    def test_recherche_et_historique_d_un_membre(self):
        self._scenario()
        par_nom = svc.lister(self.conn, exercice_id=self.ex.id, search="yawo")
        self.assertEqual((par_nom.total, par_nom.entrees), (4, 154000))     # 131 000 + 10 000 + 12 000 + 1 000
        self.assertEqual(svc.lister(self.conn, exercice_id=self.ex.id, search="0001").total, 4)   # par carnet
        fiche = svc.historique_membre(self.conn, self.yawo.id, exercice_id=self.ex.id)
        self.assertEqual((fiche.total, fiche.entrees), (4, 154000))
        self.assertEqual({l.rubrique for l in fiche.lignes}, {"mensuelle", "funeraire", "parallele", "amende"})
        self.assertEqual(svc.lister(self.conn, exercice_id=self.ex.id, search="kokou").total, 1)   # bénéficiaire

    def test_filtre_par_periode(self):
        self._scenario()
        p = svc.lister(self.conn, exercice_id=self.ex.id, date_debut=date(2026, 6, 1), date_fin=date(2026, 6, 30))
        self.assertEqual((p.total, p.entrees, p.sorties), (4, 16000, 255000))
        self.assertEqual(p.situation, Situation(DETTE, 239000))

    def test_pagination_garde_les_totaux_du_resultat_filtre(self):
        self._scenario()
        p = svc.lister(self.conn, exercice_id=self.ex.id, limit=5, offset=0)
        self.assertEqual((len(p.lignes), p.total, p.entrees, p.sorties), (5, 22, 802000, 1180000))
        dernier = svc.lister(self.conn, exercice_id=self.ex.id, limit=5, offset=20)
        self.assertEqual(len(dernier.lignes), 2)

    def test_tous_les_exercices(self):
        self._scenario()
        exercice_service.create_exercice(self.conn, self.admin, 2024, 18000, 14000)
        depense_service.enregistrer_depense(self.conn, self.sec, "Achat ancien", 30000, None, None,
                                            date(2025, 3, 1), today=TODAY)
        self.assertEqual(svc.lister(self.conn, exercice_id=self.ex.id).total, 22)
        tout = svc.lister(self.conn)
        self.assertEqual((tout.total, tout.sorties), (23, 1210000))

    def test_qui_a_saisi_chaque_operation(self):
        self._scenario()
        p = svc.lister(self.conn, exercice_id=self.ex.id)
        self.assertEqual({l.saisi_par for l in p.lignes}, {"yawa"})
        self.assertTrue(all(l.cree_le for l in p.lignes))

    def test_parametres_invalides(self):
        cas = [dict(rubrique="inconnue"), dict(sens="autre"), dict(exercice_id=999),
               dict(date_debut=date(2026, 6, 1), date_fin=date(2026, 5, 1))]
        for c in cas:
            with self.assertRaises(HistoriqueError, msg=str(c)):
                svc.lister(self.conn, **c)

    def test_chaque_encaissement_d_amende_est_historise(self):
        amende = amende_service.creer_amende(self.conn, self.sec, self.yawo.id, "Absence AG 2", "",
                                             5000, date(2026, 5, 1), 0, today=TODAY)
        amende_service.collecter(self.conn, self.sec, amende.id, 3000, date(2026, 6, 20), today=TODAY)
        amende_service.collecter(self.conn, self.sec, amende.id, 2000, date(2026, 7, 1), today=TODAY)
        for date_invalide in (date(2026, 9, 1), date(2026, 4, 30)):       # futur, avant l'amende
            with self.assertRaises(AmendeError):
                amende_service.collecter(self.conn, self.sec, amende.id, 100, date_invalide, today=TODAY)
        a = amende_service.get_amende(self.conn, amende.id)
        self.assertEqual((a.montant_collecte, encaissements_amendes.total(self.conn, amende.id)), (5000, 5000))
        p = svc.lister(self.conn, exercice_id=self.ex.id, rubrique="amende", membre_id=self.yawo.id)
        self.assertEqual([(l.date_operation, l.montant) for l in p.lignes],
                         [(date(2026, 7, 1), 2000), (date(2026, 6, 20), 3000)])

    def test_migration_v5_reprend_les_encaissements_existants(self):
        conn = get_connection(":memory:")
        self.addCleanup(conn.close)
        for version, sql in schema.MIGRATIONS:
            if version <= 4:
                conn.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {version};\nCOMMIT;")
        conn.execute("INSERT INTO exercices (libelle, date_debut, date_fin) VALUES ('2025-2026', '2025-09-01', '2026-08-31')")
        conn.execute("INSERT INTO membres (numero_carnet, nom, sexe, date_adhesion) VALUES ('001', 'Test', 'M', '2017-09-05')")
        conn.execute("INSERT INTO amendes (exercice_id, membre_id, nom, libelle, date_amende, montant_attendu, montant_collecte) "
                     "VALUES (1, 1, 'Retard', 'Retard', '2026-04-10', 1000, 700)")
        conn.execute("INSERT INTO amendes (exercice_id, membre_id, nom, libelle, date_amende, montant_attendu, montant_collecte) "
                     "VALUES (1, 1, 'Absence', 'Absence', '2026-05-10', 2000, 0)")
        self.assertEqual(schema.migrate(conn), schema.LATEST_VERSION)
        rows = conn.execute("SELECT amende_id, montant, date_encaissement FROM encaissements_amendes").fetchall()
        self.assertEqual([tuple(r) for r in rows], [(1, 700, "2026-04-10")])


if __name__ == "__main__":
    unittest.main()