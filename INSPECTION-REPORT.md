# Inspection technique — AeroMind AI

## Résultat

Le ZIP contient un projet complet AeroMind AI (API FastAPI + cockpit React/Vite), mais pas un environnement d’exécution prêt à l’emploi. Il faut installer les dépendances Python avant de lancer l’application.

## Vérifications effectuées

- **Serveur local :** démarré avec succès sur le port `10000`.
- **Page d’accueil :** HTTP 200, titre `AeroMind AI — Cockpit d’ingénierie`.
- **API santé :** `GET /api/health` → HTTP 200, `{"status":"ok"}`.
- **Préparation :** `GET /api/ready` → HTTP 200, mode mémoire sûre.
- **Capacités :** SITL activé ; contrôle matériel, téléversement de mission et écriture télémétrique désactivés.
- **Tests :** `11 passed` après ajout de `PYTHONPATH` au contexte local.
- **Visuel :** cockpit React chargé avec succès ; routes principales observées : `/`, `/labbench`, `/admin`, `/super-admin`.

## Pourquoi le ZIP ne fonctionne pas immédiatement

1. `.venv` n’est pas inclus — c’est normal pour un ZIP de code source.
2. Les paquets Python (`httpx`, `pydantic-settings`, etc.) ne sont pas inclus — ils sont listés dans `requirements.txt`.
3. `.env` n’est pas inclus — seul `.env.example` est fourni, ce qui évite de distribuer des secrets.
4. `frontend/node_modules` n’est pas inclus — le projet utilise `frontend/pnpm-lock.yaml` et le Dockerfile réinstalle les dépendances.
5. Le ZIP contient déjà `frontend/dist`, mais le Dockerfile reconstruit aussi le cockpit dans une image propre.
6. Le déploiement Docker définit `PYTHONPATH=/app`; en exécution locale de pytest, il faut parfois fournir `PYTHONPATH=.` explicitement selon le lanceur utilisé.

## Lancement local recommandé

```bash
cd AeroMind.AI-final-integrated
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn web.app:app --host 127.0.0.1 --port 10000 --reload
```

Puis ouvrir : `http://127.0.0.1:10000/`

## URL temporaire de visualisation utilisée

`https://10000-iq886k1bz67h4u98gdej8-fea77b7d.us5.manus.computer/`

Cette URL est temporaire pour la session de visualisation.
