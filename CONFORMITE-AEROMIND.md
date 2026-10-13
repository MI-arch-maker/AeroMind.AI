# AeroMind — Clôture des missions A et B

État du dépôt et contrôles locaux le **13 octobre 2026**. Les statuts distinguent l’exécution observée de ce qui requiert Docker, GitHub ou Render. `HARDWARE_CONTROL` reste réglé sur `false`; aucun vol ni SITL conteneurisé réel n’a été exécuté.

## Tableau des livrables

| Artefact / lot | Statut | Commande exacte / prochaine action |
|---|---|---|
| Lots 1–5 : API, données, CRUD, drone, cockpit/LabBench | **VÉRIFIÉ LOCALEMENT** | `python3 -m pytest -q tests sitl_modules/tests`; `cd frontend && pnpm run check && pnpm test -- --run && pnpm run build` |
| Lot 6 : adaptateur, MockAutopilot, double confirmation, geofence, E-stop, logs | **VÉRIFIÉ LOCALEMENT — simulateur Mock uniquement** | Couvert par `tests/test_hardware_control.py` et les deux nouvelles suites frontend; résultats ci-dessous |
| Migrations fraîches + `hardware_logs` | **VÉRIFIÉ LOCALEMENT** | `DATABASE_URL=sqlite:///... PYTHONPATH=. alembic upgrade head` |
| Dockerfile multi-stage + Compose (api, PostgreSQL, nginx/frontend, test, SITL optionnel) | **YAML vérifié; build non exécuté** | `make verify` — **À EXÉCUTER** sur machine avec Docker/Compose v2 |
| Workflow CI PostgreSQL + lint + tests + build | **YAML vérifié; CI distante non exécutée** | Push vers GitHub puis attendre le workflow Actions vert |
| Blueprint Render, SSO et secrets | **YAML vérifié; déploiement non exécuté** | Créer le Blueprint, renseigner IdP/secrets et déployer selon `RUNBOOK.md` |

## Lot 6 — contrôles implémentés

`hardware/control_link.py` définit l’interface abstraite `HardwareLink` (`connect`, `arm`, `disarm`, `set_mode`, `send_command`, `telemetry_stream`) et ses adaptateurs `MockAutopilot` et `MAVLinkLink` via pymavlink. L’adaptateur physique est importé paresseusement après le contrôle serveur `HARDWARE_CONTROL`; ce flag reste faux par défaut.

`hardware/control_service.py` exige deux confirmations distinctes pour la bascule matérielle et l’armement, valide toute commande `position` ou `heading` contre les limites geofence côté serveur, journalise mode/armement/commandes acceptées et rejets geofence, et vide la file avant le désarmement d’urgence. La table incrémentale `hardware_logs` est isolée par propriétaire; `/api/control/logs` expose le journal de l’utilisateur authentifié. La commande d’urgence est sans confirmation; si la liaison ne confirme pas le désarmement, l’API signale une erreur et le RUNBOOK exige l’E-stop physique indépendant.

Le panneau LabBench rend visibles les deux confirmations et un bouton d’urgence. Le mode hardware n’est jamais activé automatiquement. Ces contrôles logiciels ne constituent pas une certification de vol : l’intégration MAVLink réelle, le geofence correspondant à une zone d’essai réelle, l’autopilote SITL en conteneur et un arrêt matériel indépendant restent à éprouver par une personne habilitée avant toute activation.

## Parcours multi-appareil et LabBench

Le test backend ouvre deux `TestClient` indépendants avec deux cookies distincts du même sujet OIDC; A crée puis configure projet/drone et ajoute une simulation; B, sans état frontend/localStorage, relit depuis l’API le projet, le drone et la simulation persistés. C’est une preuve de persistance serveur et d’isolation par identité, pas un test sur deux navigateurs physiques.

`cockpitLabBenchPropagation.test.ts` est le test frontend nommé et dédié : il vérifie la configuration initiale (drone par défaut), émet un événement de changement cockpit par BroadcastChannel et constate la nouvelle configuration LabBench sans rechargement; un projet restauré sans catalogue/configuration retourne l’état vide géré.

## Sorties de validation réellement observées

```text
$ python3 -m pytest -q tests sitl_modules/tests
27 passed, 47 warnings in 1.99s

$ ruff check web/database.py web/models.py web/business_api.py web/app_auth_helpers.py web/create_admin.py web/hardware_api.py hardware/control_link.py hardware/control_service.py migrations tests/test_business_api.py tests/test_hardware_control.py --ignore B008,BLE001
All checks passed!

$ cd frontend && pnpm run check
> tsc --noEmit
[sans erreur]

$ cd frontend && pnpm test -- --run
Test Files  23 passed (23)
Tests  124 passed (124)

$ cd frontend && pnpm run build
✓ built in 22.36s

$ alembic upgrade head  # base SQLite vierge temporaire
Running upgrade -> 0001_business_records
Running upgrade 0001_business_records -> 0002_hardware_logs
migrated tables: alembic_version, drones, hardware_logs, lab_sessions,
projects, reports, simulations, user_settings, users

$ make verify
FAIL — Docker est requis pour make verify.
make: *** [Makefile:5: verify] Error 1
MAKE_VERIFY_EXIT=2
```

La sortie frontend contient **124 tests réussis** : les **116 tests existants** et **8 nouveaux**. Les 27 tests Python comprennent les tests API/multi-client, les 7 cas matériels exécutés avec `MockAutopilot` et les tests SITL virtuels existants. Aucun des résultats Docker/Compose, GitHub Actions, autopilote ArduPilot conteneurisé ou Render ne peut être revendiqué ici; ils sont livrés avec les commandes d’exécution dans `Makefile` et `RUNBOOK.md`.

Les avertissements Python locaux comprennent la configuration `asyncio_mode` non reconnue par le pytest installé localement, des avertissements de dépréciation Starlette et une clé courte dans un ancien test JWT SITL. Ils n’ont pas fait échouer ces tests. Les dépendances de CI sont installées depuis `requirements.txt`.
