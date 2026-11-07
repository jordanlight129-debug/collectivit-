"""Paiement des cotisations funéraires et parallèles, et règlement des arriérés.

- « Cotisation en cours » = ce qui est dû dans l'exercice ouvert.
- « Arriérés » = dettes reportées d'exercices clôturés (funéraire, parallèle, amendes).
- Versement global : la cotisation en cours d'abord, puis le reliquat aux arriérés
  (la plus ancienne année d'abord). Option « arriérés seulement ».
- Les arriérés sont réglés dans l'exercice ouvert ; un exercice clôturé n'est jamais modifié.
- Un excédent n'est enregistré (comme avance) qu'après confirmation.
Chaque paiement produit un reçu : une ligne « courant » et une ligne « arriéré » par année d'origine.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from app.database.connection import transaction
from app.models.exercice import Exercice
from app.models.versement import RUBRIQUE_LABELS, Versement
from app.repositories import cotisations_paralleles, exercices, membres, reports, versements
from app.security import audit
from app.security.audit import Action
from app.security.session import Permission, Session
from app.services import carnet_service, deces_service, parallele_service
from app.services.regles import concerned_by_parallel

GLOBAL = "global"
ARRIERES = "arrieres"
RUBRIQUES = ("funeraire", "parallele", "amende")


class ReglementError(Exception):
    """Règle de paiement non respectée (message affichable)."""


class ExcedentError(ReglementError):
    """Le montant dépasse ce qui est dû : l'excédent doit être confirmé."""

    def __init__(self, excedent: int) -> None:
        self.excedent = excedent
        super().__init__(
            f"Le montant dépasse ce qui est dû de {_fmt(excedent)}. "
            "L'excédent sera enregistré comme avance : confirmez pour continuer.")


@dataclass(frozen=True)
class Arrieres:
    rubrique: str
    par_origine: tuple[tuple[Exercice, int], ...]    # (exercice d'origine, reste dû), le plus ancien d'abord

    @property
    def total(self) -> int:
        return sum(montant for _, montant in self.par_origine)


@dataclass(frozen=True)
class Ventilation:
    montant: int
    courant: int                                     # affecté à la cotisation en cours
    arrieres: tuple[tuple[Exercice, int], ...]       # (exercice d'origine, montant remboursé)
    excedent: int                                    # au-delà du dû : devient une avance
    cible: str | None                                # cotisation en cours visée

    @property
    def total_arrieres(self) -> int:
        return sum(montant for _, montant in self.arrieres)


@dataclass(frozen=True)
class Recu:
    numero: int
    lignes: tuple[Versement, ...]
    ventilation: Ventilation


def _fmt(amount: int) -> str:
    return f"{amount:,}".replace(",", "\u00A0") + " FCFA"


