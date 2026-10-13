# RUNBOOK — livraison AeroMind

## Statuts dans cette remise

| Artefact / validation | Statut | Commande exacte |
|---|---|---|
| Tests Python API + SITL locaux | VÉRIFIÉ LOCALEMENT | `pytest -q && pytest -q sitl_modules/tests` |
| Tests frontend et typecheck | VÉRIFIÉ LOCALEMENT | `cd frontend && pnpm run check && pnpm test -- --run` |
| Build frontend | VÉRIFIÉ LOCALEMENT | `cd frontend && pnpm run build` |
| Build Docker, Compose, PostgreSQL et smoke HTTP | À EXÉCUTER : make verify | `make verify` |
| Build Docker et tests par GitHub Actions | À EXÉCUTER : push → CI | `git push origin <branche>` |
| Déploiement et SSO réel | À EXÉCUTER : Render | Voir les étapes ci-dessous |
| SITL dans un conteneur | À EXÉCUTER : make verify + profil SITL | `docker compose --profile sitl up -d sitl` puis tester seulement avec `HARDWARE_CONTROL=false` jusqu’à revue formelle |

## 1. Push et CI

```bash
git status --short
git add Dockerfile docker-compose.yml Makefile nginx.conf RUNBOOK.md .github/workflows/ci.yml
git add hardware web migrations tests frontend/client/src

git commit -m "Complete guarded control and verification package"
git push origin <branche>
```

Dans GitHub, ouvrir **Actions**, attendre le workflow CI complet, puis vérifier les étapes Ruff, migrations PostgreSQL, tests Python, typecheck/tests frontend et `docker build`. Statut : **À EXÉCUTER : push → CI**; aucun accès GitHub n’a été exercé depuis cette session.

## 2. Secrets GitHub (si un futur job en dépend)

Dans le dépôt : **Settings → Secrets and variables → Actions → New repository secret**. N’ajouter que les secrets effectivement nécessaires au déploiement; ne pas transmettre de clés par commit ni dans les logs. La CI fournie n’a pas besoin de credentials Render.

## 3. Vérification Docker locale

Pré-requis : Docker Engine avec Compose v2, ports libres `5432`, `8080`, `10000`. Les valeurs de mot de passe dans Compose sont réservées au poste local; les remplacer si ce port est exposé sur un réseau.

```bash
make verify
```

Cette commande build les images, démarre PostgreSQL + API + Nginx/frontend, attend leurs healthchecks, applique les migrations, exécute les tests API/SITL et les 116 tests frontend plus les nouveaux tests, effectue les smoke tests HTTP et arrête les services. Les lignes `PASS/FAIL` identifient chaque contrôle. Si Docker n’est pas installé, la commande s’arrête explicitement avec `FAIL — Docker est requis pour make verify.`

Pour lancer le SITL optionnel séparément :

```bash
docker compose --profile sitl up -d sitl
```

Le service dépend d’une image ArduPilot disponible; l’image peut être remplacée par `SITL_IMAGE`. Le SITL n’autorise pas le mode matériel. N’activer aucun vrai autopilote pour une démonstration publique.

## 4. Blueprint Render

1. Push sur le dépôt GitHub et sélectionner **New → Blueprint** dans Render.
2. Choisir le dépôt/branche et examiner les ressources avant création : service Docker `aeromind-ai` et PostgreSQL.
3. Renseigner les variables `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI`, `AEROMIND_SUPERADMIN_EMAILS`, et éventuellement `OPENAI_API_KEY`, exclusivement dans le panneau Render.
4. Mettre `AEROMIND_ALLOWED_ORIGINS` à l’origine HTTPS exacte effectivement assignée; mettre `AEROMIND_ALLOWED_HOSTS` au hostname exact. Corriger aussi l’URL de redirection enregistrée dans l’IdP OIDC.
5. Maintenir `HARDWARE_CONTROL=false`. Déployer puis attendre le healthcheck.

Statut : **À EXÉCUTER : Render**; aucune ressource Render n’a été modifiée ou déployée par cette session.

## 5. Premier administrateur OIDC

Choisir l’adresse de l’administrateur dans le canal opérationnel de l’organisation, puis valider son format :

```bash
python -m web.create_admin --email admin@votre-domaine.example
```

Configurer exactement cette adresse comme secret/variable protégée `AEROMIND_SUPERADMIN_EMAILS` dans Render, ajouter l’URL de redirection OIDC chez l’IdP, puis se connecter avec l’identité correspondante. Le CLI ne crée pas une identité OIDC et ne stocke aucun mot de passe; le fournisseur SSO demeure l’autorité d’identité. Vérifier que `/api/trpc/superAdmin/accounts` est refusé à tout autre sujet.

## 6. Smoke tests production

```bash
export AEROMIND_URL='https://<hostname-render>'
curl --fail --show-error --silent "$AEROMIND_URL/api/health"
curl --fail --show-error --silent --output /dev/null --write-out '%{http_code}\n' "$AEROMIND_URL/"
```

Vérifier `database: connected`, la version, `mode: simulation`, puis connexion SSO, création/liste/restauration d’un projet authentifié et lectures isolées par propriétaire. Statut : **À EXÉCUTER : Render**.

## 7. Checklist matérielle — ne pas activer automatiquement

Le module adaptateur accepte `MockAutopilot` pour les tests et `MAVLinkLink` pour une liaison pymavlink. Par défaut `HARDWARE_CONTROL=false`; aucune bascule système ne met le drone en mode hardware automatiquement. Avant toute activation manuelle de flag en environnement isolé :

- CI verte et build image signé/identifié;
- `make verify` vert, incluant tests MockAutopilot et scénario cockpit → LabBench;
- autopilote SITL dédié testé, geofence serveur `AEROMIND_GEOFENCE` vérifié avec limites documentées;
- liaison MAVLink maîtrisée sur SITL isolé, jamais sur aéronef en environnement peuplé;
- arrêt d’urgence testé et vérification de l’indépendance du coupe-circuit physique;
- revue par ingénieur habilité, procédures d’essai et autorisation de l’opérateur;
- l’opérateur active explicitement le secret `HARDWARE_CONTROL=true`, démarre en SIMULATION, puis effectue les deux validations distinctes.

L’interface ou les tests logiciels ne constituent ni une certification de vol, ni une preuve de fonctionnement d’un E-stop matériel. Si une condition manque, garder le flag à `false`.
