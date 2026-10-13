# AeroMind Inspect — architecture interactive 3D et simulation de mission

## Vue d’ensemble

Le front-end est une application **React 19 + TypeScript + Vite**. L’évolution ajoute des visualisations physiques paramétriques, un studio d’assemblage piloté par la nomenclature, un cockpit de mission à plusieurs vues et un banc de charges utiles. Le principe d’architecture est de garder le modèle métier comme source de vérité et de séparer clairement **simulation locale**, **télémétrie entrante en lecture seule** et **commande matérielle réelle**.

### Flux de données

```text
Home.tsx / workspace config
├── MissionOperationsView
│   ├── LocalMissionPlan + MissionEnvironment
│   ├── FlightCommandDeck
│   │   ├── PhysicalDroneModel (Three.js / R3F)
│   │   └── FlightOperationsModules
│   │       ├── graphes — télémétrie synthétique ou WSS entrante fraîche
│   │       ├── carte locale — waypoints + évitement simplifié
│   │       ├── rendu thermique simulé
│   │       ├── journal d’événements structuré
│   │       └── éditeur de scénarios dégradés
│   └── moteur runSimulation / validateLocalMission
├── DesignStudioView
│   ├── PhysicalDroneModel (pièces InstalledMaterial → maillages)
│   ├── inspecteur de pièce (masse, traînée, puissance, bus)
│   └── PayloadMissionWorkbench (calibration et essais virtuels)
└── LabBench / catalogue de pièces existants
```

## Carte des composants livrés

| Fichier | Responsabilité |
|---|---|
| `client/src/components/PhysicalDroneModel.tsx` | Viewport Three.js + React Three Fiber réutilisable, silhouettes paramétriques, matériaux standard éclairés, animation douce, commandes d’orbite et fallback 2D. Limite de quatre Canvas WebGL simultanés et chargement différé près du viewport. |
| `client/src/components/FlightOperationsModules.tsx` | Vues Télémétrie, Carte SIG locale, Thermique IR, Journal et Milieux extrêmes; édition du plan local et recalcul de détour illustratif. |
| `client/src/components/FlightCommandDeck.tsx` | Enveloppe du cockpit, état de mission et appels vers les sous-modules, sans interface de commande réelle. |
| `client/src/components/PayloadMissionWorkbench.tsx` | Catalogue RGB, thermique, LiDAR et module de colis de secours; curseurs de calibration et séquence logicielle locale. |
| `client/src/components/DesignStudioView.tsx` | Vue d’assemblage 3D par défaut, sélection d’une pièce, bascule vers le plan 2D, panneau de configuration et ajout de charges utiles. |
| `client/src/lib/missionBridge.ts` | Parseur strict des trames entrantes en lecture seule (vitesse, altitude, batterie, cap et tangage/roulis optionnels). |
| `client/src/lib/aeroEngine.ts` | Estimation préliminaire de puissance/autonomie utilisant masse, traînée déclarée, puissance auxiliaire et facteurs de scénario. |
| `client/src/lib/droneParts.ts` | Catalogue de pièces, dont le module de colis de secours marqué simulation. |
| `client/src/components/flight-operations.css`, `payload-workbench.css`, `design-studio-physical.css` | Styles tactiques, contrôles responsives, scene 3D et calibration. |

## Cockpit et télémétrie

`FlightOperationsModules` maintient une courte série temporelle de cinq indicateurs : vitesse, altitude, tangage, roulis et batterie. Les valeurs proviennent du modèle de démonstration local par défaut. Quand une trame WSS fraîche est reçue, les champs disponibles dans `MissionTelemetryFrame` alimentent les courbes **en lecture seule**; les mesures non présentes restent explicitement identifiées comme issues du modèle local.

`missionBridge.ts` accepte des alias normalisés et vérifie les bornes numériques pour GPS, batterie, cap et attitude. Les trames ne contiennent aucun canal de commande. Une ancienne trame WSS cesse d’être présentée comme fraîche au bout de 2,5 secondes.

Les vues tactiques utilisent un canevas normalisé, et non un fond SIG géoréférencé. L’obstacle circulaire, la base et les waypoints sont des marqueurs de test locaux. L’algorithme de détour déplace les waypoints qui intersectent cette zone fictive; il ne constitue pas un planificateur de navigation validé.

