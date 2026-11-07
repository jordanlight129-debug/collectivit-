"""Données factices de démonstration (remplacées plus tard par les paramètres et les services)."""
from __future__ import annotations

from app.config import ASSOCIATION_NAME, BRAND_INITIALS
from app.ui.ports import ExerciseInfo, NotificationInfo

BRAND_NAME = ASSOCIATION_NAME
BRAND_SUB = "Gestion d’association"
ASSOCIATION_NAME = f"Association {ASSOCIATION_NAME}"
SIDEBAR_FOOTER = "Version 1.0 · Mode hors ligne"
LOGIN_TAGLINE = "Cotisations, dépenses et bilan de l’exercice, en toute transparence."
LOGIN_FEATURES = (
    "Fonctionne sans connexion Internet",
    "Données enregistrées localement sur cet ordinateur",
    "Chaque action est consignée dans le journal d’audit",
)
LOGIN_FOOTER = "Version 1.0 · Windows 10 / 11"

EXERCISES = (
    ExerciseInfo("2025–2026", True),
    ExerciseInfo("2024–2025", False),
    ExerciseInfo("2023–2024", False),
)

NOTIFICATIONS = (
    NotificationInfo("Fin d’exercice proche", "L’exercice 2025–2026 se termine dans 14 jours.", "Aujourd’hui"),
    NotificationInfo("Cotisation parallèle", "« Fête de rentrée » : 3 membres n’ont pas encore payé.", "Hier"),
    NotificationInfo("Sauvegarde", "Dernière sauvegarde automatique : 28/08/2026 à 17:42.", "28/08/2026"),
)

LAST_BACKUP = "Dernière sauvegarde : 28/08/2026 à 17:42"
DEMO_NOTICE = "Données fictives de démonstration"