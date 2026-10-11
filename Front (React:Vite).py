┌─────────────────────────────────────────────────────────┐
│  Front (React/Vite)                                     │
│  - Dashboard flotte / vols / audit                      │
│  - Visualisation CFD (VTK.js ou ParaView Glance)        │
│  - Workflow certification (signature + vérification)    │
└──────────────────────┬──────────────────────────────────┘
                       │ REST + WebSocket
┌──────────────────────▼──────────────────────────────────┐
│  Backend FastAPI (Python)                               │
│  ├── auth/          rôles : viewer→operator→admin→super │
│  ├── audit/         journal append-only chaîné (hash)   │
│  ├── flightops/     dossiers de vol, checklists,        │
│  │                  autorisations internes 2-persones   │
│  ├── payload/       charge utile CIVILE, gouvernance    │
│  ├── cfd/           runner OpenFOAM (container Docker)  │
│  ├── propulsion/    élec / H2 / thermique (dimensionnement)
│  ├── cert/          certification interne signée Ed25519│
│  └── vitualhangar/  pont MAVLink ↔ SITL ArduPilot       │
└───────┬──────────────┬──────────────┬───────────────────┘
        │              │              │
   PostgreSQL       Redis         Docker (openfoam/
   (état, audit)   (files, ws)   sitl containers)