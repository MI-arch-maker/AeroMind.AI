# requirements.txt
"""
Dépendances AeroMind AI — Architecture 5 couches
"""

# Core
python-dateutil>=2.8.0
pydantic>=2.0.0

# Données et persistance
sqlalchemy>=2.0.0
alembic>=1.12.0

# Communication matérielle (optionnel selon les besoins)
# pyserial>=3.5          # Communication série
# pyusb>=1.2.1           # USB
# python-can>=4.0.0      # CAN bus
# pymodbus>=3.5.0        # Modbus
# asyncua>=1.6.0         # OPC UA

# Interface graphique (optionnel)
# PySide6>=6.5.0         # Interface desktop
# streamlit>=1.28.0      # Interface web locale

# Calcul et simulation
numpy>=1.24.0
scipy>=1.11.0

# Rapports et documentation
reportlab>=4.0.0
matplotlib>=3.7.0

# Tests
pytest>=7.4.0
pytest-asyncio>=0.21.0
coverage>=7.3.0

# Sécurité
cryptography>=41.0.0
keyring>=24.0.0

# Format de données
PyYAML>=6.0.0
toml>=0.10.0