# Audit express global — AeroMind AI

**Date :** 13 octobre 2026  
**Verdict :** démarrage vierge confirmé et prévisualisation disponible. Le projet peut servir de **prototype/staging** sur Render avec sa configuration Docker, mais il n’est **pas prêt pour une exploitation multi-utilisateur en production**. La persistance métier serveur et plusieurs mutations API ne sont pas encore implémentées. « 100 % opérationnel » ne serait donc pas une conclusion étayée.

## Sélection automatique d’un drone

**Aucun drone n’est choisi sur un espace vierge.** `blankConcept` initialise les cotes à zéro et `airframe`/`motorCount` à `undefined`; `emptyWorkspace` démarre sans projet ni profil. La lecture du stockage élimine aussi les anciens projets de démonstration. Le catalogue conserve des profils et un ancien objet de démonstration dans le code, mais ce n’est pas le chemin d’initialisation d’un nouvel espace.

Un espace déjà sauvegardé peut toutefois restaurer le projet précédemment sélectionné. C’est la restauration de l’état utilisateur, pas une sélection imposée par AeroMind. Les vues Construction, Inspecteur, Simulation, Essais, Rapports et Studio reçoivent majoritairement la configuration commune du cockpit.

## Boutons et calculs

L’analyse statique recense **284 éléments `<button>`** dans le frontend. Deux n’ont pas de gestionnaire de clic direct, mais ils sont respectivement un déclencheur de menu Radix et une poignée de déplacement pilotée au pointeur. Aucun bouton manifestement nu n’a ainsi été repéré. Cela ne constitue pas un test exhaustif des effets de chaque commande. Certaines fonctions sont volontairement conditionnelles : elles attendent un profil, une session SSO ou un service externe. La commande matérielle réelle est désactivée par conception (`hardware_control: false`, téléversement de mission et écriture de télémétrie désactivés).

**Le LabBench est une exception à la configuration partagée du drone.** Il lit le projet local sélectionné, mais ses paramètres d’essai thermique vivent dans une clé de stockage distincte et il ne reçoit pas la configuration drone par props. Ses données de banc sont synthétiques; cela ne prouve ni liaison à du matériel, ni mesure réelle.

## Synchronisation et état réellement opérationnel

Les principales vues partagent l’état React du cockpit et la sauvegarde navigateur utilise `localStorage` et `BroadcastChannel`. Cela permet une continuité dans la session et entre onglets du même navigateur. Ce n’est **pas** une synchronisation serveur ou multi-appareil.

Le backend déclare explicitement `database: not-configured` et `mode: in-memory-safe` dans `/api/ready`. Le pont de compatibilité `/api/trpc` renvoie des listes vides pour projets, runs, versions et rapports, et `null` pour les mutations métier non implémentées. Le frontend tente aussi une sauvegarde sur `/api/local/workspace`, route qui n’existe pas dans `web/app.py`; l’échec est absorbé et le brouillon navigateur reste la seule sauvegarde. Les comptes et événements d’administration sont écrits en JSON sous `data/`, sans disque persistant défini dans `render.yaml`.

J’ai ajouté une garde à la création de projet : si l’API répond `null` ou un objet incomplet, l’interface ne plante plus et conserve un brouillon local avec un avertissement. **Cela améliore le comportement dégradé, mais ne crée pas de persistance serveur.**

## Déploiement Render / autre hébergeur

Le dépôt possède un `Dockerfile`, un `entrypoint.sh` FastAPI et un `render.yaml`. Le conteneur écoute sur `PORT` (10000 par défaut) et le health check pointe vers `/api/health`. Le plan `0.5c-512mb` est reconnu par la spécification Blueprint Render; `sync: false` demande de fournir les variables secrètes lors de la configuration du Blueprint [1] [2]. Le `.dockerignore` exclut `.env`, les dépendances frontend et les données locales.

Les secrets OIDC/Entra et la liste Super-Admin doivent être fournis dans le service Render. Les URL de redirection, `AEROMIND_ALLOWED_ORIGINS` et les hôtes autorisés doivent correspondre au domaine effectivement déployé. La clé LLM est facultative; sans elle, le code prévoit un mode local à règles. L’auto-déploiement est désactivé dans le manifeste, donc un déclenchement manuel est attendu.

**Ne pas déployer avec le runtime Node générique** en utilisant la commande `start` de `frontend/package.json` : elle vise `dist/index.js`, fichier absent après le build Vite. La voie définie par le projet est Docker, qui compile le frontend puis le sert avec FastAPI. La route de santé répond OK même si la base est absente; elle ne valide donc pas la disponibilité des fonctions métier.

## Corrections faites pendant l’audit

- Suppression d’une identité Super-Admin codée en valeur de repli dans `web/config.py`; aucune identité privilégiée n’est désormais admise sans configuration explicite.
- Remplacement de l’adresse préremplie dans `.env.example` par une valeur vide.
- Ajout du garde-fou contre une réponse API de création de projet nulle ou incomplète.
- Mise à jour de trois attentes de tests obsolètes : le catalogue contient actuellement 60 profils, 27 profils « fixed-wing » et 21 morphologies distinctes.

Le `.env` local n’a pas été lu et n’est pas inclus dans l’archive livrable. Aucun déploiement ni configuration de compte Render n’a été effectué.

## Vérifications exécutées

- **TypeScript :** `pnpm run check` réussi.
- **Frontend :** build Vite réussi.
- **Tests frontend :** **21 fichiers et 116 tests réussis** après actualisation des assertions de comptage obsolètes.
- **Python :** compilation syntaxique (`compileall`) réussie.
- **Prévisualisation statique :** page d’accueil et `/manus-routes.json` répondent HTTP 200. Cette prévisualisation sert le frontend statique; elle ne valide pas l’API FastAPI.
- **Non vérifié :** les tests API Python n’ont pas pu être lancés dans cet environnement : `pytest`, `pydantic-settings` et `PyJWT` manquaient; l’installation de dépendances s’est interrompue sur une vérification de hash. La commande Docker n’est pas disponible ici; le build complet du conteneur Render n’a donc pas été exécuté.

## Pour déclarer la production prête

1. Implémenter et tester une base de données pour les projets, versions, simulations, rapports et journaux, puis relier chaque mutation à cette persistance.
2. Choisir explicitement le stockage durable des comptes; ne pas compter sur le système de fichiers éphémère du conteneur.
3. Configurer et tester OIDC sur le vrai domaine, fournir l’adresse Super-Admin autorisée, puis vérifier les parcours authentifiés.
4. Exécuter les tests API dans un environnement de dépendances vérifié, construire l’image Docker et tester `/api/ready` avec les services réellement configurés.
5. Ajouter des tests de bout en bout pour les parcours principaux et vérifier les contraintes d’usage du LabBench et des états locaux.

**Sources Render consultées :**

[1]: https://render.com/docs/blueprint-spec "Blueprint YAML Reference – Render Docs"
[2]: https://render.com/docs/infrastructure-as-code "Render Blueprints (IaC) – Render Docs"
