AeroMind.AI/
├── render.yaml  Dockerfile  Dockerfile.openfoam  .dockerignore  .gitignore
├── README.md  requirements.txt
├── backend/
│   ├── __init__.py            (vide)
│   ├── tests/test_smoke.py
│   └── app/
│       ├── __init__.py        (vide)
│       ├── core.py  auth.py  audit.py  main.py
│       ├── flightops.py       ← MODULE 1
│       ├── cfd_panel.py  cfd_openfoam.py  cfd_api.py   ← MODULE 2
│       ├── bench_sim.py  bench_mavlink.py  bench_api.py ← MODULE 3
│       ├── propulsion.py      ← MODULE 4
│       └── cert.py  payload.py
└── frontend/
    ├── package.json  vite.config.js  index.html
    └── src/  main.jsx  App.jsx  api.js  ui.jsx
        └── views/  FlightOps.jsx  Cfd.jsx  Bench.jsx  Propulsion.jsx  Audit.jsx  Users.jsx