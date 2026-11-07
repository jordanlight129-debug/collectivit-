import unittest
import sqlite3
from datetime import date

from app.database.connection import get_connection
from app.database.schema import migrate
from app.models.deces import BEAU_PARENT, MEMBRE, PARENT
from app.models.sexe import Sexe
from app.models.versement import FUNERAIRE, MENSUELLE, PARALLELE
from app.repositories import utilisateurs
from app.security.session import CurrentUser, Role, Session
from app.services import (
    amende_service,
    bilan_service,
    deces_service,
    depense_service,
    exercice_service,
    membre_service,
    parallele_service,
    versement_service,
)

TODAY = date(2026, 8, 31)


class Etape0CartographieTest(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.addCleanup(self.conn.close)
        migrate(self.conn)
        utilisateurs.create(self.conn, "ama", "Ama K.", "x", Role.ADMINISTRATEUR)
        utilisateurs.create(self.conn, "yawa", "Yawa D.", "x", Role.SECRETAIRE)
        self.admin = Session()
        self.sec = Session()
        self.admin.login(CurrentUser(1, "ama", "Ama K.", Role.ADMINISTRATEUR))
        self.sec.login(CurrentUser(2, "yawa", "Yawa D.", Role.SECRETAIRE))
        self.ex = exercice_service.create_exercice(self.conn, self.admin, 2025, 18000, 14000)
        exercice_service.set_funeral_tarifs(self.conn, self.admin, self.ex.id, 10000, 8000)

        def mk(nom, sexe, adhesion=date(2017, 9, 5)):
            return membre_service.create_membre(self.conn, self.admin, nom, sexe, adhesion, today=TODAY)

        self.yawo = mk("Yawo Agbodjan", Sexe.HOMME)
        self.efua = mk("Efua Dosseh", Sexe.FEMME)
        self.abla = mk("Abla Tsogbé", Sexe.FEMME)
        self.kossi = mk("Kossi Ayité", Sexe.HOMME)
        self.mina = mk("Mina Gbedemah", Sexe.FEMME, date(2026, 1, 10))

    def _pay(self, membre, montant, rubrique, d=date(2026, 2, 1), cotisation=None):
        versement_service.enregistrer(
            self.conn,
            self.sec,
            membre.id,
            self.ex.id,
            rubrique,
            montant,
            d,
            today=TODAY,
            cotisation_id=cotisation.id if cotisation else None,
        )

    def test_schema_et_convention_du_carnet_sont_coherents(self):
        # Colonne texte + contrainte UNIQUE : le schéma impose bien un stockage texte unique.
        info = self.conn.execute("PRAGMA table_info(membres)").fetchall()
        cols = {row[1]: row for row in info}
        self.assertEqual(cols["numero_carnet"][2], "TEXT")
        self.assertEqual(cols["numero_carnet"][3], 1)  # NOT NULL

        # Le format canonique connu du projet est exactement 4 chiffres, zéro conservé.
        self.assertEqual(self.yawo.numero_carnet, "0001")
        self.assertEqual(len(self.yawo.numero_carnet), 4)
        self.assertTrue(self.yawo.numero_carnet.isdigit())

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO membres (numero_carnet, nom, sexe, date_adhesion) VALUES (?, ?, ?, ?)",
                ("0001", "Doublon", "M", TODAY.isoformat()),
            )

    def test_depense_avec_reliquat_est_caracterisee(self):
        dep = depense_service.enregistrer_depense(
            self.conn,
            self.sec,
            "Achat de chaises",
            105000,
            "Ets Kokou",
            120000,
            date(2026, 6, 16),
            today=TODAY,
        )
        self.assertEqual((dep.montant_prevu, dep.montant_depense, dep.reliquat_montant), (120000, 105000, 15000))
        lignes, total = depense_service.list_reliquats(self.conn, self.ex.id)
        self.assertEqual((len(lignes), total), (1, 15000))
        self.assertEqual(lignes[0].reliquat.montant, 15000)

    def test_bilan_service_avec_valeurs_connues(self):
        for membre, montant in ((self.yawo, 131000), (self.efua, 150000), (self.abla, 180000), (self.kossi, 126000)):
            self._pay(membre, montant, MENSUELLE)

        c = lambda *a, **k: deces_service.creer_collecte(self.conn, self.sec, *a, today=TODAY, **k)
        c("Mme Lawson", PARENT, date(2025, 12, 10))
        c("", MEMBRE, date(2026, 3, 14), membre_defunt_id=self.kossi.id)
        c("M. Dosseh", BEAU_PARENT, date(2026, 5, 2), membre_endeuille_id=self.efua.id, exempter_endeuille=True)
        c("Mme Tsogbé", PARENT, date(2026, 6, 20), membre_endeuille_id=self.abla.id, exempter_endeuille=True)

        for membre, montant in ((self.yawo, 10000), (self.efua, 20000), (self.abla, 24000), (self.kossi, 10000)):
            self._pay(membre, montant, FUNERAIRE)

        cot = parallele_service.creer_cotisation(
            self.conn,
            self.admin,
            "Projet salle des fêtes",
            date(2026, 1, 1),
            date(2026, 6, 30),
            12000,
            10000,
        )
        for membre, montant in ((self.yawo, 12000), (self.abla, 10000), (self.efua, 6000)):
            self._pay(membre, montant, PARALLELE, date(2026, 4, 1), cot)

        amende_service.creer_amende(self.conn, self.sec, self.yawo.id, "Absence AG", "", 5000, date(2026, 5, 20), 0, today=TODAY)
        amende_service.creer_amende(self.conn, self.sec, self.efua.id, "Retard", "", 2000, date(2026, 4, 10), 2000, today=TODAY)
        amende_service.creer_amende(self.conn, self.sec, self.yawo.id, "Retard", "", 2000, date(2026, 6, 15), 1000, today=TODAY)

        depense_service.enregistrer_depense(self.conn, self.sec, "Achat de chaises", 105000, "Ets Kokou", 120000, date(2026, 6, 16), today=TODAY)
        depense_service.enregistrer_depense(self.conn, self.sec, "Location salle assemblée", 150000, "Salle Le Baobab", 150000, date(2026, 6, 2), today=TODAY)
        depense_service.enregistrer_depense(self.conn, self.sec, "Aide funérailles — Kossi Ayité", 255000, "Famille Ayité", 300000, date(2026, 5, 20), today=TODAY)
        depense_service.enregistrer_depense(self.conn, self.sec, "Sonorisation fête", 200000, "Studio Éclair", 200000, date(2026, 4, 12), today=TODAY)
        depense_service.enregistrer_depense(self.conn, self.sec, "Tenues de l’association", 390000, "Atelier Mawu", 450000, date(2026, 3, 3), today=TODAY)
        depense_service.enregistrer_depense(self.conn, self.sec, "Frais de gestion", 80000, None, 80000, date(2026, 2, 10), today=TODAY)

        bilan = bilan_service.calculer(self.conn, self.ex.id)
        self.assertEqual(bilan.total_entrees, 802000)
        self.assertEqual((bilan.total_du, bilan.total_manque), (975000, 293000))
        self.assertEqual((bilan.depenses, bilan.depenses_prevues), (1180000, 1300000))
        self.assertEqual(bilan.solde, -378000)


if __name__ == "__main__":
    unittest.main()
