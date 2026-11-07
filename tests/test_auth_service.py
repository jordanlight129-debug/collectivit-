import sqlite3
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.database.connection import transaction
from app.database.schema import migrate
from app.repositories import utilisateurs
from app.security import audit
from app.security.passwords import PasswordPolicyError, hash_password
from app.security.session import Role, Session
from app.services import auth_service as auth
from app.services.auth_service import (
    AccountDisabled, AccountLocked, AuthError, InvalidCredentials,
)

T0 = datetime(2026, 10, 21, 10, 0, 0)


class AuthServiceTest(unittest.TestCase):
    def setUp(self):
        patcher = patch("app.security.passwords.ITERATIONS", 1000)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        migrate(self.conn)
        self.session = Session()
        auth.create_first_admin(self.conn, "ama", "Ama Kpodar", "Secret2026")

    def _login(self, ident, pwd, now=T0):
        return auth.login(self.conn, self.session, ident, pwd, now=now)

    def test_connexion_reussie(self):
        user = self._login("AMA", "Secret2026")          # insensible à la casse
        self.assertEqual(user.role, Role.ADMINISTRATEUR)
        self.assertTrue(self.session.is_authenticated)
        self.assertEqual(audit.list_entries(self.conn)[0]["action"], audit.Action.CONNEXION)

    def test_deuxieme_administrateur_refuse(self):
        with self.assertRaises(AuthError):
            auth.create_first_admin(self.conn, "autre", "Autre", "Secret2026")

    def test_mot_de_passe_faible_refuse(self):
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        self.addCleanup(c.close)
        migrate(c)
        with self.assertRaises(PasswordPolicyError):
            auth.create_first_admin(c, "ama", "Ama", "court")

    def test_essais_restants_puis_verrouillage(self):
        with self.assertRaises(InvalidCredentials) as ctx:
            self._login("ama", "faux")
        self.assertEqual(ctx.exception.remaining, 4)
        for _ in range(3):
            with self.assertRaises(InvalidCredentials):
                self._login("ama", "faux")
        with self.assertRaises(AccountLocked):            # 5e échec
            self._login("ama", "faux")
        with self.assertRaises(AccountLocked):            # même avec le bon mot de passe (verrou de 30s)
            self._login("ama", "Secret2026", now=T0 + timedelta(seconds=20))
        self.assertFalse(self.session.is_authenticated)
        self._login("ama", "Secret2026", now=T0 + timedelta(seconds=31))  # après expiration du verrou
        self.assertTrue(self.session.is_authenticated)

    def test_identifiant_inconnu_meme_message(self):
        with self.assertRaises(InvalidCredentials) as ctx:
            self._login("fantome", "Secret2026")
        self.assertIsNone(ctx.exception.remaining)
        self.assertEqual(audit.list_entries(self.conn)[0]["identifiant"], "fantome")

    def test_compte_desactive(self):
        with transaction(self.conn):
            uid = utilisateurs.create(self.conn, "yawa", "Yawa Dovi", hash_password("Secret2026"), Role.SECRETAIRE)
            utilisateurs.set_active(self.conn, uid, False)
        with self.assertRaises(AccountDisabled):
            self._login("yawa", "Secret2026")

    def test_deconnexion_journalisee(self):
        self._login("ama", "Secret2026")
        auth.logout(self.conn, self.session)
        self.assertFalse(self.session.is_authenticated)
        self.assertEqual(audit.list_entries(self.conn)[0]["action"], audit.Action.DECONNEXION)

    def test_verrouillage_apres_5_echecs_non_regression(self):
        """Test de non-régression : le verrouillage doit persister après 5 échecs."""
        # 5 échecs consécutifs
        for _ in range(5):
            with self.assertRaises((InvalidCredentials, AccountLocked)):
                self._login("ama", "faux")
        # Le compte doit être verrouillé, même avec le bon mot de passe
        with self.assertRaises(AccountLocked):
            self._login("ama", "Secret2026", now=T0 + timedelta(seconds=10))
        # Le compteur d'échecs doit avoir été remis à zéro après verrouillage
        # Une nouvelle tentative échouée ne doit pas re-verrouiller immédiatement
        # (le compteur a été remis à 0 par record_failure avec 0)
        with self.assertRaises(InvalidCredentials) as ctx:
            self._login("ama", "faux", now=T0 + timedelta(seconds=31))
        self.assertEqual(ctx.exception.remaining, 4)  # 1 échec sur 5 autorisés


if __name__ == "__main__":
    unittest.main()