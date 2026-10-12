from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone


class PayloadState(str, Enum):
    OFF = "off"
    READY = "ready"
    ACTIVE = "active"
    FAULT = "fault"


@dataclass
class GimbalStatus:
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    stabilized: bool = True


@dataclass
class VirtualPayload:
    payload_id: str
    kind: str
    state: PayloadState = PayloadState.OFF
    gimbal: GimbalStatus = field(default_factory=GimbalStatus)
    trigger_count: int = 0
    last_trigger_at: datetime | None = None

    def power_on(self) -> None:
        if self.state is PayloadState.FAULT:
            raise RuntimeError("charge utile en défaut")
        self.state = PayloadState.READY

    def trigger(self, event: str = "capture") -> dict[str, object]:
        if self.state is not PayloadState.READY:
            raise RuntimeError("charge utile non prête")
        self.state = PayloadState.ACTIVE
        self.trigger_count += 1
        self.last_trigger_at = datetime.now(timezone.utc)
        return {"payload_id": self.payload_id, "kind": self.kind, "event": event, "sequence": self.trigger_count}

    def stop(self) -> None:
        self.state = PayloadState.READY if self.state is not PayloadState.FAULT else self.state

    def set_gimbal(self, *, roll_deg: float, pitch_deg: float, yaw_deg: float) -> None:
        if any(abs(value) > 180 for value in (roll_deg, pitch_deg, yaw_deg)):
            raise ValueError("angle de nacelle hors plage")
        self.gimbal = GimbalStatus(roll_deg, pitch_deg, yaw_deg, stabilized=True)
