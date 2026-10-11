# core/__init__.py
"""
AeroMind AI — Noyau central
Référentiel commun : identité, paramètres, machines à états.
"""

from .identity import DeviceIdentity, ProjectIdentity
from .parameters import ParameterRepository, Parameter, ParameterStatus
from .state_machine import DeviceStateMachine, DeviceState, StateTransition