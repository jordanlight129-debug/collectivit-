import unittest
from datetime import date

from app.database.connection import get_connection
from app.database.schema import migrate
from app.models.deces import BEAU_PARENT, MEMBRE, PARENT, Deces
from app.models.membre import Membre
from app.models.sexe import Sexe
from app.models.versement import FUNERAIRE, MENSUELLE, PARALLELE
from app.repositories import reports, utilisateurs
from app.security.session import CurrentUser, Role, Session
from app.services import (
    amende_service, bilan_service, calendrier, cloture_service, cotisation_funeraire,
    cotisation_mensuelle as cm, deces_service, depense_service, exercice_service,
    membre_service, parallele_service, reglement_service as rs, tableau_funeraire,
    tableau_mensuel, versement_service,
)
from app.services.affichage import DETTE, EXCEDENT, Situation

TODAY = date(2026, 8, 31)        # saisie de l'exercice 2025-2026
CLOTURE = date(2026, 9, 1)       # le lendemain de sa fin
TODAY26 = date(2026, 10, 20)     # saisie dans l'exercice 2026-2027
M2026 = calendrier.exercise_months(2026)
ANCIEN = date(2017, 9, 5)


def sessions(conn):
    utilisateurs.create(conn, "ama", "Ama K.", "x", Role.ADMINISTRATEUR)
    utilisateurs.create(conn, "yawa", "Yawa D.", "x", Role.SECRETAIRE)
    admin, sec = Session(), Session()
    admin.login(CurrentUser(1, "ama", "Ama K.", Role.ADMINISTRATEUR))
    sec.login(CurrentUser(2, "yawa", "Yawa D.", Role.SECRETAIRE))
    return admin, sec


class ImputationPureTest(unittest.TestCase):
    def test_mensuelle_la_plus_ancienne_dette_d_abord_exemple_de_yawo(self):
        s = cm.monthly_statement(ANCIEN, None, M2026, 18000, 100000, carried_debt=85000)
        self.assertEqual((s.carried_debt_paid, s.carried_debt_left, s.credit), (85000, 0, 15000))
        self.assertEqual([c.status for c in s.cells], [cm.PARTIEL] + [cm.IMPAYE] * 11)
        self.assertEqual((s.cells[0].paid, s.debt, s.total_debt, s.advance), (15000, 201000, 201000, 0))

    def test_mensuelle_versement_inferieur_a_la_dette_ne_touche_pas_aux_mois(self):
        s = cm.monthly_statement(ANCIEN, None, M2026, 14000, 10000, carried_debt=18000)
        self.assertEqual((s.carried_debt_paid, s.carried_debt_left, s.credit), (10000, 8000, 0))
        self.assertEqual([c.status for c in s.cells], [cm.IMPAYE] * 12)
        self.assertEqual((s.debt, s.total_debt), (168000, 176000))

    def test_mensuelle_dette_soldee_puis_le_reste_sur_les_mois(self):
        s = cm.monthly_statement(date(2026, 1, 10), None, M2026, 14000, 126000, carried_debt=112000)
        self.assertEqual((s.carried_debt_left, s.credit), (0, 14000))
        self.assertEqual((s.cells[0].status, s.debt, s.total_debt), (cm.PAYE, 154000, 154000))

    def test_mensuelle_avance_reportee_compte_comme_deja_versee(self):
        s = cm.monthly_statement(ANCIEN, None, M2026, 14000, 0, carried_advance=12000)
        self.assertEqual((s.cells[0].status, s.cells[0].paid), (cm.PARTIEL, 12000))
        self.assertEqual((s.total_paid, s.credit, s.debt, s.advance), (0, 12000, 156000, 0))
        with self.assertRaises(ValueError):
            cm.build_statement(14000, M2026, M2026, 0, carried_debt=-1)

    def test_funeraire_la_cotisation_en_cours_d_abord(self):
        membre = Membre(1, "0001", "Test", Sexe.HOMME, ANCIEN, "actif", None)
        deaths = [Deces(1, 1, "D1", PARENT, None, date(2026, 10, 3), 10000, 8000, None, False),
                  Deces(2, 1, "D2", PARENT, None, date(2026, 11, 10), 10000, 8000, None, False)]
        s = cotisation_funeraire.build_statement(membre, deaths, 35000, carried_debt=30000)
        self.assertEqual([c.status for c in s.cells], [cm.PAYE, cm.PAYE])        # les arriérés ne bougent pas
        self.assertEqual((s.total_due, s.credit, s.advance, s.carried_debt_left, s.total_debt),
                         (20000, 35000, 15000, 30000, 30000))

    def test_funeraire_les_arrieres_se_reglent_par_un_paiement_explicite(self):
        membre = Membre(1, "0001", "Test", Sexe.HOMME, ANCIEN, "actif", None)
        deaths = [Deces(1, 1, "D1", PARENT, None, date(2026, 10, 3), 10000, 8000, None, False),
                  Deces(2, 1, "D2", PARENT, None, date(2026, 11, 10), 10000, 8000, None, False)]
        s = cotisation_funeraire.build_statement(membre, deaths, 5000, carried_debt=30000, arrears_paid=20000)
        self.assertEqual([c.status for c in s.cells], [cm.PARTIEL, cm.IMPAYE])
        self.assertEqual((s.carried_debt_paid, s.carried_debt_left, s.debt, s.total_debt, s.cash_total),
                         (20000, 10000, 15000, 25000, 25000))


class ReportIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.addCleanup(self.conn.close)
        migrate(self.conn)
        self.admin, self.sec = sessions(self.conn)
        self.ex = exercice_service.create_exercice(self.conn, self.admin, 2025, 18000, 14000)
        exercice_service.set_funeral_tarifs(self.conn, self.admin, self.ex.id, 10000, 8000)

        def mk(nom, sexe, adhesion=ANCIEN):
            return membre_service.create_membre(self.conn, self.admin, nom, sexe, adhesion, today=TODAY)

        self.yawo = mk("Yawo Agbodjan", Sexe.HOMME)
        self.efua = mk("Efua Dosseh", Sexe.FEMME)
        self.abla = mk("Abla Tsogbé", Sexe.FEMME)
        self.kossi = mk("Kossi Ayité", Sexe.HOMME)
        self.mina = mk("Mina Gbedemah", Sexe.FEMME, date(2026, 1, 10))
        self._scenario()
        res = cloture_service.cloturer(self.conn, self.admin, self.ex.id, "CLÔTURER", today=CLOTURE)
        self.ex26 = res.suivant

    def _pay25(self, membre, montant, rubrique, d=date(2026, 2, 1), cotisation=None):
        versement_service.enregistrer(
            self.conn, self.sec, membre.id, self.ex.id, rubrique, montant, d, today=TODAY,
            cotisation_id=cotisation.id if cotisation else None)

    def _pay26(self, membre, montant, rubrique=MENSUELLE):
        versement_service.enregistrer(self.conn, self.sec, membre.id, self.ex26.id, rubrique,
                                      montant, date(2026, 10, 5), today=TODAY26)

    def _scenario(self):
        for membre, montant in ((self.yawo, 131000), (self.efua, 150000),
                                (self.abla, 180000), (self.kossi, 126000)):
            self._pay25(membre, montant, MENSUELLE)
        c = lambda *a, **k: deces_service.creer_collecte(self.conn, self.sec, *a, today=TODAY, **k)
        c("Mme Lawson", PARENT, date(2025, 12, 10))
        c("", MEMBRE, date(2026, 3, 14), membre_defunt_id=self.kossi.id)
        c("M. Dosseh", BEAU_PARENT, date(2026, 5, 2), membre_endeuille_id=self.efua.id, exempter_endeuille=True)
        c("Mme Tsogbé", PARENT, date(2026, 6, 20), membre_endeuille_id=self.abla.id, exempter_endeuille=True)
        for membre, montant in ((self.yawo, 10000), (self.efua, 20000),
                                (self.abla, 24000), (self.kossi, 10000)):
            self._pay25(membre, montant, FUNERAIRE)
        cot = parallele_service.creer_cotisation(
            self.conn, self.admin, "Projet salle des fêtes", date(2026, 1, 1), date(2026, 6, 30), 12000, 10000)
        for membre, montant in ((self.yawo, 12000), (self.abla, 10000), (self.efua, 6000)):
            self._pay25(membre, montant, PARALLELE, date(2026, 4, 1), cot)
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

    def test_mensuelle_dettes_et_avances_reportees(self):
        p = tableau_mensuel.tableau(self.conn, self.ex26.id)
        par = {l.membre.nom: l.releve for l in p.lignes}
        abla = par["Abla Tsogbé"]                                       # avance reportée de 12 000
        self.assertEqual((abla.carried_advance, [c.status for c in abla.cells][:2]), (12000, [cm.PARTIEL, cm.IMPAYE]))
        self.assertEqual((abla.cells[0].paid, abla.total_debt, abla.advance), (12000, 156000, 0))
        self.assertEqual((par["Yawo Agbodjan"].carried_debt, par["Efua Dosseh"].carried_debt,
                          par["Mina Gbedemah"].carried_debt), (85000, 18000, 112000))
        self.assertNotIn("Kossi Ayité", par)                            # décédé avant l'exercice, sans dette mensuelle
        self.assertEqual((p.general.dette_reportee, p.general.avance_reportee), (215000, 12000))

        self._pay26(self.yawo, 100000)
        self._pay26(self.efua, 10000)
        self._pay26(self.mina, 126000)
        par = {l.membre.nom: l.releve for l in tableau_mensuel.tableau(self.conn, self.ex26.id).lignes}
        yawo = par["Yawo Agbodjan"]                                     # 85 000 sur l'ancienne dette, 15 000 sur septembre
        self.assertEqual((yawo.carried_debt_paid, yawo.carried_debt_left, yawo.cells[0].status,
                          yawo.cells[0].paid, yawo.total_debt), (85000, 0, cm.PARTIEL, 15000, 201000))
        efua = par["Efua Dosseh"]                                       # 10 000 < 18 000 : les mois ne bougent pas
        self.assertEqual((efua.carried_debt_left, efua.total_debt, {c.status for c in efua.cells}),
                         (8000, 176000, {cm.IMPAYE}))
        mina = par["Mina Gbedemah"]
        self.assertEqual((mina.carried_debt_left, mina.cells[0].status, mina.total_debt), (0, cm.PAYE, 154000))
        self.assertEqual(versement_service.releve_mensuel(self.conn, self.yawo.id, self.ex26.id).total_debt, 201000)

    def test_funeraire_cotisation_en_cours_d_abord_puis_arrieres(self):
        deces_service.creer_collecte(self.conn, self.sec, "M. Test", PARENT, date(2026, 10, 3), today=TODAY26)
        recu = rs.enregistrer_paiement(self.conn, self.sec, self.yawo.id, self.ex26.id, "funeraire", 25000,
                                       date_versement=date(2026, 10, 5), today=TODAY26)
        self.assertEqual((recu.ventilation.courant, recu.ventilation.total_arrieres), (10000, 15000))
        s = deces_service.releve_funeraire(self.conn, self.yawo.id, self.ex26.id)
        self.assertEqual((s.carried_debt, s.carried_debt_paid, s.carried_debt_left), (30000, 15000, 15000))
        self.assertEqual([c.status for c in s.cells], [cm.PAYE])
        self.assertEqual((s.debt, s.total_debt), (0, 15000))
        efua = deces_service.releve_funeraire(self.conn, self.efua.id, self.ex26.id)      # femme : 8 000
        self.assertEqual((efua.carried_debt, efua.total_debt, efua.cells[0].status), (4000, 12000, cm.IMPAYE))
        self.assertEqual(tableau_funeraire.tableau(self.conn, self.ex26.id).general.dette_reportee, 58000)

    def test_bilan_de_l_exercice_suivant_avec_solde_d_ouverture(self):
        self._pay26(self.yawo, 100000)
        b = bilan_service.calculer(self.conn, self.ex26.id)
        m = b.ligne("mensuelle")
        self.assertEqual((m.du, m.dette_reportee, m.avance_reportee, m.percu, m.manque),
                         (720000, 215000, 12000, 100000, 823000))
        self.assertEqual(m.situation, Situation(DETTE, 823000))
        self.assertEqual((m.dettes, m.avances), (823000, 0))
        f, p, a = b.ligne("funeraire"), b.ligne("parallele"), b.ligne("amendes")
        self.assertEqual((f.du, f.dette_reportee, f.percu, f.manque), (0, 58000, 0, 58000))
        self.assertEqual((p.du, p.dette_reportee, p.manque), (0, 26000, 26000))
        self.assertEqual((a.du, a.dette_reportee, a.manque), (0, 6000, 6000))
        self.assertEqual(b.ligne("reliquats").percu, 0)
        for ligne in b.lignes:
            if ligne.du is not None:
                self.assertEqual(ligne.manque, ligne.dettes - ligne.avances, ligne.rubrique)
        self.assertEqual(b.total_entrees, 100000)
        self.assertEqual(b.situation_globale, Situation(DETTE, 913000))
        self.assertEqual((b.solde_ouverture, b.solde, b.solde_cumule), (-378000, 100000, -278000))
        self.assertEqual(b.situation_ouverture, Situation(DETTE, 378000))          # rouge, « Dette », sans signe moins
        self.assertEqual(b.situation_ouverture.couleur, "rouge")
        self.assertEqual(b.situation_solde, Situation(EXCEDENT, 100000))
        self.assertEqual(b.situation_cumulee, Situation(DETTE, 278000))

    def test_deuxieme_cloture_reporte_encore_ce_qui_reste_avec_son_annee_d_origine(self):
        self._pay26(self.yawo, 100000)
        res = cloture_service.cloturer(self.conn, self.admin, self.ex26.id, "CLÔTURER", today=date(2027, 9, 1))
        self.assertEqual(res.suivant.libelle, "2027-2028")
        lignes = reports.list_for_cible(self.conn, res.suivant.id)
        somme = lambda t, r: sum(l.montant for l in lignes if l.type == t and l.rubrique == r)
        self.assertEqual((somme("dette", "mensuelle"), somme("dette", "funeraire"),
                          somme("dette", "parallele"), somme("dette", "amende")), (823000, 58000, 26000, 6000))
        self.assertEqual(somme("avance", "mensuelle"), 0)                          # l'avance d'Abla a été consommée
        self.assertEqual([l.montant for l in lignes if l.type == "solde"], [-278000])
        par_origine = {}
        for l in lignes:
            if l.type == "dette" and l.rubrique == "mensuelle":
                par_origine[l.exercice_origine_id] = par_origine.get(l.exercice_origine_id, 0) + l.montant
        self.assertEqual(par_origine, {self.ex.id: 130000, self.ex26.id: 693000})   # l'ancienne dette garde son année
        for rubrique in ("funeraire", "parallele", "amende"):
            origines = {l.exercice_origine_id for l in lignes if l.type == "dette" and l.rubrique == rubrique}
            self.assertEqual(origines, {self.ex.id}, rubrique)


