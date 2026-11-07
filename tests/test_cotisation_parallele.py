import unittest
from datetime import date

from app.models.cotisation_parallele import CotisationParallele
from app.models.membre import Membre
from app.models.sexe import Sexe
from app.services.cotisation_mensuelle import IMPAYE, NON_APPLICABLE, PARTIEL, PAYE
from app.services.cotisation_parallele import build_statement

COT = CotisationParallele(1, 1, "Salle des fêtes", date(2026, 1, 1), date(2026, 6, 30), 12000, 10000)


def membre(sexe=Sexe.HOMME, adhesion=date(2017, 9, 5), deces=None):
    return Membre(1, "0001", "Test", sexe, adhesion, "decede" if deces else "actif", deces)


class ParalleleTest(unittest.TestCase):
    def test_montant_selon_le_sexe_et_paye(self):
        h = build_statement(membre(Sexe.HOMME), COT, 12000)
        f = build_statement(membre(Sexe.FEMME), COT, 10000)
        self.assertEqual((h.due, h.status, h.debt), (12000, PAYE, 0))
        self.assertEqual((f.due, f.status, f.debt), (10000, PAYE, 0))

    def test_partiel_et_impaye(self):
        p = build_statement(membre(Sexe.FEMME), COT, 6000)
        self.assertEqual((p.status, p.debt), (PARTIEL, 4000))
        i = build_statement(membre(Sexe.HOMME), COT, 0)
        self.assertEqual((i.status, i.debt), (IMPAYE, 12000))

    def test_adhesion_en_cours_de_periode_montant_entier(self):
        s = build_statement(membre(Sexe.FEMME, adhesion=date(2026, 3, 10)), COT, 0)
        self.assertEqual((s.concerned, s.due), (True, 10000))

    def test_non_concerne(self):
        apres = build_statement(membre(adhesion=date(2026, 7, 1)), COT, 0)
        decede = build_statement(membre(deces=date(2025, 12, 31)), COT, 0)
        for s in (apres, decede):
            self.assertEqual((s.concerned, s.due, s.status, s.debt), (False, 0, NON_APPLICABLE, 0))

    def test_excedent(self):
        s = build_statement(membre(Sexe.HOMME), COT, 15000)
        self.assertEqual((s.status, s.debt, s.advance), (PAYE, 0, 3000))

    def test_total_verse_negatif_refuse(self):
        with self.assertRaises(ValueError):
            build_statement(membre(), COT, -1)


if __name__ == "__main__":
    unittest.main()