from __future__ import annotations

from dataclasses import dataclass


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class RawRcInput:
    roll: int = 1500
    pitch: int = 1500
    yaw: int = 1500
    throttle: int = 1000


@dataclass(frozen=True)
class FlightInputs:
    roll: float
    pitch: float
    yaw: float
    throttle: float


class VirtualHal:
    """Convertit une entrée RC normalisée en variables SITL bornées."""

    def __init__(self) -> None:
        self.last_input = FlightInputs(0.0, 0.0, 0.0, 0.0)

    @staticmethod
    def _axis(value: int, *, minimum: int = 1000, center: int = 1500, maximum: int = 2000) -> float:
        if not minimum <= value <= maximum:
            raise ValueError("canal RC hors plage 1000..2000")
        return (value - center) / (center - minimum)

    def read_rc(self, raw: RawRcInput) -> FlightInputs:
        mapped = FlightInputs(
            roll=clamp(self._axis(raw.roll)),
            pitch=clamp(self._axis(raw.pitch)),
            yaw=clamp(self._axis(raw.yaw)),
            throttle=clamp((raw.throttle - 1000) / 1000, 0.0, 1.0),
        )
        self.last_input = mapped
        return mapped

    def read_joystick(self, *, roll: float, pitch: float, yaw: float, throttle: float) -> FlightInputs:
        mapped = FlightInputs(clamp(roll), clamp(pitch), clamp(yaw), clamp(throttle, 0.0, 1.0))
        self.last_input = mapped
        return mapped
