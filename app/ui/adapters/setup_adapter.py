"""Adaptateur pour le premier démarrage."""
from __future__ import annotations

from app.database.connection import get_connection, transaction
from app.repositories import utilisateurs
from app.security.session import Role
from app.security.passwords import hash_password, validate_policy, PasswordPolicyError
from app.security.audit import Action
from app.security import audit
from app.security.session import Session, CurrentUser


class SetupAdapter:
    """Implémente SetupPort pour la création du premier administrateur."""

    def create_admin(self, identifiant: str, mot_de_passe: str, nom_complet: str) -> int:
        """Crée le premier administrateur."""
        conn = get_connection()
        try:
            # Vérifier qu'aucun utilisateur n'existe déjà
            count = conn.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0]
            if count > 0:
                raise Exception("Un utilisateur existe déjà")

            # Valider le mot de passe
            try:
                validate_policy(mot_de_passe)
            except PasswordPolicyError as e:
                raise Exception(str(e))

            # Hacher le mot de passe
            password_hash = hash_password(mot_de_passe)

            # Créer l'utilisateur
            with transaction(conn):
                user_id = utilisateurs.create(
                    conn,
                    identifiant,
                    nom_complet,
                    password_hash,
                    Role.ADMINISTRATEUR
                )

                # Journal d'audit
                session = Session()
                session.login(CurrentUser(user_id, identifiant, nom_complet, Role.ADMINISTRATEUR))
                audit.log(conn, session.user, Action.COMPTE_CREATION, "Premier démarrage",
                          f"Compte administrateur créé : {identifiant}")

            conn.commit()
            conn.close()
            return user_id
        except Exception as e:
            conn.close()
            raise
