# AeroMind AI — Rapport de livraison : modules dynamiques et immersive

Date : 13 octobre 2026
Périmètre : cinq espaces de l'interface d'ingénierie (`frontend/client/src`)
Statut : implémenté, testé et vérifié dans le navigateur

---

## 1. Synthèse

Les cinq espaces demandés ont été rendus dynamiques et immersifs, sans jamais
simuler une mesure physique ni ouvrir une sortie matérielle :

| Espace | Ce qui est désormais dynamique |
| --- | --- |
| Poste de commande de vol | Flux de vol continu (horizon, télémétrie, graphiques défilants), armement/désarmement virtuel, état global affiché dans la barre supérieure |
| Écran d'observation | Sélecteur de vision **VIS / IR / THERM**, gain réglable, palette radiométrique simulée, points chauds, bruit capteur, ligne de balayage |
| Bibliothèque de drones | Nouvelle catégorie **HALE / MALE** (5 vecteurs d'observation longue portée) avec filtres, indicateurs et fiches techniques complètes |
| Bibliothèque de matériels | Cartes enrichies (glyphe de catégorie, source, statut de vérification) et **visualiseur filaire 3D WebGL** avec repli Canvas 2D |
| Centre aéronautique | Jauge circulaire animée et recalcul en direct de la masse, de la charge et de l'autonomie |
| Opérations sûres | Barre de progression de la séquence d'autorisation JWT et **flux système continu** horodaté |

Contraintes de sûreté respectées partout : aucune commande d'actionneur, aucun
téléversement, aucune télémétrie sortante, aucune donnée présentée comme une
mesure embarquée. Chaque écran rappelle la nature simulée des valeurs.

---

## 2. Détail par module

### 2.1 Poste de commande de vol — flux de simulation continue

- `lib/liveSimulation.ts` : modèle de vol déterministe et pur (aucune horloge
  interne), phases `standby / preflight / cruise`, attitude, cap, altitude,
  vitesse, puissance estimée, vibration, qualité de liaison, température.
  Tampon circulaire borné (180 trames) alimentant les courbes défilantes.
- `components/ArtificialHorizon.tsx` : horizon artificiel animé (échelle de
  tangage, roulis, ruban de cap, cadre actif/inactif).
- `components/TelemetryStripChart.tsx` : graphiques défilants (SVG, sans
  dépendance) avec min/max/dernière valeur.
- Intégration : l'horizon et la télémétrie sont alimentés par le même flux, y
  compris lorsque le poste n'a pas de projet chargé.
- Armement virtuel : `ARMER (SIM)` / `DISARM` dans la console de commande et
  dans la barre supérieure ; l'état est global à l'application.
- **Honnêteté des valeurs** : sans configuration renseignée, aucune décharge de
  batterie n'est simulée (mention « BUDGET ÉNERGIE NON RENSEIGNÉ · AUCUNE
  DÉCHARGE SIMULÉE ») et les cibles de croisière sont signalées comme valeurs
  par défaut du simulateur. En vol, la pente de décharge applique un facteur
  d'accélération de démonstration documenté (`DEMO_TIME_SCALE`).

### 2.2 Écran d'observation — spectre VIS / IR / THERM

- `components/VisionShaderOverlay.tsx` : couches de vision simulées
  (luminance infrarouge, palette radiométrique, plumes de chaleur, points
  chauds, bruit capteur, ligne de balayage), avec en-tête indiquant la nature
  simulée de la palette.