class MembreNonConcerneTest(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.addCleanup(self.conn.close)
        migrate(self.conn)
        self.admin, self.sec = sessions(self.conn)
        self.ex = exercice_service.create_exercice(self.conn, self.admin, 2025, 18000, 14000)
        self.parti = membre_service.create_membre(self.conn, self.admin, "Parti Endetté", Sexe.HOMME, ANCIEN, today=TODAY)
        membre_service.create_membre(self.conn, self.admin, "Ami Fidèle", Sexe.HOMME, ANCIEN, today=TODAY)
        membre_service.declare_deceased(self.conn, self.admin, self.parti.id, date(2026, 1, 15), today=TODAY)
        self.ex26 = cloture_service.cloturer(self.conn, self.admin, self.ex.id, "CLÔTURER", today=CLOTURE).suivant

    def test_un_membre_decede_garde_sa_dette_reportee_dans_le_tableau(self):
        par = {l.membre.nom: l.releve for l in tableau_mensuel.tableau(self.conn, self.ex26.id).lignes}
        parti = par["Parti Endetté"]                                   # décédé en janvier 2026 : 5 mois impayés
        self.assertEqual((parti.total_due, parti.carried_debt, parti.total_debt), (0, 90000, 90000))
        self.assertEqual({c.status for c in parti.cells}, {cm.NON_APPLICABLE})
        self.assertEqual(par["Ami Fidèle"].carried_debt, 216000)
        versement_service.enregistrer(self.conn, self.sec, self.parti.id, self.ex26.id, MENSUELLE,
                                      90000, date(2026, 10, 5), today=TODAY26)
        p = tableau_mensuel.tableau(self.conn, self.ex26.id)
        self.assertEqual(next(l.releve.total_debt for l in p.lignes if l.membre.nom == "Parti Endetté"), 0)
        en_dette = tableau_mensuel.tableau(self.conn, self.ex26.id, situation="dette")
        self.assertNotIn("Parti Endetté", [l.membre.nom for l in en_dette.lignes])


if __name__ == "__main__":
    unittest.main()