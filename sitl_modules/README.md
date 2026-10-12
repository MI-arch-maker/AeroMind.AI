# AeroMind.AI — modules SITL additifs

Cette arborescence est **isolée** du code fonctionnel existant. Elle fournit des briques de simulation purement logicielle pour un environnement académique/industriel : aucune classe ne pilote un appareil, n’ouvre de port série, ni n’émet de commande physique.

## Architecture

```text
ExternalControl Mock ──┐
Virtual HAL (RC/joystick) ─┼─> FlightController FSM ─> Heartbeat MAVLink-like
Payload Manager ───────────┘             │
                                        └─> audit/event log
JWT Parallel Validator ── protège les flux inter-modules
OpenFOAM Docker Runner ── cas CFD local indépendant
```

| Brique | Fichier | Rôle |
|---|---|---|
| MAVLink abstrait | `mavlink.py` | Framing v1-like, checksum X25, heartbeat |
| Banc de test | `flight_state.py` | Arm/disarm, Manual/Guided/Auto, takeoff/land |
| Contrôles externes | `external_control.py` | File asynchrone de commandes attitude/position |
| Charge utile | `payload.py` | Capteurs virtuels, déclenchement, nacelle |
| HAL | `hal.py` | Mapping RC/joystick vers entrées bornées |
| JWT parallèle | `auth.py` | Validation concurrente avec limite de concurrence |
| Mock credentials | `config.py` + `config/.env.sitl.example` | Configuration locale jetable |
| CFD | `cfd/` | Dockerfile + lancement OpenFOAM |
| Interop C++ | `cpp/sitl_gateway.hpp` | Interfaces C++17 pour adaptation future |

## Démarrage

Depuis la racine du projet :

```bash
python -m pytest sitl_modules/tests -q
PYTHONPATH=. python -m sitl_modules.cfd.run_openfoam ./cases/drone_profile
```

Le codec est volontairement nommé **MAVLink-like** : pour un échange MAVLink réel, intégrer `pymavlink` et ses dialectes officiels, puis conserver cette couche derrière une interface d’adaptation testée.

## Sécurité et limites

- `config/.env.sitl.example` contient uniquement des secrets de démonstration et doit rester dans un environnement local.
- Ne pas réutiliser les valeurs `change-me` pour une API exposée ou un équipement réel.
- L’authentification JWT protège les flux logiciels mais ne constitue pas une autorisation d’action physique.
- Le runner OpenFOAM monte uniquement un répertoire de cas CFD et ne nécessite aucun accès matériel.
