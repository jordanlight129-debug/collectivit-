CAHIER DES CHARGES
Logiciel de gestion d'association
Cotisations, cotisation funéraire, dépenses et bilan

Élément	Détail
Date	19 octobre 2026
Version	1.0 – proposition
Type de solution	Application Windows installable (.exe), fonctionnement hors ligne
Exercice de gestion	Septembre à août
Devise	Franc CFA (FCFA)
1. Contexte et objectifs
L'association souhaite remplacer la gestion manuelle de ses carnets par un logiciel qui calcule automatiquement les cotisations, les dettes et les avances de chaque membre, suit les dépenses et produit le bilan de chaque exercice.
Objectifs principaux :
•	Enregistrer les membres et leurs versements sans erreur de calcul.
•	Afficher à tout moment, pour chaque membre, le total dû, le total perçu et la dette éventuelle.
•	Suivre séparément chaque rubrique d'entrée et le manque à gagner correspondant.
•	Produire le bilan (entrées moins dépenses) par exercice.
•	Tracer toutes les actions pour garantir la transparence.
•	Conserver les données de manière fiable pendant 10 à 30 ans.
2. Utilisateurs et droits
Profil	Droits
Administrateur (1)	Gère les comptes, modifie et supprime, voit toutes les données et le journal d'audit, clôture les exercices.
Secrétaires (3)	Saisissent les membres, les versements et les dépenses. Ne peuvent ni supprimer, ni gérer les comptes.

