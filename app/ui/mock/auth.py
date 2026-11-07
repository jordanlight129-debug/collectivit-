"""Authentification fictive pour la démonstration de l'interface (aucun accès à la base)."""
from __future__ import annotations

from app.security.passwords import validate_policy
from app.security.session import CurrentUser, Session
from app.ui.ports import LoginResult, LoginStatus, Role, UserInfo

MAX_ATTEMPTS = 5            # à aligner sur auth_service au branchement
LOCK_MINUTES = 15

_COMPTES = {
    "admin": ("Admin2026", "Ama Kpodar", Role.ADMINISTRATEUR),
    "yawa": ("Secret2026", "Yawa Dovi", Role.SECRETAIRE),
}


class MockAuth:
    """Deux comptes fictifs. Cinq échecs verrouillent l'identifiant (jusqu'à la fermeture)."""

    def __init__(self) -> None:
        self._echecs: dict[str, int] = {}
        self._comptes = dict(_COMPTES)
        self.session = Session()

    def login(self, identifiant: str, password: str) -> LoginResult:
        cle = identifiant.strip().lower()
        if self._echecs.get(cle, 0) >= MAX_ATTEMPTS:
            return self._verrouille()
        compte = self._comptes.get(cle)
        if compte is not None and compte[0] == password:
            self._echecs.pop(cle, None)
            user_info = UserInfo(cle, compte[1], compte[2])
            # Créer un CurrentUser et le stocker dans la session
            current_user = CurrentUser(
                id=1 if cle == "admin" else 2,
                identifiant=cle,
                nom_complet=compte[1],
                role=compte[2]
            )
            self.session.login(current_user)
            return LoginResult(LoginStatus.OK, user_info)
        echecs = self._echecs.get(cle, 0) + 1
        self._echecs[cle] = echecs
        if echecs >= MAX_ATTEMPTS:
            return self._verrouille()
        restantes = MAX_ATTEMPTS - echecs
        pluriel = "s" if restantes > 1 else ""
        return LoginResult(LoginStatus.REFUSED, message=(
            f"Identifiant ou mot de passe incorrect. Il vous reste {restantes} tentative{pluriel}."))

    @staticmethod
    def _verrouille() -> LoginResult:
        return LoginResult(LoginStatus.LOCKED, message=(
            f"Compte verrouillé après {MAX_ATTEMPTS} tentatives échouées. Réessayez dans {LOCK_MINUTES} minutes "
            "ou demandez à l’administrateur de réinitialiser votre mot de passe."))

    def logout(self) -> None:
        self.session.logout()

    def change_password(self, current_password: str, new_password: str) -> None:
        user = self.session.user
        compte = self._comptes[user.identifiant]
        if current_password != compte[0]:
            raise ValueError("Le mot de passe actuel est incorrect.")
        if new_password == current_password:
            raise ValueError("Le nouveau mot de passe doit être différent de l'ancien.")
        validate_policy(new_password)
        self._comptes[user.identifiant] = (new_password, compte[1], compte[2])
