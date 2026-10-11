# AeroMind AI — cockpit React + API Python sécurisée

Le noyau Python métier est conservé dans `core`, `hardware`, `safety`, `simulation`, `testing`, `maintenance`, `security`, `control` et `ai_copilot`. Le cockpit React/Vite d’origine est intégré dans `frontend/` et est servi par FastAPI.

## Lancement local

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn web.app:app --host 127.0.0.1 --port 10000 --reload
```

Pour reconstruire le cockpit :

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm exec vite build --config vite.config.ts
```

L’API sert ensuite `frontend/dist` sur `/`, `/labbench` et `/super-admin`. Les endpoints de santé sont `/api/health`, `/api/ready`, `/api/capabilities`, `/api/system/status` et `/api/safety/check`.

## Render / Docker

Le `Dockerfile` utilise deux étapes : Node construit le cockpit React, puis Python installe FastAPI et sert les fichiers compilés. Render doit utiliser le runtime Docker, `./Dockerfile`, le port `10000` et le health check `/api/health`.

```bash
docker build -t aeromind-ai .
docker run --rm -p 10000:10000 --env-file .env aeromind-ai
```

## Authentification et IA

Microsoft Entra/OIDC utilise PKCE, state, nonce, validation JWKS et cookies signés `HttpOnly`, `Secure`, `SameSite`. La redirection exacte est :

```text
https://aeromind-ai-eu4b.onrender.com/api/auth/oidc/callback
```

Le cockpit peut vérifier la session avec `/api/auth/oidc/me`. Le copilote OpenAI-compatible est optionnel et protégé par session OIDC. Sans clé LLM, le mode règles local reste actif.

Les contrôles physiques, le téléversement de mission et l’écriture de télémétrie ne sont pas exposés par l’API web. Toute action d’ingénierie exige une validation humaine indépendante.