def _d(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def arrieres(conn: sqlite3.Connection, membre_id: int, exercice_id: int, rubrique: str) -> Arrieres:
    """Arriérés restant dus par un membre, par exercice d'origine, au sein de l'exercice donné."""
    if rubrique not in RUBRIQUES:
        raise ReglementError("Rubrique inconnue.")
    if exercices.get(conn, exercice_id) is None:
        raise ReglementError("Exercice introuvable.")
    recus = reports.by_member_and_origin(conn, exercice_id, "dette", rubrique).get(membre_id, [])
    payes = versements.arrears_paid_by_origin(conn, exercice_id, membre_id, rubrique)
    restes = []
    for origine_id, montant in recus:
        reste = montant - payes.get(origine_id, 0)
        if reste > 0:
            restes.append((exercices.get(conn, origine_id), reste))
    return Arrieres(rubrique, tuple(restes))


def _preparer(conn, membre_id, exercice_id, rubrique, montant, mode, cotisation_id):
    if rubrique == "mensuelle":
        raise ReglementError("La cotisation mensuelle se règle par un versement ordinaire : "
                             "la plus ancienne dette est payée d'abord, automatiquement.")
    if rubrique not in RUBRIQUES:
        raise ReglementError("Rubrique inconnue.")
    if mode not in (GLOBAL, ARRIERES):
        raise ReglementError("Mode de paiement inconnu (global ou arriérés seulement).")
    if isinstance(montant, bool) or not isinstance(montant, int) or montant <= 0:
        raise ReglementError("Le montant doit être un entier positif (en FCFA).")
    exercice = exercices.get(conn, exercice_id)
    if exercice is None:
        raise ReglementError("Exercice introuvable.")
    if not exercice.is_open:
        raise ReglementError(f"L'exercice {exercice.libelle} est clôturé : ses écritures ne peuvent plus changer. "
                             "Les arriérés se règlent dans l'exercice en cours.")
    membre = membres.get(conn, membre_id)
    if membre is None:
        raise ReglementError("Membre introuvable.")
    if rubrique == "amende":
        mode = ARRIERES          # les amendes en cours s'encaissent une par une, les arriérés ici

    cotisation = None
    courant_du = 0
    cible = None
    if mode == GLOBAL:
        if rubrique == "funeraire":
            courant_du = deces_service.releve_funeraire(conn, membre.id, exercice.id).debt
            cible = f"Cotisation funéraire de l'exercice {exercice.libelle}" if courant_du > 0 else None
        else:
            if cotisation_id is None:
                raise ReglementError("Choisissez la cotisation parallèle à payer, ou réglez uniquement vos arriérés.")
            cotisation = cotisations_paralleles.get(conn, cotisation_id)
            if cotisation is None:
                raise ReglementError("Cotisation parallèle introuvable.")
            if cotisation.exercice_id != exercice.id:
                raise ReglementError("Cette cotisation parallèle n'appartient pas à l'exercice en cours.")
            if not concerned_by_parallel(membre.date_adhesion, membre.date_deces,
                                         cotisation.date_debut, cotisation.date_fin):
                raise ReglementError(f"{membre.nom} n'est pas concerné par la cotisation « {cotisation.nom} ».")
            courant_du = parallele_service.releve_parallele(conn, membre.id, cotisation.id).debt
            cible = f"Cotisation « {cotisation.nom} »"

    restants = arrieres(conn, membre.id, exercice.id, rubrique)
    courant = min(montant, courant_du)
    reste = montant - courant
    parts = []
    for origine, du in restants.par_origine:
        if reste <= 0:
            break
        part = min(reste, du)
        parts.append((origine, part))
        reste -= part
    if mode == ARRIERES:
        if restants.total == 0:
            raise ReglementError(f"{membre.nom} n'a aucun arriéré à régler pour cette rubrique.")
        if reste > 0:
            raise ReglementError(f"Le montant dépasse les arriérés restants ({_fmt(restants.total)}).")
    return membre, exercice, cotisation, Ventilation(montant, courant, tuple(parts), reste, cible)


def apercu_paiement(conn: sqlite3.Connection, membre_id: int, exercice_id: int, rubrique: str,
                    montant: int, mode: str = GLOBAL, cotisation_id: int | None = None) -> Ventilation:
    """Aperçu affiché avant de valider : comment le montant sera réparti. N'écrit rien."""
    return _preparer(conn, membre_id, exercice_id, rubrique, montant, mode, cotisation_id)[3]


def enregistrer_paiement(conn: sqlite3.Connection, session: Session, membre_id: int, exercice_id: int,
                         rubrique: str, montant: int, *, mode: str = GLOBAL,
                         cotisation_id: int | None = None, date_versement: date | None = None,
                         note: str | None = None, confirmer_excedent: bool = False,
                         today: date | None = None) -> Recu:
    """Enregistre un paiement (global ou arriérés seulement) et retourne le reçu."""
    session.require(Permission.PAYMENT_CREATE)
    today = today or date.today()
    membre, exercice, cotisation, v = _preparer(conn, membre_id, exercice_id, rubrique, montant,
                                                mode, cotisation_id)
    date_v = date_versement or today
    if not isinstance(date_v, date):
        raise ReglementError("La date du paiement est invalide.")
    if date_v > today:
        raise ReglementError("La date du paiement ne peut pas être dans le futur.")
    if date_v < membre.date_adhesion:
        raise ReglementError(f"La date du paiement ne peut pas précéder l'adhésion ({_d(membre.date_adhesion)}).")
    note = " ".join((note or "").split()) or None
    if note and len(note) > 200:
        raise ReglementError("La note est trop longue (200 caractères maximum).")
    if v.excedent > 0 and not confirmer_excedent:
        raise ExcedentError(v.excedent)

    with transaction(conn):
        numero = versements.next_recu(conn)
        ids = []
        courant_enregistre = v.courant + v.excedent
        if courant_enregistre > 0:
            ids.append(versements.add(
                conn, membre.id, exercice.id, rubrique, date_v, courant_enregistre, note,
                session.user.id, cotisation.id if cotisation else None, "courant", None, numero))
        for origine, part in v.arrieres:
            ids.append(versements.add(
                conn, membre.id, exercice.id, rubrique, date_v, part, note,
                session.user.id, None, "arriere", origine.id, numero))

        parties = []
        if v.courant > 0:
            parties.append(f"cotisation en cours {_fmt(v.courant)}")
        for origine, part in v.arrieres:
            parties.append(f"arriérés de {origine.libelle} {_fmt(part)}")
        if v.excedent > 0:
            parties.append(f"excédent (avance) {_fmt(v.excedent)}")
        detail = (f"Reçu n° {numero} · {RUBRIQUE_LABELS[rubrique]} · {_fmt(montant)} · "
                  + " · ".join(parties) + f" · {_d(date_v)} · exercice {exercice.libelle}")
        action = Action.REGLEMENT_ARRIERES if v.arrieres else Action.VERSEMENT_AJOUT
        audit.log(conn, session.user, action, carnet_service.format_carnet_label(membre.numero_carnet), detail)

    return Recu(numero, tuple(versements.get(conn, i) for i in ids), v)