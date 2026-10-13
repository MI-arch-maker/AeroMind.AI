# AeroMind Inspect — rapport de refonte et de validation

## Périmètre livré

Le frontend existant a été audité et conservé comme base de production React/Vite/TailwindCSS/Three.js. Il contient déjà les modules demandés :

- **Poste de commandement de vol** : pont de mission, KPIs, télémétrie synthétique/lecture seule, séquence d’exécution et contrôles pré-vol.
- **Observation tactique** : carte SIG locale avec vecteurs, waypoints, zones et journal de mission.
- **Vues caméra** : vue thermique IR synthétique et écran de vision dégradée, explicitement signalés comme données simulées.
- **Analyse ingénieur** : courbes SVG/Recharts de télémétrie et indicateurs énergie, propulsion, structure et environnement.
- **Studio d’assemblage** : modèle physique Three.js/React Three Fiber, composants paramétriques, masse et configuration cumulées.
- **Opérations sécurisées** : checklist, approbation humaine, garde-fous de simulation, validation JWT parallèle côté SITL et impossibilité structurelle de commander du matériel réel.

## Corrections appliquées

1. **Thème cyber sombre par défaut**
   - `ThemeProvider` démarre désormais en mode `dark`, cohérent avec le cockpit industriel et les accents cyan/vert/orange déjà présents dans les styles.

2. **Identités privilégiées hors dépôt**
   - Suppression de l’e-mail Super-Admin par défaut dans `web/config.py` et `.env.example`.
   - `render.yaml` utilise `sync: false` pour `AEROMIND_SUPERADMIN_EMAILS`.
   - La console Super-Admin indique désormais que les identités sont pilotées par la variable d’environnement OIDC.
   - Le test backend associé vérifie qu’aucun Super-Admin n’est créé implicitement.

3. **Déploiement Render / SPA**
   - Le service Web Docker reste le mode recommandé, car il sert simultanément l’API, l’authentification OIDC et les fichiers statiques.
   - `web/app.py` sert les assets compilés, expose `/api/health` et renvoie `index.html` pour toute route non-API : le rafraîchissement des routes SPA ne produit pas de 404.
   - La configuration runtime publique est injectée par `/api/platform/config.js`; aucun secret n’est exposé au bundle frontend.

4. **WebGL sans GPU serveur**
   - Le composant 3D existant utilise `failIfMajorPerformanceCaveat: false`, `powerPreference: low-power`, une limite de contextes actifs, un chargement proche de la zone visible, une ErrorBoundary et un fallback CSS/2D.

## Validation

- `pnpm build:static` : **réussi**.
- `pnpm test -- --run` : **19 fichiers, 95 tests réussis**.
- `python3 -m compileall -q web sitl_modules tests` : **réussi**.
- `pnpm check` : non bloquant mais **échoue sur 81 erreurs TypeScript legacy** dans des types tRPC/Drizzle et quelques inférences `any` de `SuperAdmin.tsx`. Ces erreurs préexistaient à cette passe et n’empêchent pas le build Vite de production.
- `pytest` : non exécuté, le binaire n’est pas installé dans l’environnement de validation.

## Déploiement Render

Le blueprint `render.yaml` est configuré pour un **Web Service Docker** avec :

```text
Build : Dockerfile
Port  : 10000
Health check : /api/health
```

À renseigner dans Render, hors dépôt :

- `AEROMIND_SESSION_SECRET`
- `AEROMIND_SUPERADMIN_EMAILS`
- les variables `ENTRA_*` ou `OIDC_*`
- `OPENAI_API_KEY` si le copilote distant est activé

Ne pas mettre de secrets dans `frontend/client`, `render.yaml` ou les fichiers de démonstration.

## Limite de performance observée

Le build signale un bundle principal d’environ **2,8 Mo minifiés**. Il provient surtout des éditeurs de code, diagrammes et modules HLS présents dans la page principale. Pour une optimisation ultérieure, scinder ces zones par `import()` dynamique et charger les modules lourds uniquement à l’ouverture du panneau concerné.
