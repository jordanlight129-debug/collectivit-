RAPPORT D'AUDIT COMPLET - Gestion d'Association
1. RÉSUMÉ GLOBAL
Note globale : 7.5/10

Notes par domaine :

Sécurité : 8.5/10
Qualité du code : 8/10
Calculs financiers : 9/10
Conformité au cahier des charges : 7/10
Tests : 8/10
Documentation : 3/10
2. TABLEAU DES PROBLÈMES
Gravité	Fichier:ligne	Description	Correction recommandée
Critique	App non connectée à la logique métier	L'interface utilise des mocks (MockAuth, MockDashboard) sans connexion aux services réels. Il n'y a pas d'adaptateurs entre l'UI et les services.	Créer des adaptateurs dans app/ui/adapters/ qui implémentent AuthPort et DashboardPort en appelant auth_service et bilan_service. Remplacer les mocks dans main_window.py.
Critique	Absence d'exports Excel/PDF	Les dépendances openpyxl et reportlab sont présentes mais aucun code d'export n'existe. Le cahier des charges exige des exports multiples.	Implémenter un module app/services/export_service.py avec fonctions pour générer les rapports Excel et PDF exigés (bilan, membres, cotisations, dettes, journal, reçus).
Élevée	main.py:32	Lancement direct avec des mocks au lieu de brancher sur les services authentiques.	Remplacer MockAuth() et MockDashboard() par des adaptateurs réels connectés aux services.
Élevée	Cotisation funéraire - incohérence cahier/maquette	Le code (deces_service.py:3-6) fixe le montant selon le sexe uniquement, alors que la maquette montre des montants par type de décès. Le cahier mentionne les deux approches.	Clarifier dans la documentation ou le code quelle approche est retenue. Actuellement le code privilégie "selon le sexe" ce qui est techniquement valide mais diffère de la maquette.
Moyenne	Sauvegarde automatique partielle	backup_service.py:148 implémente la sauvegarde à la fermeture mais PAS la sauvegarde quotidienne à 18h mentionnée dans la maquette.	Ajouter un scheduler ou vérifier au démarrage si une sauvegarde du jour existe, sinon en créer une.
Moyenne	Import Excel des membres absent	Le cahier des charges §5 exige un import Excel des membres, mais aucun code n'existe.	Implémenter un service d'import dans app/services/import_service.py utilisant openpyxl.
Moyenne	Archive annuelle à la clôture non implémentée	Le cahier exige une archive Excel et PDF à la clôture d'exercice. cloture_service.py ne génère pas ces archives.	Ajouter dans cloture_service.py l'appel à export_service pour générer les archives avant/après la clôture.
Faible	README.md:1	Le README ne contient qu'un mot, aucune documentation d'installation ou d'utilisation.	Rédiger un README complet avec installation, configuration, lancement, et guide d'utilisation.
Faible	scripts/verifier.py:244-251	Utilisation de print() au lieu de logging.	Remplacer les print() par des appels au module logging.
Faible	scripts/generate_icons.py:57	Utilisation de print() au lieu de logging.	Remplacer par logging.
Faible	.gitignore:1-9	.gitignore est minimal mais fonctionnel. Pourrait inclure .spec si utilisé pour PyInstaller.	Ajouter .spec au .gitignore si utilisé.
3. TABLEAU DE CONFORMITÉ
Droits et sécurité
Exigence	Statut	Preuve
Connexion par identifiant et mot de passe chiffré	Fait	app/security/passwords.py:38 (PBKDF2-SHA256, 600k itérations)
Mot de passe haché (bcrypt/argon2, pas MD5/SHA simple)	Fait	passwords.py:12-13 utilise PBKDF2-SHA256 (OWASP recommandé)
Administrateur : comptes, modification, suppression, journal, clôture, paramètres, sauvegardes	Fait	app/security/session.py:31-38 - toutes les permissions définies
Secrétaires : saisie membres, versements, dépenses	Fait	session.py:41-49 - SECRETARY_PERMISSIONS contient ces droits
Secrétaires : ni suppression, ni gestion des comptes	Fait	session.py:41-49 - DELETE et USERS_MANAGE non dans SECRETARY_PERMISSIONS
Correction d'un versement réservée à l'administrateur	Fait	session.py:39 - PAYMENT_EDIT uniquement pour admin
Journal d'audit : qui, quoi, quand	Fait	app/security/audit.py:45-73 - log() enregistre utilisateur, action, objet, détail
Journal d'audit : incluant l'administrateur	Fait	audit.py:61-62 - même log() pour tous les utilisateurs
Journal d'audit : impossible à modifier/effacer	Fait	schema.py:58-63 - triggers RAISE(ABORT) sur UPDATE/DELETE
Contrôle des droits côté logique	Fait	Tous les services appellent session.require() avant les opérations sensibles
Membres
Exigence	Statut	Preuve
N° de carnet unique et non modifiable	Fait	schema.py:68 (UNIQUE), membre_service.py:99 (modification sans numéro)
Nom, sexe, date d'adhésion, statut actif/décédé	Fait	schema.py:66-76, app/models/membre.py:15-22
Nouveau membre cotise à partir de son mois d'adhésion	Fait	app/services/regles.py:17-25 (applicable_months)
Uniquement aux décès postérieurs à son adhésion	Fait	regles.py:28-43 (concerned_by_death)
Cotisation arrêtée pour un membre décédé	Fait	regles.py:25 (end du mois du décès)
Exercice
Exigence	Statut	Preuve
Septembre à août	Fait	app/config.py:17 (FISCAL_YEAR_START_MONTH = 9)
Choix de l'exercice affiché	Fait	app/ui/navigation.py:29-43 (NAV_ITEMS), shell.py:104-112
Clôture irréversible	Fait	cloture_service.py:211-212 (confirmation "CLÔTURER" requise)
Exercice verrouillé en lecture seule après clôture	Fait	schema.py:19 (CHECK statut), cloture_service.py:234
Report automatique des soldes, dettes et avances	Fait	cloture_service.py:122-168 (reports), 230-233 (reports.add)
Cotisation mensuelle
Exigence	Statut	Preuve
Montant selon le sexe (18 000 H / 14 000 F)	Fait	schema.py:24-30 (tarifs_mensuels), exercice_service.py:30-49
Un changement ne touche pas les mois déjà saisis	Fait	deces_service.py:5-6 (montant figé dans la collecte) - même principe applicable
12 colonnes remplies dans l'ordre	Fait	cotisation_mensuelle.py:68-91 (build_statement remplit en ordre)
Dû = montant x mois applicables	Fait	cotisation_mensuelle.py:35-36 (total_due = sum des dues)
Perçu = somme des versements	Fait	cotisation_mensuelle.py:38 (total_paid)
Excédent = avance reportée	Fait	cotisation_mensuelle.py:63-65 (advance = max(credit - total_due, 0))
Manque = dette	Fait	cotisation_mensuelle.py:53-55 (debt = max(total_due - credit, 0))
Cotisation funéraire
Exigence	Statut	Preuve
Une collecte par décès, une colonne par décès	Fait	schema.py:78-94 (table deces)
Types : membre, parent, beau-parent, autre	Fait	schema.py:85 (CHECK type_deces)
Défunt membre passe à « décédé »	Fait	deces_service.py:105-106 (declare_deceased appelé)
Membre endeuillé : cotise, avec option exemption	Fait	schema.py:91 (exempter_endeuille), deces_service.py:79-80
Cases grisées exclues du dû	Fait	cotisation_funeraire.py:90-92 (reason → NON_APPLICABLE)
Versement partiel imputé au décès le plus ancien	Fait	cotisation_funeraire.py:81 (sorted deaths)
Montant selon le sexe (code) vs selon le type (maquette)	Partiel	deces_service.py:3-6 - code privilégie sexe, maquette montre type. Voir section 4.
Autres rubriques
Exigence	Statut	Preuve
Cotisation parallèle : nom, montant par sexe, période	Fait	schema.py:96-107, parallele_service.py
Attendu, perçu et dette par membre	Fait	cotisation_parallele.py, tableau_parallele.py
Amende : membre, nom, libellé, montant, encaissé, manque	Fait	schema.py:126-138, amende_service.py
Dépense : date, libellé, montant, bénéficiaire, montant prévu	Fait	schema.py:141-151, depense_service.py
Si dépensé < prévu : reliquat créé automatiquement	Fait	depense_service.py:86-94 (reliquat calculé et créé)
Reliquat compté en entrée	Fait	bilan_service.py:182 (reliquats dans les entrées)
Bilan : entrées = mensuelle + funéraire + parallèle + reliquats + amendes	Fait	bilan_service.py:31, 174-185
Bilan = entrées - dépenses	Fait	bilan_service.py:114-115 (solde = total_entrees - depenses)
Manque à gagner par rubrique	Fait	bilan_service.py:55-59 (manque = du + dette_reportee - perçu - avance_reportee)
Données, sauvegarde et exports
Exigence	Statut	Preuve
Exports Excel et PDF	Absent	Aucun code d'export trouvé malgré openpyxl et reportlab dans requirements.txt
Liste des membres, cotisations, dettes, journal, reçus	Absent	Non implémenté
Import Excel des membres	Absent	Non implémenté
Sauvegarde automatique à chaque fermeture	Fait	backup_service.py:148-157 (sauvegarder_automatique)
30 copies conservées	Fait	backup_service.py:25 (KEEP_AUTOMATIC = 30), 155
Sauvegarde manuelle	Fait	backup_service.py:136-145 (sauvegarder_manuelle)
Restauration guidée avec sauvegarde de sécurité	Fait	backup_service.py:160-213 (restaurer avec copie securite)
Inscription au journal	Fait	backup_service.py:209-210 (audit.log pour restauration)
Vérification d'intégrité au démarrage	Fait	backup_service.py:74-82 (verifier_integrite) - mais non appelé dans main.py
Archive annuelle Excel et PDF à la clôture	Absent	Non implémenté dans cloture_service.py
Numéro de version du schéma	Fait	schema.py:3-5 (PRAGMA user_version), 285 (LATEST_VERSION)
Interface
Exigence	Statut	Preuve
Menu complet (13 entrées)	Fait	navigation.py:29-43 (NAV_ITEMS avec 13 pages)
Écran de connexion	Fait	login.py (LoginView)
Fiche membre	Partiel	PlaceholderPage pour MEMBERS - écran non implémenté
Formulaires d'ajout/modification	Absent	Seuls placeholders existent
Fenêtres de confirmation (clôture, restauration, décès)	Absent	Non implémenté dans l'UI
États vides et erreurs	Partiel	Banner dans login.py mais pas de gestion générale des erreurs
Notifications de succès	Partiel	Toast existe (banner.py) mais peu utilisé
Profil et changement de mot de passe	Absent	shell.py:161 bouton présent mais non connecté
Légende des couleurs (dette rouge, avance verte)	Fait	labels.py (SituationLabel) implémente les couleurs
Ligne grisée pour décédé	Fait	cotisation_funeraire.py:90-92 (NON_APPLICABLE gris)
4. ÉCARTS CAHIER DES CHARGES / MAQUETTE
4.1 Cotisation funéraire - Montant selon sexe vs type
Cahier des charges : montant selon le sexe
Maquette : montre des montants différents par type de décès
Code actuel : deces_service.py:3-6 implémente "selon le sexe uniquement"
Analyse : Le code suit le cahier des charges mais s'écarte de la maquette. Commentaire explicite dans deces_service.py:3-6 signale ce choix.
4.2 Sauvegarde automatique
Cahier des charges : à chaque fermeture
Maquette : quotidienne à 18:00
Code actuel : implémente uniquement la sauvegarde à la fermeture
Analyse : Manque la sauvegarde quotidienne programmée de la maquette.
4.3 Interface - Écrans non implémentés
La plupart des écrans de la maquette sont des placeholders (PlaceholderPage) :

