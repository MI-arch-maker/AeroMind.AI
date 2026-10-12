"""Briques SITL autonomes d'AeroMind.AI.

Tous les adaptateurs de ce package sont virtuels et n'émettent aucune commande
vers un appareil physique.
"""

from .flight_state import FlightMode, VirtualFlightController
from .mavlink import Heartbeat, SimMessage

__all__ = ["FlightMode", "Heartbeat", "SimMessage", "VirtualFlightController"]
