#!/usr/bin/env python
"""Réinitialise le mot de passe de l'administrateur existant ou en crée un nouveau."""
from __future__ import annotations

import getpass
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DB_PATH
from app.database.connection import get_connection, transaction
from app.repositories import utilisateurs
from app.security.session import Role
from app.security.passwords import hash_password, validate_policy, PasswordPolicyError
from app.security.audit import Action
from app.security import audit
from app.security.session import Session, CurrentUser


def backup_database(db_path: Path) -> Path:
    """Crée une sauvegarde datée de la base de données."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"association_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    return backup_path


def main() -> int:
    print("=== Réinitialisation du mot de passe administrateur ===\n")
    
    # Vérifier que l'application n'est pas en cours d'exécution
    print("[!] IMPORTANT : Fermez l'application avant de continuer.")
    reponse = input("L'application est-elle fermee ? (o/n) : ").strip().lower()
    if reponse != 'o':
        print("\n[ERREUR] Annulation. Fermez l'application puis relancez ce script.")
        return 1
    
    db_path = DB_PATH
    if not db_path.exists():
        print(f"\n[ERREUR] Base de donnees introuvable : {db_path}")
        return 1
    
    # Créer une sauvegarde
    print(f"\n[*] Sauvegarde de la base de donnees...")
    backup_path = backup_database(db_path)
    print(f"[OK] Sauvegarde creee : {backup_path}")
    
    identifiant = input("Identifiant [admin] : ").strip() or "admin"
    nom_complet = input("Nom complet [Administrateur] : ").strip() or "Administrateur"
    
    while True:
        mot_de_passe = getpass.getpass("Mot de passe : ")
        if not mot_de_passe:
            print("Le mot de passe ne peut pas être vide.")
            continue
        
        confirmation = getpass.getpass("Confirmer le mot de passe : ")
        if mot_de_passe != confirmation:
            print("Les mots de passe ne correspondent pas.")
            continue
        
        try:
            validate_policy(mot_de_passe)
            break
        except PasswordPolicyError as e:
            print(f"Mot de passe non conforme : {e}")
    
    conn = get_connection()
    try:
        # Vérifier si l'utilisateur existe
        user = utilisateurs.get_by_identifiant(conn, identifiant)
        
        password_hash = hash_password(mot_de_passe)
        
        with transaction(conn):
            if user:
                # Mettre à jour l'utilisateur existant
                utilisateurs.update_hash(conn, user.id, password_hash)
                user_id = user.id
                action = "Mot de passe réinitialisé"
                audit_action = Action.UTILISATEUR_MODIF
            else:
                # Créer un nouvel administrateur
                user_id = utilisateurs.create(
                    conn,
                    identifiant,
                    nom_complet,
                    password_hash,
                    Role.ADMINISTRATEUR
                )
                action = "Compte administrateur créé"
                audit_action = Action.UTILISATEUR_AJOUT
            
            # Journal d'audit
            session = Session()
            session.login(CurrentUser(user_id, identifiant, nom_complet, Role.ADMINISTRATEUR))
            audit.log(conn, session.user, audit_action, identifiant, action)
        
        print(f"\n[OK] {action} avec succes.")
        print(f"  Identifiant : {identifiant}")
        print(f"  Nom complet : {nom_complet}")
        print(f"\n[*] Sauvegarde conservee : {backup_path}")
        return 0
    except Exception as e:
        print(f"\n[ERREUR] Erreur : {e}")
        print(f"[*] Sauvegarde disponible : {backup_path}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
