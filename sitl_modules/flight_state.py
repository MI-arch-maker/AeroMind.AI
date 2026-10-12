from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class FlightMode(str, Enum):
    MANUAL = "Manual"
    GUIDED = "Guided"
    AUTO = "Auto"


class FlightStateError(RuntimeError):
    pass


@dataclass
class VirtualFlightController:
    mode: FlightMode = FlightMode.MANUAL
    armed: bool = False
    safety_switch: bool = True
    altitude_m: float = 0.0
    event_log: list[str] = field(default_factory=list)
    _listeners: list[Callable[[str], None]] = field(default_factory=list, repr=False)

    def add_listener(self, listener: Callable[[str], None]) -> None:
        self._listeners.append(listener)

    def _record(self, event: str) -> None:
        self.event_log.append(event)
        for listener in self._listeners:
            listener(event)

    def arm(self) -> None:
        if self.armed:
            return
        if self.safety_switch:
            raise FlightStateError("armement refusé: safety switch actif")
        if self.altitude_m != 0:
            raise FlightStateError("armement refusé: altitude virtuelle non nulle")
        self.armed = True
        self._record("armed")

    def disarm(self) -> None:
        if self.altitude_m > 0:
            raise FlightStateError("désarmement refusé en vol virtuel")
        self.armed = False
        self._record("disarmed")

    def set_mode(self, mode: FlightMode) -> None:
        if not self.armed and mode is not FlightMode.MANUAL:
            raise FlightStateError("mode automatique refusé avant armement")
        if mode is FlightMode.AUTO and self.altitude_m <= 0:
            raise FlightStateError("mode Auto réservé à un vol virtuel engagé")
        self.mode = mode
        self._record(f"mode:{mode.value}")

    def takeoff(self, altitude_m: float = 10.0) -> None:
        if not self.armed:
            raise FlightStateError("décollage refusé: véhicule désarmé")
        if altitude_m <= 0:
            raise ValueError("altitude de décollage positive requise")
        self.altitude_m = altitude_m
        self._record(f"takeoff:{altitude_m:.1f}")

    def land(self) -> None:
        self.altitude_m = 0.0
        self.mode = FlightMode.MANUAL
        self._record("landed")

    def heartbeat(self, sequence: int = 0):
        from .mavlink import Heartbeat
        return Heartbeat(self.armed, self.mode.value).to_message(sequence)
