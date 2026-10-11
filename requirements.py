"""Référentiel Python historique des dépendances AeroMind.

Le fichier installable pour Render est désormais requirements.txt.
Cette constante conserve les dépendances métier originales sous une forme
Python valide et importable.
"""

DEPENDENCIES = [
    "python-dateutil>=2.8.0",
    "pydantic>=2.0.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "numpy>=1.24.0",
    "scipy>=1.11.0",
    "reportlab>=4.0.0",
    "matplotlib>=3.7.0",
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "coverage>=7.3.0",
    "cryptography>=41.0.0",
    "keyring>=24.0.0",
    "PyYAML>=6.0.0",
    "toml>=0.10.0",
]

OPTIONAL_HARDWARE_DEPENDENCIES = [
    "pyserial>=3.5",
    "pyusb>=1.2.1",
    "python-can>=4.0.0",
    "pymodbus>=3.5.0",
    "asyncua>=1.6.0",
]
