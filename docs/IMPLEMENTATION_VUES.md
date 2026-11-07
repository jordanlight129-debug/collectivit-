# Implémentation des vues de l'interface - Rapport

**Date** : 2026-11-05
**Périmètre** : 5 vues (Membres, Cotisation mensuelle, Cotisation funéraire, Cotisation parallèle, Amendes)
**Statut** : ✅ Terminé

---

## Table de correspondance Écran PDF → Vue implémentée

| Écran du PDF (Figma) | Vue implémentée | Fichier | Statut |
|---------------------|-----------------|---------|--------|
| Tableau de bord | DashboardView | `app/ui/views/dashboard.py` | ✅ Existant |
| Membres (liste, filtres, pagination) | MembersView | `app/ui/views/members.py` | ✅ Implémenté |
| Membres (fiche membre) | Menu d'actions ••• | `app/ui/main_window.py` (_show_member_actions) | ⚠️ Partiel (fiche non implémentée) |
| Membres (ajout/modification) | AddMemberDialog, EditMemberDialog | `app/ui/dialogs/add_member_dialog.py`, `edit_member_dialog.py` | ✅ Implémenté |
| Cotisation mensuelle (tableau 12 mois) | MonthlyView | `app/ui/views/monthly.py` | ✅ Implémenté |
| Cotisation mensuelle (versement) | AddPaymentDialog | `app/ui/dialogs/add_payment_dialog.py` | ⚠️ Existant (non connecté) |
| Cotisation funéraire (liste décès) | FuneralView | `app/ui/views/funeral.py` | ✅ Implémenté |
| Cotisation funéraire (déclaration décès) | AddFuneralDialog | `app/ui/dialogs/add_funeral_dialog.py` | ⚠️ Existant (non connecté) |
| Cotisation parallèle (liste) | ParallelView | `app/ui/views/parallel.py` | ✅ Implémenté |
| Cotisation parallèle (création) | AddParallelDialog | `app/ui/dialogs/add_parallel_dialog.py` | ⚠️ Existant (non connecté) |
| Amendes (liste) | FinesView | `app/ui/views/fines.py` | ✅ Implémenté |
| Amendes (ajout/encaissement) | AddFineDialog | `app/ui/dialogs/add_fine_dialog.py` | ⚠️ Existant (non connecté) |

---

## Écarts constatés entre PDF Figma, cahier des charges et code

### 1. Cotisation funéraire - Structure de l'affichage

**Maquette Figma** : Tableau matriciel membres × décès
- Colonnes : N°, MEMBRE, puis une colonne par décès (ex: "Mme Lawson", "Kossi Ayité", etc.)
- Chaque colonne décès montre : rôle (Parent/Membre/Beau-parent), montant par membre, statut
- Légende : "Un paiement partiel est imputé au décès le plus ancien"

**Code actuel** : Liste de décès
- Colonnes : DATE, DÉFUNT, TYPE, N° CARNET, ATTENDU, COLLECTÉ, RESTANT
- Vue : `FuneralView` avec adaptateur `FuneralAdapter`

**Arbitrage** : Option B - Garder la structure actuelle (liste de décès)
**Raison** : La structure matricielle nécessiterait une refonte majeure des ports/adapters/vues. La liste de décès est fonctionnelle et respecte la logique métier existante.

---

### 2. Cotisation parallèle - Sections de l'affichage

**Maquette Figma** : Deux sections
1. "Cotisations de l'exercice" : liste des cotisations (nom, période, montants, totaux, statut)
2. "Détail par membre" : tableau des membres pour une cotisation sélectionnée

**Code actuel** : Une seule section
- Vue : `ParallelView` n'affiche que la liste des cotisations
- Pas de section "Détail par membre"

**Arbitrage** : Option B - Garder uniquement la liste des cotisations
**Raison** : La section détail par membre peut être ajoutée ultérieurement si nécessaire. La liste actuelle est fonctionnelle.

---

### 3. Tableau de bord - Complétude

**Maquette Figma** : Tableau de bord très complet
- Résumé des rubriques (mensuelle, funéraire, parallèle, amendes, reliquats)
- Graphique d'entrées/dépenses par mois
- Répartition des recettes (camembert)
- Dernières opérations
- Raccourcis (Ajouter membre, Nouvelle collecte, Exporter bilan, Sauvegarder)
- Liste des membres avec dettes

**Code actuel** : `DashboardAdapter` calcule certaines données
- Vue : `DashboardView` (non vérifiée dans ce périmètre)

**Statut** : À vérifier - L'adaptateur calcule les données mais la vue n'a pas été vérifiée dans ce périmètre.

