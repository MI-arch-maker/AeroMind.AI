# Manifeste d’intégration SITL — AeroMind.AI

Ces composants sont **intégrés dans AeroMind.AI** sous `sitl_modules/` et exposés par le routeur `sitl_modules/api.py`, enregistré dans `web/app.py`. Ils fonctionnent uniquement en simulation locale et n’envoient aucune commande à un drone physique.

| Exigence | Implémentation | Classe / fonction principale | Endpoint de démonstration |
|---|---|---|---|
| Communication abstraite MAVLink | `mavlink.py` | `SimMessage.encode()`, `SimMessage.decode()`, `Heartbeat` | `GET /api/sitl/status` |
| Arm / Disarm / modes | `flight_state.py` | `VirtualFlightController.arm()`, `.disarm()`, `.set_mode()` ; `FlightMode` | `POST /api/sitl/flight/arm`, `/disarm`, `/mode` |
| Contrôles externes | `external_control.py` | `MockExternalControl`, `AttitudeCommand`, `PositionCommand` | `POST /api/sitl/control/attitude`, `/position` |
| Gestionnaire payload | `payload.py` | `VirtualPayload.power_on()`, `.trigger()`, `.stop()`, `.set_gimbal()` | `POST /api/sitl/payload/{payload_id}/power-on`, `/trigger` |
| Hardware Abstraction Layer | `hal.py` | `VirtualHal.read_rc()`, `.read_joystick()` ; `RawRcInput` | `POST /api/sitl/hal/rc` |

## Fichiers à vérifier

```text
sitl_modules/api.py
sitl_modules/mavlink.py
sitl_modules/flight_state.py
sitl_modules/external_control.py
sitl_modules/payload.py
sitl_modules/hal.py
sitl_modules/auth.py
sitl_modules/config.py
sitl_modules/cfd/Dockerfile
sitl_modules/cpp/sitl_gateway.hpp
web/app.py
```

## Vérification locale

```bash
python3 -m pytest -q sitl_modules/tests tests/test_api.py
```

Le scénario de test vérifie le codec, la machine à états, les commandes externes, le payload, le HAL, la validation JWT et les endpoints FastAPI. La sortie attendue est `16 passed`.

## Limite explicite

Le mot « opérationnel » signifie ici **opérationnel dans le SITL AeroMind.AI**. La frontière de contrôle conserve `hardware_control = false` : aucun armement réel, aucune trame série, aucun actionneur et aucun téléversement de mission ne sont activés.
