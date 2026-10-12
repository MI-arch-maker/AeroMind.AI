# Analyse d’intégration Python — archive Aeromind-AI

## Résultat

L’archive finale contenait une seconde pile backend, distincte de l’application `web/` actuelle. Les modules communs (`main.py`, `web/app.py`, `web/config.py`, `web/oidc.py`, `web/admin.py`, `security/`, `hardware/`, `simulation/`) étaient identiques à la version de travail.

Les fichiers supplémentaires utilisaient des noms contenant des deux-points (`backend:app:...`, `app:...`) et n’étaient pas importables comme une package Python normale sans réorganisation.

## Fonctions intégrées

Les capacités compatibles ont été adaptées dans `web/engineering_extensions.py` et branchées dans `web/app.py` sous `/api/engineering` :

- estimation CFD 2D NACA en lecture seule ;
- comparaison énergétique préliminaire LiPo / Li-ion ;
- génération d’une preuve interne signée Ed25519 ;
- authentification par cookie OIDC ;
- déclaration explicite des limites et de l’absence de contrôle matériel.

Routes ajoutées :

- `POST /api/engineering/cfd/airfoil`
- `POST /api/engineering/propulsion/compare`
- `POST /api/engineering/evidence/certificate`

Ces routes ne commandent pas de matériel et ne chargent aucune mission.

## Fonctions volontairement non branchées

Les modules suivants n’ont pas été intégrés comme routes opérationnelles :

- `backend:app:bench_api.py` et `backend:app:bench_mavlink.py` : armement, contrôle de modes et passerelle MAVLink ;
- `app:virtualhangar:mavlink_bridge.py` : communication MAVLink ;
- `backend:app:payload.py` et `app:payload:governed_release.py` : libération de charge utile ;
- `app:cfd:openfoam_runner.py` : exécution Docker directe, non adaptée au worker isolé actuel ;
- `backend:app:auth.py` et `backend:app:core.py` : authentification JWT parallèle avec secret par défaut et comptes/mots de passe de démonstration codés en dur ;
- `backend:app:flightops.py` : seconde gestion d’autorisation et de zones, incompatible avec la session OIDC et les routes actuelles.

Les informations utiles de ces modules restent prises en compte dans l’architecture actuelle, mais les chemins concurrents ou capables de produire une commande physique sont exclus.

## Validation

- `python3 -m py_compile` : réussi.
- Suite backend : **8 tests réussis**.
- Les extensions exigent une session OIDC.
- La comparaison propulsion renvoie `hardware_control: false`.
