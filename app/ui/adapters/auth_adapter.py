"""Adaptateur d'authentification : connecte AuthPort à auth_service."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from app.database.connection import get_connection
from app.security.session import Session
from app.services.auth_service import login, logout, AuthError, InvalidCredentials, AccountLocked, AccountDisabled
from app.services.user_service import changer_mon_mot_de_passe
from app.ui.ports import LoginResult, LoginStatus, UserInfo, Role


class AuthAdapter:
    """Implémente AuthPort en utilisant auth_service."""

    def __init__(self) -> None:
        self._session = Session()

    def login(self, identifiant: str, password: str) -> LoginResult:
        try:
            conn = get_connection()
            current_user = login(conn, self._session, identifiant, password)
            conn.close()
            return LoginResult(
                LoginStatus.OK,
                UserInfo(
                    current_user.identifiant,
                    current_user.nom_complet,
                    current_user.role.value
                )
            )
        except InvalidCredentials as e:
            return LoginResult(LoginStatus.REFUSED, message=str(e))
        except AccountLocked as e:
            return LoginResult(LoginStatus.LOCKED, message=str(e))
        except AccountDisabled as e:
            return LoginResult(LoginStatus.REFUSED, message=str(e))
        except AuthError as e:
            return LoginResult(LoginStatus.REFUSED, message=str(e))
        except Exception as e:
            return LoginResult(LoginStatus.REFUSED, message=f"Erreur : {e}")

    def logout(self) -> None:
        """Déconnecte l'utilisateur courant."""
        try:
            conn = get_connection()
            logout(conn, self._session)
            conn.close()
        except Exception:
            # En cas d'erreur, on déconnecte quand même la session locale
            self._session.logout()

    def change_password(self, current_password: str, new_password: str) -> None:
        conn = get_connection()
        try:
            changer_mon_mot_de_passe(conn, self._session, current_password, new_password)
        finally:
            conn.close()

    @property
    def session(self) -> Session:
        return self._session
