# tests/test_session.py
import unittest

from app.security.session import (
    CurrentUser, NotAuthenticated, Permission, PermissionDenied, Role, Session,
)


def user(role):
    return CurrentUser(1, "x", "X", role)


class SessionTest(unittest.TestCase):
    def test_non_connecte(self):
        s = Session()
        self.assertFalse(s.is_authenticated)
        self.assertFalse(s.can(Permission.EXPORT))
        with self.assertRaises(NotAuthenticated):
            s.require(Permission.EXPORT)

    def test_administrateur_a_tous_les_droits(self):
        s = Session()
        s.login(user(Role.ADMINISTRATEUR))
        self.assertTrue(all(s.can(p) for p in Permission))

    def test_secretaire_limite(self):
        s = Session()
        s.login(user(Role.SECRETAIRE))
        self.assertTrue(s.can(Permission.MEMBER_CREATE))
        self.assertTrue(s.can(Permission.PARALLEL_DEFINE))
        self.assertTrue(s.can(Permission.PAYMENT_CREATE))
        for interdit in (Permission.MEMBER_EDIT, Permission.PAYMENT_EDIT, Permission.DELETE,
                 Permission.USERS_MANAGE, Permission.AUDIT_VIEW, Permission.EXERCISE_CLOSE,
                 Permission.BALANCE_VIEW, Permission.BACKUP_MANAGE, Permission.SETTINGS_MANAGE):
            self.assertFalse(s.can(interdit))
        with self.assertRaises(PermissionDenied):
            s.require(Permission.DELETE)

    def test_deconnexion(self):
        s = Session()
        s.login(user(Role.SECRETAIRE))
        s.logout()
        self.assertFalse(s.is_authenticated)


if __name__ == "__main__":
    unittest.main()