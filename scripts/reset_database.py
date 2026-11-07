"""Script de remise à zéro de la base de données.

⚠️  ATTENTION : Ce script supprime TOUTES les données de la base de données.
Utilisez-le uniquement pour une réinitialisation complète ou en développement.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import get_connection
from app.database.schema import migrate


def confirm_reset() -> bool:
    """Demande confirmation à l'utilisateur."""
    print("\n" + "=" * 60)
    print("⚠️  REMISE À ZÉRO DE LA BASE DE DONNÉES")
    print("=" * 60)
    print("\nCette action va :")
    print("  - Supprimer tous les utilisateurs")
    print("  - Supprimer tous les membres")
    print("  - Supprimer toutes les cotisations")
    print("  - Supprimer tous les décès")
    print("  - Supprimer toutes les amendes")
    print("  - Supprimer toutes les dépenses")
    print("  - Réinitialiser le schéma de la base")
    print("\nCette action est IRRÉVERSIBLE !")
    print("\nÊtes-vous sûr de vouloir continuer ? (oui/non)")

    response = input("> ").strip().lower()
    return response in ("oui", "yes", "o", "y")


def reset_database() -> None:
    """Remet la base de données à zéro."""
    print("\n🔄 Suppression de la base de données existante...")

    db_path = Path("data/association.db")
    if db_path.exists():
        db_path.unlink()
        print("✓ Base de données supprimée")
    else:
        print("✓ Aucune base de données existante")

    print("\n🔄 Création de la nouvelle base de données...")
    conn = get_connection()
    migrate(conn)
    conn.close()
    print("✓ Base de données créée et migrée")

    print("\n✅ Remise à zéro terminée avec succès !")
    print("\n📝 Prochaine étape :")
    print("   Lancez l'application : python main.py")
    print("   L'écran de premier démarrage vous demandera de créer l'administrateur.")


def main() -> int:
    """Point d'entrée du script."""
    if not confirm_reset():
        print("\n❌ Opération annulée")
        return 1

    try:
        reset_database()
        return 0
    except Exception as e:
        print(f"\n❌ Erreur lors de la remise à zéro : {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