- Barre d'outils : trois boutons de vision + réglage de gain ; les modes ne sont
  accessibles que lorsque le scénario local est armé (le bouton l'explique).
- Journalisation : chaque changement de couche est tracé dans le journal de
  session (« shader simulé, aucune mesure radiométrique »).

### 2.3 Bibliothèque de drones — vecteurs d'observation longue portée

- `lib/longRangeObservation.ts` : catalogue de 5 vecteurs (2 HALE, 3 MALE) avec
  architecture, endurance visée, plafond de référence, envergure, charge
  capteurs, contraintes environnementales, suite de capteurs et points de
  vigilance. Catégorisation explicite « CAPTEURS · NON ARMÉ ».
- Morphologies `HALE` et `MALE` ajoutées aux types de calcul (`lib/aeroEngine.ts`)
  et au catalogue (`lib/droneCatalog.ts`), traitées en voilure fixe par les
  maquettes 3D.
- Interface : filtres TOUS / HALE / MALE avec compteurs, bandeau d'indicateurs
  et fiches techniques complètes, y compris la note de préparation documentaire.

### 2.4 Bibliothèque de matériels — cartes et visualiseur filaire

- Grille de cartes du catalogue unifié (41 références) avec glyphe de catégorie,
  fabricant, masse, badge de source et statut de vérification.
- `components/WireframeViewer.tsx` : volume filaire 3D rotatif WebGL (shaders
  minimalistes, GLSL ES 1.00) avec repli Canvas 2D ; le visualiseur partage le
  budget de contextes graphiques de l'application et remonte un canvas neuf en
  cas de perte de contexte.

### 2.5 Centre aéronautique — recalcul en direct

- `components/AeronauticalCenterView.tsx` réécrit : jauge circulaire animée
  (masse, charge utile, énergie) et recalcul immédiat à chaque changement
  d'équipement.
- `lib/aeronauticalCenter.ts` : puissance déclarée par équipement et calcul de
  charge (`equipmentLoadSummary`), sans valeur inventée lorsque la donnée est
  absente.

### 2.6 Opérations sûres — autorisation et flux continu

- Barre de progression de la séquence d'authentification (6 étapes) : état
  inactif, en cours, refusé si la session n'est pas authentifiée
  (« Séquence interrompue · prérequis manquant »).
- Flux système continu horodaté, alimenté par l'activité réelle de l'interface
  (aucune donnée fabriquée).

---

## 3. Fichiers concernés

Créés :

- `frontend/client/src/lib/liveSimulation.ts` (+ `liveSimulation.test.ts`)
- `frontend/client/src/lib/longRangeObservation.ts` (+ `longRangeObservation.test.ts`)
- `frontend/client/src/components/ArtificialHorizon.tsx`
- `frontend/client/src/components/TelemetryStripChart.tsx`
- `frontend/client/src/components/WireframeViewer.tsx`
- `frontend/client/src/components/VisionShaderOverlay.tsx`
- `frontend/client/src/aeromind-dynamics.css`

Modifiés :

- `frontend/client/src/pages/Home.tsx` (intégration des modules)
- `frontend/client/src/components/AeronauticalCenterView.tsx` (réécrit)
- `frontend/client/src/components/PhysicalDroneModel.tsx` (voilure fixe HALE/MALE,
  légende d'envergure déclarée, utilitaires de contexte graphique exportés)
- `frontend/client/src/lib/aeroEngine.ts`, `droneCatalog.ts`,
  `aircraftControlBoundary.ts`, `aeronauticalCenter.ts` (+ tests associés)
- `frontend/client/src/main.tsx` (feuille de style des modules dynamiques)

---

## 4. Vérifications

| Contrôle | Résultat |
| --- | --- |
| `pnpm test` (frontend) | 116 tests réussis / 21 fichiers |
| `pnpm check` (TypeScript) | aucune erreur |
| `pnpm exec vite build` | build réussi |
| `pytest` (backend Python) | 11 tests réussis |
| Vérification navigateur | Poste de commande, observation (VIS/IR/THERM), bibliothèques drones et matériels, centre aéronautique, opérations sûres |

Points vérifiés en conditions réelles : flux continu à 117 trames sans action
opérateur, horizon suivant le cap (374° puis 014°), couche thermique et
infrarouge visibles et lisibles, budget énergie non renseigné correctement
signalé, refus de la séquence d'autorisation sans session authentifiée.

---

## 5. Exécution

```bash
# Backend (API + interface compilée)
cp .env.example .env
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
PYTHONPATH=. uvicorn web.app:app --host 0.0.0.0 --port 10000

# Frontend (développement ou recompilation)
cd frontend && pnpm install
pnpm dev            # développement
pnpm test           # tests unitaires
pnpm check          # typage
pnpm exec vite build  # sortie dans frontend/dist, servie par l'API
```

---

## 6. Limites assumées

- Les valeurs de vol, la palette radiométrique et les volumes filaires sont des
  **simulations d'interface** : aucune mesure capteur, aucun essai réel.
- Les vecteurs HALE/MALE sont des hypothèses d'avant-projet, sans valeur
  réglementaire ni autorisation de vol.
- Le visualiseur filaire est une représentation géométrique simplifiée, non un
  modèle CAO exploitable pour fabrication.