Chaque connexion exige un identifiant et un mot de passe chiffré. Le journal d'audit enregistre qui a fait quoi et quand, y compris pour l'administrateur. Il ne peut être ni modifié ni effacé depuis le logiciel.
3. Règles de gestion
3.1 Membres
Chaque membre a un numéro de carnet unique, un nom, un sexe et une date d'adhésion. Son statut est « actif » ou « décédé ». Un nouveau membre cotise à partir de son mois d'adhésion et uniquement aux décès postérieurs à son adhésion.
3.2 Exercice annuel
L'exercice va de septembre à août (exemple : 2026-2027 = septembre 2026 à août 2027). L'utilisateur choisit l'exercice affiché. À la clôture, les soldes, dettes et avances sont reportés automatiquement sur l'exercice suivant.
3.3 Cotisation mensuelle
•	Le montant mensuel est fixé selon le sexe.
•	Chaque versement est enregistré avec sa date et son montant ; les 12 colonnes (septembre à août) se remplissent automatiquement dans l'ordre.
•	Total dû = montant mensuel × nombre de mois applicables. Total perçu = somme des versements.
•	Si le perçu dépasse le dû, l'excédent est reporté sur l'exercice suivant comme avance.
•	Si le perçu est inférieur au dû, la différence est affichée comme dette.
•	Les cotisations d'un membre décédé s'arrêtent.
3.4 Cotisation funéraire
•	Obligatoire pour tous les membres actifs. Chaque décès crée une collecte avec son propre montant, fixé selon le sexe.
•	Types de décès : membre de l'association, parent, beau-parent, autre.
•	Une colonne est ajoutée au tableau pour chaque décès, avec le nom du défunt en en-tête.
•	Le défunt, lorsqu'il est membre, passe au statut « décédé » et ne cotise plus.
•	Le membre endeuillé cotise ; une option permet de l'exempter décès par décès.
•	Les cases des membres non concernés sont grisées et ne comptent pas dans le total dû.
•	Un versement partiel est imputé au décès le plus ancien ; la différence apparaît comme dette.
3.5 Cotisation parallèle
L'administration définit le nom de la cotisation, le montant attendu par sexe et la période. Le logiciel affiche le montant attendu, le montant perçu et la dette de chaque membre.
3.6 Reliquat
Le reliquat est le reste d'une dépense : lorsque la dépense est inférieure à la somme prévue, la différence est enregistrée comme entrée, avec son nom, son montant et la dépense d'origine.
3.7 Amende
Chaque amende comporte le membre concerné, un nom, un libellé et un montant, ainsi qu'un champ de collecte. Le manque à gagner est la part non encaissée.
3.8 Dépenses
Chaque dépense comporte une date, un libellé, un montant et un bénéficiaire. Si le montant dépensé est inférieur au montant prévu, un reliquat est généré.
3.9 Bilan
Entrées = cotisation mensuelle + cotisation funéraire + cotisation parallèle + reliquats + amendes. Bilan = entrées − dépenses. Pour chaque rubrique, le logiciel affiche le manque à gagner (dû − perçu) et le total général.
4. Exigences techniques
Élément	Choix
Plateforme	Windows 10 et 11, installation par un fichier .exe
Langage et interface	Python, interface de bureau
Base de données	SQLite, un fichier unique sur l'ordinateur, sans serveur
Exports	Excel et PDF (listes, dettes, bilan, reçus de paiement)
Sauvegarde	Copie manuelle et automatique, restauration guidée
4.1 Durabilité des données sur 10 à 30 ans
SQLite convient à ce projet. Ses limites techniques sont très largement supérieures aux besoins : une association de plusieurs centaines de membres produit quelques dizaines de milliers de lignes par an, soit quelques dizaines de Mo après 30 ans, alors que SQLite gère des bases de plusieurs centaines de To. Son format de fichier est stable et documenté, le logiciel est du domaine public, et ses auteurs s'engagent à le maintenir sur le long terme.
Le vrai risque sur 30 ans n'est pas SQLite mais la perte du fichier (panne d'ordinateur, vol, virus) et l'évolution de Windows. Les mesures suivantes sont donc prévues :
•	Sauvegarde automatique à chaque fermeture, avec conservation des 30 dernières copies.
•	Copie recommandée sur clé USB ou disque externe, et sur un stockage en ligne.
•	Vérification d'intégrité de la base à chaque démarrage.
•	Archive annuelle à la clôture de l'exercice, au format Excel et PDF, lisible sans le logiciel.
•	Numéro de version de la structure de la base, pour migrer les données lors des mises à jour.
•	Code source et documentation remis à l'association, pour éviter toute dépendance à un seul prestataire.
•	Fichier de données stocké dans un dossier connu, facile à copier.
Si l'association grandit fortement (utilisation simultanée sur plusieurs ordinateurs), une migration vers un serveur de base de données sera possible grâce à la structure conçue dès le départ.
5. Livrables
•	Installateur Windows (.exe) du logiciel.
•	Code source complet et documentation technique.
•	Guide d'utilisation pour l'administrateur et les secrétaires.
•	Formation d'une demi-journée pour l'administrateur et les trois secrétaires.
•	Reprise des données existantes jusqu'à 200 membres (saisie ou import Excel).
6. Planning prévisionnel
Phase	Contenu	Durée
1	Conception, maquettes, validation du cahier des charges	1 semaine
2	Comptes, membres, audit, cotisation mensuelle, funéraire	2 semaines
3	Parallèle, amendes, reliquats, dépenses, bilan	2 semaines
4	Exports, reçus, sauvegarde, installateur, tests	1 semaine
5	Installation, reprise des données, formation	3 jours
Durée totale estimée : environ 6 semaines après validation du cahier des charges.
7. Proposition financière
Les montants ci-dessous sont une proposition indicative en FCFA, à ajuster selon le périmètre final validé.
Poste	Montant (FCFA)
Analyse, conception et maquettes	60 000
Comptes, authentification, journal d'audit, gestion des membres	90 000
Cotisation mensuelle (12 mois, dettes et avances, report d'exercice)	100 000
Cotisation funéraire (décès, membre endeuillé, tableau dynamique)	100 000
Cotisation parallèle, amendes et reliquats	90 000
Dépenses, bilan et manque à gagner	90 000
Exports Excel/PDF et reçus de paiement	70 000
Sauvegarde, restauration et sécurité	40 000
Installateur, tests, reprise des données et formation	60 000
TOTAL	700 000

Modalités de paiement
Étape	Part	Montant (FCFA)
Signature du cahier des charges	40 %	280 000
Livraison de la version de test (phases 2 et 3)	30 %	210 000
Livraison finale et formation	30 %	210 000

Maintenance (optionnelle)
Forfait annuel de 70 000 FCFA : corrections d'anomalies, assistance par téléphone, aide à la clôture de l'exercice, mise à jour pour les nouvelles versions de Windows et vérification des sauvegardes.
Conditions
•	Les modifications de règles de gestion demandées après validation du cahier des charges font l'objet d'un devis complémentaire.
•	Le paiement de la dernière tranche entraîne la remise du code source.
•	La proposition reste valable 30 jours à compter de sa date.
8. Validation
Document lu et approuvé par les deux parties.
Pour l'association	Le prestataire
Nom et fonction : 	Nom :
Date :	Date :
Signature :	Signature :