Membres (gestion complète)
Cotisations mensuelles (tableau interactif)
Cotisations funéraires (tableau interactif)
Cotisations parallèles
Amendes
Dépenses
Reliquats
Bilan financier
Rapports et exports
Sauvegardes
Journal d'audit
Paramètres
Seuls sont fonctionnels :

Connexion (login)
Tableau de bord (avec données fictives MockDashboard)
4.4 Fonctionnalités UI manquantes
Dialogues de confirmation (clôture, restauration, décès)
Formulaires d'ajout/modification
Changement de mot de passe
Gestion des comptes utilisateurs
Paramètres des tarifs
État vide des listes
Gestion centralisée des erreurs
5. 5 ACTIONS PRIORITAIRES
Connecter l'interface à la logique métier (CRITIQUE)
Créer app/ui/adapters/ avec AuthAdapter et DashboardAdapter
Remplacer MockAuth et MockDashboard dans main_window.py
Permettre à l'application de fonctionner réellement
Implémenter les exports Excel et PDF (CRITIQUE)
Créer app/services/export_service.py
Implémenter les exports exigés : bilan, membres, cotisations mensuelles, funéraires, dettes, journal, reçus
Intégrer dans l'écran "Rapports et exports"
Implémenter les écrans principaux de l'interface (ÉLEVÉE)
Remplacer les PlaceholderPage par des vues réelles
Commencer par : Membres, Cotisations mensuelles, Dépenses
Utiliser les services existants (membre_service, versement_service, depense_service)
Ajouter l'import Excel des membres (MOYENNE)
Créer app/services/import_service.py
Utiliser openpyxl pour lire un fichier Excel structuré
Valider les données avant import
Implémenter l'archive annuelle à la clôture (MOYENNE)
Ajouter dans cloture_service.py l'appel à export_service
Générer automatiquement les archives Excel et PDF avant/après la clôture
6. POINTS POSITIFS
Architecture propre et bien structurée
Séparation claire : models, repositories, services, ui
Pattern Repository bien appliqué
Fonctions pures pour les calculs (cotisation_mensuelle.py, cotisation_funeraire.py)
Sécurité robuste
PBKDF2-SHA256 avec 600k itérations (OWASP recommandé)
Protection contre timing attacks (dummy hash)
Blocage après échecs répétés
Journal d'audit en lecture seule (triggers SQL)
Contrôle des permissions côté logique (session.require)
Calculs financiers rigoureux
Utilisation d'entiers (int) pour tous les montants en FCFA
Pas de float - évite les erreurs d'arrondi
Règles de gestion bien testées
Clôture d'exercice avec reports automatiques complexes
Base de données bien conçue
Schéma versionné avec migrations (schema.py)
Clés étrangères activées
Contraintes CHECK pour l'intégrité
Index sur les colonnes fréquentées
Mode WAL pour la robustesse
Tests exhaustifs
27 fichiers de tests couvrant la plupart des services
Tests d'intégration pour le bilan et la clôture
Tests de schéma et de sécurité
Cas limites bien couverts
Code de qualité
PEP 8 respecté
Annotations de type (type hints)
Docstrings présentes
Pas de duplication majeure
Exceptions bien définies et gérées
Transactions bien gérées
Context manager transaction() avec imbrication (SAVEPOINT)
Toutes les écritures dans des transactions
Audit log dans la même transaction
7. POINTS NON VÉRIFIABLES
Performance en conditions réelles
L'application n'est pas connectée à la logique métier
Impossible de tester avec des volumes de données réels
L'interface pourrait bloquer sur des traitements longs (non vérifié)
Packaging PyInstaller
Aucun fichier .spec trouvé
Chemins relatifs non testés en .exe
Impossible de vérifier le comportement empaqueté
Comportement de l'interface utilisateur
MockData ne permet pas de tester les interactions réelles
Flux utilisateur non testable
Navigation entre écrans non fonctionnelle
Sauvegarde quotidienne à 18h
Le code n'existe pas, mais la maquette l'exige
Non implémenté donc non vérifiable
Reçus de paiement
Le cahier exige des reçus
La fonctionnalité n'existe pas (service reglement_service génère un numéro de reçu mais pas le document)
Utilisation réelle sur Windows
L'application n'a pas été testée en conditions d'utilisation
Intégration Windows (ID de l'application, barre des tâches) présente mais non testée en production
Conclusion

Le projet présente une excellente base technique avec une architecture solide, une sécurité robuste et des calculs financiers précis. Le code backend est de haute qualité et bien testé. Cependant, l'interface utilisateur n'est pas connectée à la logique métier et la plupart des fonctionnalités visuelles sont des placeholders. Les exports (Excel/PDF) exigés par le cahier des charges sont absents malgré les dépendances présentes.

L'application est techniquement prête pour la logique métier mais nécessite un travail important sur l'interface et les exports pour être conforme au cahier des charges et utilisable en production.u