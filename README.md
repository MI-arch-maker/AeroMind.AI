# AeroMind AI

Cockpit drone, API FastAPI, simulations et banc LabBench. Le mode de fonctionnement par défaut est **simulation**; le contrôle matériel réel est désactivé (`HARDWARE_CONTROL=false`).

## Installation locale

Pré-requis : Python 3.11+, Node.js 22 et pnpm 10.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # définir un secret aléatoire d’au moins 32 octets
npm install --global pnpm@10.18.0
cd frontend && pnpm install --frozen-lockfile && pnpm run build && cd ..
alembic upgrade head
uvicorn web.app:app --reload --port 10000
```

Sans `DATABASE_URL`, SQLite est utilisé dans `data/aeromind.db` uniquement pour le développement. Les migrations sont versionnées dans `migrations/` et s’exécutent avec `alembic upgrade head`; le démarrage du conteneur les applique avant Uvicorn.

## Configuration

Variables principales : `DATABASE_URL` (PostgreSQL en production), `AEROMIND_SESSION_SECRET`, `AEROMIND_ENV`, `AEROMIND_ALLOWED_ORIGINS` (liste exacte d’origines séparées par virgule), `AEROMIND_ALLOWED_HOSTS`, les variables `OIDC_*`, `AEROMIND_SUPERADMIN_EMAILS` et, facultativement, `OPENAI_API_KEY`/`OPENAI_API_BASE`/`OPENAI_MODEL`. **Ne jamais committer les secrets.** `HARDWARE_CONTROL` reste à `false` par défaut.

## API métier

API JSON sous `/api`. Les projets, simulations, rapports, sessions LabBench, drones et réglages sont rattachés au sujet OIDC authentifié et filtrés par propriétaire. Routes :

- `GET/POST /api/projects`, `GET/PUT/PATCH/DELETE /api/projects/{id}`
- `GET/PUT /api/projects/{id}/drone`
- `GET/POST /api/projects/{id}/simulations|reports|lab-sessions`, puis `GET/PUT/PATCH/DELETE .../{record_id}`
- `GET/PUT /api/settings`
- `GET /api/health` (application, version, base, mode)

Création de projet crée un drone par défaut lié au projet. Le pont `/api/trpc` est conservé pour les écrans historiques.

## Premier administrateur

Aucune adresse privilégiée n’est codée en dur. L’opérateur valide l’adresse avec `python -m web.create_admin --email admin@exemple.fr`, puis configure cette adresse dans le secret Render `AEROMIND_SUPERADMIN_EMAILS`. Ce flux ne crée pas de compte local et n’accorde aucun rôle à une identité autre que l’utilisateur OIDC correspondant.

## Docker et Render

`docker build -t aeromind . && docker run --env-file .env -p 10000:10000 aeromind`. Le `render.yaml` déclare le service Docker, PostgreSQL et les références de secrets. Vérifier/définir dans Render les origines et hôtes exacts du domaine réel ainsi que les paramètres OIDC et le redirect URI avant déploiement. Le déploiement réel n’est pas exécuté par ce dépôt/agent.

## CI et contrôles

GitHub Actions exécute les migrations sur PostgreSQL éphémère, pytest, les tests et le typage frontend ainsi que le build Docker. Localement : `pytest -q`, puis `cd frontend && pnpm run check && pnpm test -- --run && pnpm run build`.

## Vérification Compose

Avec Docker Engine et Compose v2 : `make verify` construit les images, démarre PostgreSQL/API/frontend, exécute migrations, tests backend et frontend, smoke tests HTTP, puis arrête les services. La procédure de push, CI, Render, SSO et limites hardware figure dans [`RUNBOOK.md`](RUNBOOK.md). Le service ArduPilot facultatif se lance avec `docker compose --profile sitl up -d sitl`.

## Sécurité matérielle

Le module adaptateur `HardwareLink` fournit `MockAutopilot` et `MAVLinkLink`; il n’est chargé qu’après activation serveur du feature flag. `HARDWARE_CONTROL=false` par défaut. Même flag actif, le passage au matériel exige deux confirmations distinctes, une geofence serveur configurée, une liaison MAVLink et une confirmation explicite par session. Arrêt d’urgence purge la file et demande le désarmement. Le SITL reste virtuel; le code n’est pas une certification de sécurité ni une preuve de fonctionnement d’un E-stop matériel. Ne pas activer sur un aéronef sans revue/autorisation d’ingénierie indépendante et essais en site contrôlé.
