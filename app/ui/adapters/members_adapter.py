"""Adaptateur des membres : connecte MembersPort aux services."""
from __future__ import annotations

import sqlite3
from datetime import date

from app.database.connection import get_connection
from app.repositories import membres, exercices
from app.services.tableau_mensuel import tableau as tableau_mensuel
from app.services.membre_service import create_membre, update_membre, delete_membre, declare_deceased, MembreError
from app.security.session import Session
from app.ui.ports_members import MemberInfo, MembersData, MemberStatus


class MembersAdapter:
    """Implémente MembersPort en utilisant les services."""

    def __init__(self) -> None:
        self._session = Session()

    def _require_session(self) -> None:
        if not self._session.is_authenticated:
            raise PermissionError("Veuillez vous connecter.")

    def load(self, exercise_label: str) -> MembersData:
        conn = get_connection()
        try:
            exercice = conn.execute(
                "SELECT id, libelle, statut FROM exercices WHERE libelle = ?",
                (exercise_label,)
            ).fetchone()

            if not exercice:
                conn.close()
                return MembersData(exercise_label, True, ())

            exercice_id = exercice["id"]
            is_open = exercice["statut"] == "ouvert"

            # Récupérer tous les membres
            all_members = membres.list_(conn)

            # Calculer les totaux par membre pour cet exercice
            members_info = []
            for m in all_members:
                statut = MemberStatus.ACTIF if m.statut == "actif" else MemberStatus.DECEDE

                # Calculer dû et reçu pour cet exercice
                du = 0
                recu = 0

                if is_open:
                    # Utiliser le tableau mensuel pour calculer
                    try:
                        page = tableau_mensuel(conn, exercice_id)
                        for ligne in page.lignes:
                            if ligne.membre.id == m.id:
                                du = ligne.releve.total_due
                                recu = ligne.releve.total_paid
                                break
                    except Exception:
                        pass

                members_info.append(MemberInfo(
                    m.numero_carnet,
                    m.id,
                    m.nom,
                    m.sexe.value,
                    m.date_adhesion,
                    statut,
                    du,
                    recu
                ))

            conn.close()
            return MembersData(exercise_label, is_open, tuple(members_info))
        except Exception as e:
            conn.close()
            print(f"Erreur members adapter: {e}")
            import traceback
            traceback.print_exc()
            return MembersData(exercise_label, True, ())

    def add_member(self, nom: str, sexe: str, date_adhesion: str) -> int:
        """Ajoute un nouveau membre."""
        self._require_session()
        from app.models.sexe import Sexe
        conn = get_connection()
        try:
            adhesion_date = date.fromisoformat(date_adhesion)
            sexe_enum = Sexe.HOMME if sexe == "M" else Sexe.FEMME

            membre = create_membre(conn, self._session, nom, sexe_enum, adhesion_date)

            conn.commit()
            conn.close()
            return membre.id
        except MembreError as e:
            conn.close()
            raise e
        except Exception as e:
            conn.close()
            raise Exception(f"Erreur lors de l'ajout du membre: {e}")

    def update_member(self, membre_id: int, nom: str, date_adhesion: str) -> None:
        """Modifie un membre existant."""
        self._require_session()
        conn = get_connection()
        try:
            # Récupérer le membre pour obtenir son sexe (non modifiable)
            membre = membres.get(conn, membre_id)
            if not membre:
                raise MembreError("Membre introuvable")

            adhesion_date = date.fromisoformat(date_adhesion)

            update_membre(conn, self._session, membre_id, nom, membre.sexe, adhesion_date)

            conn.commit()
            conn.close()
        except MembreError as e:
            conn.close()
            raise e
        except Exception as e:
            conn.close()
            raise Exception(f"Erreur lors de la modification du membre: {e}")

    def delete_member(self, membre_id: int) -> None:
        """Supprime un membre (admin uniquement)."""
        self._require_session()
        conn = get_connection()
        try:
            delete_membre(conn, self._session, membre_id)

            conn.commit()
            conn.close()
        except MembreError as e:
            conn.close()
            raise e
        except Exception as e:
            conn.close()
            raise Exception(f"Erreur lors de la suppression du membre: {e}")

    def declare_deceased(self, membre_id: int, date_deces: str) -> None:
        """Déclare un membre décédé."""
        self._require_session()
        conn = get_connection()
        try:
            deces_date = date.fromisoformat(date_deces)

            declare_deceased(conn, self._session, membre_id, deces_date)

            conn.commit()
            conn.close()
        except MembreError as e:
            conn.close()
            raise e
        except Exception as e:
            conn.close()
            raise Exception(f"Erreur lors de la déclaration de décès: {e}")