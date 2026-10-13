"""Server-side hardware interlocks, bounded command queue and audit callback."""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event, RLock
from typing import Any

from .control_link import HardwareLink


class SafetyError(ValueError):
    """A requested operation violates a control interlock."""


@dataclass(frozen=True)
class Geofence:
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float

    def contains(self, latitude: float, longitude: float) -> bool:
        return (
            self.min_latitude <= latitude <= self.max_latitude
            and self.min_longitude <= longitude <= self.max_longitude
        )


class HardwareControlService:
    def __init__(
        self,
        link: HardwareLink,
        geofence: Geofence,
        journal: Callable[[str, dict[str, Any], str], None],
    ):
        self.link = link
        self.geofence = geofence
        self.journal = journal
        self.queue: deque[tuple[str, dict[str, Any]]] = deque()
        self.mode = "SIMULATION"
        self._dispatch_lock = RLock()
        self._emergency_requested = Event()

    def select_mode(
        self,
        mode: str,
        first_confirmation: bool,
        second_confirmation: bool,
        address: str = "mock://autopilot",
    ):
        mode = mode.upper()
        if mode not in {"SIMULATION", "HARDWARE"}:
            raise SafetyError("Mode must be SIMULATION or HARDWARE")
        if mode == "HARDWARE" and not (first_confirmation and second_confirmation):
            raise SafetyError("Two distinct confirmations are required")
        if mode == "HARDWARE":
            self.link.connect(address)
            self.link.set_mode("STABILIZE")
            self.journal("set_mode", {"mode": "STABILIZE"}, "sent")
            self._emergency_requested.clear()
        self.mode = mode
        return self.mode

    def arm(self, first_confirmation: bool, second_confirmation: bool):
        if self.mode != "HARDWARE":
            raise SafetyError("Hardware mode is not active")
        if not (first_confirmation and second_confirmation):
            raise SafetyError("Two distinct confirmations are required to arm")
        self.link.arm()
        self.journal("arm", {}, "sent")
        return {"armed": True}

    def enqueue(self, command: str, payload: dict[str, Any]):
        if command not in {"position", "heading"}:
            raise SafetyError("Command not allowed")
        if self._emergency_requested.is_set():
            raise SafetyError(
                "Emergency stop latched; new double-confirmed mode selection required"
            )
        if self.mode != "HARDWARE":
            raise SafetyError("Hardware mode is not active")
        if not self.geofence.contains(
            float(payload.get("latitude", float("nan"))),
            float(payload.get("longitude", float("nan"))),
        ):
            self.journal(command, payload, "rejected_geofence")
            raise SafetyError("Command outside configured geofence")
        with self._dispatch_lock:
            if self._emergency_requested.is_set():
                raise SafetyError("Emergency stop latched; command cancelled")
            self.queue.append((command, payload))
            command, payload = self.queue.popleft()
            result = self.link.send_command(command, payload)
            self.journal(command, payload, "sent")
            return result

    def emergency_disarm(self):
        # Latch before taking the dispatch lock so new queued work is denied immediately.
        self._emergency_requested.set()
        with self._dispatch_lock:
            purged = len(self.queue)
            self.queue.clear()
            self.link.disarm()
            self.journal("emergency_disarm", {"purged": purged}, "sent")
            self.mode = "SIMULATION"
            return {"disarmed": True, "queue_purged": purged, "mode": self.mode}