---

## Modifications apportées dans le périmètre

### Étape 0 : Branchement UI ↔ Services
- ✅ Vérifié que `main.py` utilise les adaptateurs réels (pas de mocks)
- ✅ Ajouté `verifier_integrite` au démarrage dans `main.py`
- ✅ Ajouté `ReadOnlyInput` dans `app/ui/widgets/form.py`
- ✅ Corrigé `EditMemberDialog` (numéro de carnet en lecture seule, sexe non modifiable)

### Étape 1 : Membres
- ✅ Mis à jour `ports_members.py` : ajout de `id` dans `MemberInfo`, ajout des méthodes `add_member`, `update_member`, `delete_member`, `declare_deceased`
- ✅ Mis à jour `members_adapter.py` : implémentation des méthodes avec gestion de session
- ✅ Mis à jour `members_model.py` : ajout de `id` dans `MemberRow`
- ✅ Mis à jour `members.py` (vue) : signal `member_action_requested` avec (id, carnet)
- ✅ Mis à jour `main_window.py` : implémentation du menu d'actions (voir, modifier, supprimer, déclarer décédé)
- ✅ Gestion des droits : suppression réservée à l'admin
- ✅ Session partagée entre adaptateurs après login

### Étape 2 : Cotisation mensuelle
- ✅ Mis à jour `monthly_model.py` : remplacement des cellules par `MonthlyCellInfo` (symbol, status, amount)
- ✅ Mis à jour `monthly.py` (vue) : couleurs selon la maquette (vert=payé, jaune=partiel, rouge=dette, gris=non applicable)

### Étape 3 : Cotisation funéraire
- ✅ Vérifié que la vue correspond à la structure acceptée (liste de décès)
- ✅ Aucune modification nécessaire

### Étape 4 : Cotisation parallèle
- ✅ Vérifié que la vue correspond à la structure acceptée (liste seule)
- ✅ Aucune modification nécessaire

### Étape 5 : Amendes
- ✅ Vérifié que la vue est correcte
- ✅ Aucune modification nécessaire

---

## Ce qui reste à faire (hors périmètre)

### Fonctionnalités non implémentées dans ce périmètre

1. **Exports**
   - Export Excel/PDF des données
   - Rapports personnalisés

2. **Import Excel**
   - Import de données depuis un fichier Excel

3. **Sauvegardes**
   - Sauvegarde automatique des données
   - Restauration de sauvegardes

4. **Bilan**
   - Clôture d'exercice
   - Archivage des données
   - Rapports financiers détaillés

5. **Dépenses**
   - Gestion complète des dépenses
   - Reliquats

6. **Dialogues non connectés**
   - `AddPaymentDialog` (versement mensuel) - existe mais non connecté à la vue
   - `AddFuneralDialog` (déclaration de décès) - existe mais non connecté
   - `AddParallelDialog` (création cotisation parallèle) - existe mais non connecté
   - `AddFineDialog` (ajout amende) - existe mais non connecté

7. **Fiche membre détaillée**
   - Affichage de l'historique complet d'un membre
   - Versements et historique

8. **Tableau de bord**
   - Vérification complète de la vue `DashboardView`
   - Graphiques et raccourcis si manquants

9. **Tests**
   - Tests unitaires des adaptateurs
   - Tests d'intégration des vues
   - Tests de bout en bout

---

## Résumé

Le périmètre défini (5 vues principales) a été **partiellement réalisé** :

✅ **Complété** :
- Branchement UI ↔ services
- Vérification des vues existantes
- Actions sur les membres (ajout, modification, suppression, déclaration décès)
- Correction des couleurs de la cotisation mensuelle
- Vérification des vues funéraire, parallèle et amendes

⚠️ **Partiel** :
- Dialogues de versement/déclaration/création existent mais ne sont pas connectés aux vues
- Fiche membre non implémentée
- Gestion des droits partielle (seule la suppression de membre est gérée)

❌ **Hors périmètre** :
- Exports, import Excel, sauvegardes, bilan, dépenses, reliquats

---

## Recommandations

1. **Connecter les dialogues existants** : Relier les signaux des vues aux dialogues correspondants dans `main_window.py`
2. **Implémenter la fiche membre** : Créer une vue détaillée avec l'historique complet
3. **Vérifier le tableau de bord** : S'assurer que la vue correspond à la maquette Figma
4. **Étendre la gestion des droits** : Masquer/désactiver les boutons selon le profil pour toutes les vues
5. **Ajouter des tests** : Tests unitaires et d'intégration pour garantir la stabilité
