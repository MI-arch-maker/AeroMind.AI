# AeroMind AI — Python secure API

Le noyau Python original est conservé dans les packages `core`, `hardware`, `safety`, `simulation`, `testing`, `maintenance`, `security`, `control` et `ai_copilot`. Les fichiers mal nommés du ZIP d’origine ont été restructurés en packages Python importables.

## Lancement local

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# définir AEROMIND_SESSION_SECRET avec au moins 32 octets
uvicorn web.app:app --host 127.0.0.1 --port 10000 --reload
```

API : `GET /api/health`, `GET /api/ready`, `GET /api/capabilities`, `GET /api/system/status`, `GET /api/safety/check`.

Le noyau CLI reste disponible avec `python main.py`. L’interface HTTP est le point d’entrée Render : `web.app:app`.

## Render

Le dépôt contient `Dockerfile` et `render.yaml`. Dans Render : **New → Blueprint**, connecter le dépôt et déployer. Le service écoute sur `0.0.0.0:${PORT}` et le health check est `/api/health`.

Variables secrètes à saisir uniquement dans Render :

```text
AEROMIND_SESSION_SECRET
ENTRA_TENANT_ID
ENTRA_CLIENT_ID
ENTRA_CLIENT_SECRET
ENTRA_REDIRECT_URI
```

L’URI Entra doit être `https://<domaine>/api/auth/oidc/callback`. Pour un fournisseur OIDC générique, utiliser `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` et `OIDC_REDIRECT_URI` à la place du bloc Entra. Ne pas activer les deux blocs ensemble.

Le copilote utilise OpenAI-compatible si `OPENAI_API_KEY` est configurée, sinon un mode règles local sans appel externe. Les clés ne sont jamais envoyées au navigateur.

## Déploiement Docker générique

```bash
docker build -t aeromind-ai .
docker run --rm -p 10000:10000 --env-file .env aeromind-ai
```

## Validation

```bash
python -m compileall -q .
pytest -q
```

Les contrôles physiques, le téléversement de mission et l’écriture de télémétrie ne sont pas exposés par l’API web. Toute décision d’ingénierie et toute action matérielle exigent une validation humaine indépendante.
