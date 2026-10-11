# hardware/__init__.py
"""
AeroMind AI — Couche matérielle
Profils, compatibilité, passerelle de communication et connecteurs.
"""

from .profiles import HardwareProfile, SensorProfile, ActuatorProfile, InterfaceProfile
from .compatibility import CompatibilityEngine, CompatibilityResult, CompatibilityIssue
from .gateway import DeviceGateway, GatewayEvent