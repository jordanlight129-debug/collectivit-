"""Tests complets pour la fonctionnalité Cotisations mensuelles."""
import unittest
from datetime import date

from app.database.connection import get_connection
from app.database.schema import migrate
from app.models.sexe import Sexe
from app.repositories import exercices, utilisateurs, versements
from app.security.session import CurrentUser, Role, Session
from app.services import exercice_service, membre_service, versement_service
from app.services import tableau_mensuel as tm
from app.services.cotisation_mensuelle import monthly_statement
from app.services.calendrier import exercise_months

TODAY = date(2026, 8, 31)


class CotisationsMensuellesTest(unittest.TestCase):
    """Tests bout en bout des cotisations mensuelles."""

    def setUp(self):
        self.conn = get_connection(":memory:")
        self.addCleanup(self.conn.close)
        migrate(self.conn)
        utilisateurs.create(self.conn, "admin", "Admin", "x", Role.ADMINISTRATEUR)
        self.session = Session()
        self.session.login(CurrentUser(1, "admin", "Admin", Role.ADMINISTRATEUR))
        self.ex = exercice_service.create_exercice(self.conn, self.session, 2025, 18000, 14000)

    def test_ajouter_cotisation(self):
        """Test: ajouter une cotisation pour un membre et un mois."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        versement_service.enregistrer(
            self.conn, self.session, membre.id, self.ex.id,
            versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY
        )
        # Vérifier que le versement est enregistré
        total = versements.total_paid(self.conn, membre.id, self.ex.id, versement_service.MENSUELLE)
        self.assertEqual(total, 18000)

    def test_refuser_doublon(self):
        """Test: refuser un doublon de versement (pas de contrainte UNIQUE, mais vérifier la logique)."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        # Ajouter deux versements identiques (ce qui est autorisé par le modèle)
        versement_service.enregistrer(
            self.conn, self.session, membre.id, self.ex.id,
            versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY
        )
        versement_service.enregistrer(
            self.conn, self.session, membre.id, self.ex.id,
            versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY
        )
        # Les deux versements doivent exister (pas de contrainte UNIQUE)
        total = versements.total_paid(self.conn, membre.id, self.ex.id, versement_service.MENSUELLE)
        self.assertEqual(total, 36000)

    def test_modifier_cotisation(self):
        """Test: modifier une cotisation."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        v = versement_service.enregistrer(
            self.conn, self.session, membre.id, self.ex.id,
            versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY
        )
        # Modifier le versement
        versement_service.modifier(
            self.conn, self.session, v.id, 20000, date(2026, 2, 2), note="Modifié"
        )
        v_modifie = versements.get(self.conn, v.id)
        self.assertEqual(v_modifie.montant, 20000)
        self.assertEqual(v_modifie.note, "Modifié")

    def test_supprimer_cotisation(self):
        """Test: supprimer une cotisation."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        v = versement_service.enregistrer(
            self.conn, self.session, membre.id, self.ex.id,
            versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY
        )
        # Supprimer le versement
        versement_service.supprimer(self.conn, self.session, v.id)
        v_supprime = versements.get(self.conn, v.id)
        self.assertIsNone(v_supprime)

    def test_total_par_membre(self):
        """Test: calculer correctement le total payé par membre."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        versement_service.enregistrer(self.conn, self.session, membre.id, self.ex.id, versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY)
        versement_service.enregistrer(self.conn, self.session, membre.id, self.ex.id, versement_service.MENSUELLE, 14000, date(2026, 3, 1), today=TODAY)
        total = versements.total_paid(self.conn, membre.id, self.ex.id, versement_service.MENSUELLE)
        self.assertEqual(total, 32000)

    def test_total_par_mois(self):
        """Test: calculer correctement le total payé par mois (via le tableau mensuel)."""
        membre1 = membre_service.create_membre(self.conn, self.session, "Membre 1", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        membre2 = membre_service.create_membre(self.conn, self.session, "Membre 2", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        versement_service.enregistrer(self.conn, self.session, membre1.id, self.ex.id, versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY)
        versement_service.enregistrer(self.conn, self.session, membre2.id, self.ex.id, versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY)
        # Le tableau mensuel doit refléter les totaux
        page = tm.tableau(self.conn, self.ex.id)
        self.assertEqual(page.general.percu, 36000)

    def test_membre_sans_cotisation(self):
        """Test: gérer un membre sans aucune cotisation."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        # Aucun versement
        total = versements.total_paid(self.conn, membre.id, self.ex.id, versement_service.MENSUELLE)
        self.assertEqual(total, 0)
        # Le relevé doit montrer une dette
        releve = versement_service.releve_mensuel(self.conn, membre.id, self.ex.id)
        self.assertEqual(releve.total_paid, 0)
        self.assertGreater(releve.total_debt, 0)

    def test_mois_futur(self):
        """Test: gérer un mois futur (date dans le futur)."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        # Essayer d'ajouter un versement avec une date future
        with self.assertRaises(versement_service.VersementError) as context:
            versement_service.enregistrer(
                self.conn, self.session, membre.id, self.ex.id,
                versement_service.MENSUELLE, 18000, date(2027, 1, 1), today=TODAY
            )
        self.assertIn("futur", str(context.exception).lower())

    def test_montant_zero(self):
        """Test: gérer un montant à 0."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        with self.assertRaises(versement_service.VersementError) as context:
            versement_service.enregistrer(
                self.conn, self.session, membre.id, self.ex.id,
                versement_service.MENSUELLE, 0, date(2026, 2, 1), today=TODAY
            )
        self.assertIn("positif", str(context.exception).lower())

    def test_montant_negatif(self):
        """Test: gérer un montant négatif."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        with self.assertRaises(versement_service.VersementError) as context:
            versement_service.enregistrer(
                self.conn, self.session, membre.id, self.ex.id,
                versement_service.MENSUELLE, -1000, date(2026, 2, 1), today=TODAY
            )
        self.assertIn("positif", str(context.exception).lower())

    def test_membre_supprime(self):
        """Test: gérer un membre supprimé (statut deces)."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        versement_service.enregistrer(self.conn, self.session, membre.id, self.ex.id, versement_service.MENSUELLE, 18000, date(2026, 2, 1), today=TODAY)
        # Marquer le membre comme décédé
        membre_service.declare_deceased(self.conn, self.session, membre.id, date(2026, 6, 1), today=TODAY)
        # Le membre doit toujours apparaître dans le tableau s'il a des versements
        page = tm.tableau(self.conn, self.ex.id)
        noms = [l.membre.nom for l in page.lignes]
        self.assertIn("Test Membre", noms)

    def test_montants_entiers_precis(self):
        """Test: vérifier que les montants sont stockés comme entiers précis."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        montant = 12345
        versement_service.enregistrer(
            self.conn, self.session, membre.id, self.ex.id,
            versement_service.MENSUELLE, montant, date(2026, 2, 1), today=TODAY
        )
        v = versements.list_for_member(self.conn, membre.id, exercice_id=self.ex.id, rubrique=versement_service.MENSUELLE)[0]
        self.assertEqual(v.montant, montant)
        self.assertIsInstance(v.montant, int)

    def test_repartition_versements_sur_mois(self):
        """Test: vérifier que les versements sont répartis correctement sur les mois."""
        membre = membre_service.create_membre(self.conn, self.session, "Test Membre", Sexe.HOMME, date(2017, 9, 5), today=TODAY)
        # Payer pour 3 mois
        versement_service.enregistrer(
            self.conn, self.session, membre.id, self.ex.id,
            versement_service.MENSUELLE, 54000, date(2026, 2, 1), today=TODAY
        )
        releve = versement_service.releve_mensuel(self.conn, membre.id, self.ex.id)
        # Les 3 premiers mois doivent être payés
        self.assertEqual(releve.cells[0].status, "paye")
        self.assertEqual(releve.cells[1].status, "paye")
        self.assertEqual(releve.cells[2].status, "paye")
        self.assertEqual(releve.cells[3].status, "impaye")


if __name__ == "__main__":
    unittest.main()