Le mode IR applique une palette/filtre visuel synthétique à la source affichée. Il ne calcule pas une scène thermique réelle et ne transforme pas des valeurs caméra physiques.

## Assemblage et intégration des charges utiles

Les pièces de `InstalledMaterial[]` sont converties en volumes paramétriques simples par catégorie. Les matériaux du prototype utilisent les propriétés Three.js `MeshStandardMaterial` (métal/roughness) et une texture carbone procédurale. Ces volumes ne sont pas des géométries industrielles, des fichiers STEP ni des modèles fabricants certifiés.

L’inspecteur expose, par pièce : masse, position/échelle selon les contrôles existants, aire de traînée équivalente estimée (`dragAreaM2`), puissance auxiliaire (`powerDrawW`) et bus logique simulé (`connectedTo`). Ces paramètres rejoignent la configuration locale et le moteur d’estimation. Les valeurs initiales pour les composants non documentés sont des **hypothèses ajustables**, pas des données constructeur.

Le banc de charges utiles fournit quatre modules d’interface. L’installation modifie seulement la nomenclature du modèle; l’inclinaison et le champ de vision restent des réglages virtuels de la démonstration. La séquence de colis se termine explicitement sans sortie physique : aucun moteur, servo, largueur ou capteur connecté n’est piloté.

## Scénarios dégradés et autonomie

`MissionEnvironment` expose température ambiante, vent et niveau CEM synthétique. Le calcul d’autonomie tient compte :

- de la puissance auxiliaire et de la traînée déclarées par les pièces;
- d’un terme simplifié pour le vent additionnel;
- d’un facteur de température pour l’énergie utile de batterie;
- d’un facteur heuristique pour température et perturbations CEM.

Ces coefficients sont de niveau maquette et ne sont **ni calibrés ni qualifiés**. Le cockpit les présente comme des hypothèses de simulation, jamais comme une marge de vol ou une certification réglementaire.

## Compatibilité WebGL et réduction de charge

Le renderer est créé uniquement si WebGL 2 passe une sonde, qui libère immédiatement son contexte temporaire. Three.js r163+ ne prenant plus en charge WebGL 1, la stratégie retenue est un fallback DOM/CSS 2D au lieu d’une fausse tentative de repli. Le constructeur R3F fixe `powerPreference: "low-power"`, `failIfMajorPerformanceCaveat: false`, `precision: "mediump"`, antialiasing désactivé et DPR limité.

Un Error Boundary intercepte l’échec à la création du Canvas. Les vues hors écran sont suspendues et un pool plafonne le nombre de Canvas pour éviter les limites de contexte GPU des navigateurs. La silhouette alternative annonce clairement le motif du fallback.

## Garde-fous de commande

- Les boutons du cockpit manipulent exclusivement l’état virtuel local.
- Le WSS entrant est un canal de lecture seule; le parseur rejette le JSON mal formé et n’expose aucun ordre sortant.
- Aucun armement, actionneur, téléversement de mission, commande de vol réelle ou largage physique n’est ajouté.
- Toute sortie du mode simulation doit passer par une architecture distincte, une revue de sécurité et les systèmes de commande déjà protégés par `aircraftControlBoundary.ts`.

## Vérifications exécutées

- `pnpm build:static` : réussite; avertissement Vite déjà pertinent sur la taille du bundle principal (> 500 kB).
- `pnpm test` : **95 tests réussis** sur 19 fichiers, dont tests de calcul sous environnement dégradé et parsing attitude.
- `pnpm check` : échoue sur des erreurs TypeScript préexistantes dans plusieurs fichiers non concernés (`Home.tsx` à d’autres lignes, `LabBenchPersistencePanel.tsx`, `SuperAdmin.tsx`, `shared/types.ts`, hooks et `main.tsx`). Aucun diagnostic TypeScript n’est signalé dans les nouveaux modules ni dans les lignes d’intégration ciblées.

## Limites et suite recommandée

Le rendu 3D est une maquette WebGL paramétrique : il permet de choisir des pièces et de tester l’interface, mais ne remplace pas un éditeur CAO, un solveur aérodynamique, une géométrie fabricant, un banc HIL, une carte SIG ou une télémétrie certifiée. Pour une mise en production d’ingénierie, intégrer des maillages fournisseurs vérifiés, calibrer chaque coefficient à partir de données mesurées, ajouter des tests de géométrie/accessibilité/performance GPU faible et qualifier indépendamment tout planificateur de route.
