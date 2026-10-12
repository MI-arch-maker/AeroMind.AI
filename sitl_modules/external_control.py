from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio


@dataclass(frozen=True)
class AttitudeCommand:
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    thrust: float

    def validate(self) -> None:
        if not all(-180 <= value <= 180 for value in (self.roll_deg, self.pitch_deg, self.yaw_deg)):
            raise ValueError("attitude hors plage virtuelle")
        if not 0 <= self.thrust <= 1:
            raise ValueError("thrust doit être compris entre 0 et 1")


@dataclass(frozen=True)
class PositionCommand:
    latitude: float
    longitude: float
    altitude_m: float
    frame: str = "local"

    def validate(self) -> None:
        if not -90 <= self.latitude <= 90 or not -180 <= self.longitude <= 180:
            raise ValueError("coordonnées hors plage")
        if self.altitude_m < 0:
            raise ValueError("altitude négative interdite")


@dataclass(frozen=True)
class ExternalCommand:
    command: AttitudeCommand | PositionCommand
    received_at: datetime
    source: str


class MockExternalControl:
    """File d'interconnexion asynchrone : aucune socket ni commande physique."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[ExternalCommand] = asyncio.Queue()

    async def publish_attitude(self, command: AttitudeCommand, source: str = "mock-aircraft") -> None:
        command.validate()
        await self._queue.put(ExternalCommand(command, datetime.now(timezone.utc), source))

    async def publish_position(self, command: PositionCommand, source: str = "mock-aircraft") -> None:
        command.validate()
        await self._queue.put(ExternalCommand(command, datetime.now(timezone.utc), source))

    async def receive(self, timeout_s: float = 1.0) -> ExternalCommand:
        return await asyncio.wait_for(self._queue.get(), timeout=timeout_s)
