"""Hardware link adapters. This module is imported only after the server-side feature gate."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any


class HardwareLink(ABC):
    @abstractmethod
    def connect(self, address: str, timeout: float = 10.0) -> None: ...
    @abstractmethod
    def arm(self) -> None: ...
    @abstractmethod
    def disarm(self) -> None: ...
    @abstractmethod
    def set_mode(self, mode: str) -> None: ...
    @abstractmethod
    def send_command(self, command: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    @abstractmethod
    def telemetry_stream(self) -> Iterator[dict[str, Any]]: ...


class MockAutopilot(HardwareLink):
    """Deterministic in-process autopilot used in tests and simulation only."""

    def __init__(self):
        self.connected = False
        self.armed = False
        self.mode = "STABILIZE"
        self.commands: list[tuple[str, dict[str, Any]]] = []
        self.address = "mock://autopilot"

    def connect(self, address: str = "mock://autopilot", timeout: float = 0) -> None:
        self.address = address
        self.connected = True

    def arm(self) -> None:
        if not self.connected:
            raise RuntimeError("Autopilot not connected")
        self.armed = True

    def disarm(self) -> None:
        self.armed = False
        self.commands.append(("disarm", {}))

    def set_mode(self, mode: str) -> None:
        if not self.connected:
            raise RuntimeError("Autopilot not connected")
        self.mode = mode.upper()
        self.commands.append(("set_mode", {"mode": self.mode}))

    def send_command(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.connected:
            raise RuntimeError("Autopilot not connected")
        self.commands.append((command, dict(payload)))
        return {"accepted": True, "command": command, "simulated": True}

    def telemetry_stream(self) -> Iterator[dict[str, Any]]:
        yield {"armed": self.armed, "mode": self.mode, "source": "MockAutopilot"}


class MAVLinkLink(HardwareLink):
    """pymavlink adapter. Instantiated/connected only behind HARDWARE_CONTROL."""

    def __init__(self):
        self._connection = None

    def connect(self, address: str, timeout: float = 10.0) -> None:
        from pymavlink import mavutil

        self._connection = mavutil.mavlink_connection(address, autoreconnect=True)
        if self._connection.wait_heartbeat(timeout=timeout) is None:
            self._connection = None
            raise TimeoutError("MAVLink heartbeat not received")

    def _link(self):
        if self._connection is None:
            raise RuntimeError("MAVLink link not connected")
        return self._connection

    def arm(self) -> None:
        link = self._link()
        link.arducopter_arm()
        link.motors_armed_wait(timeout=10)

    def disarm(self) -> None:
        link = self._link()
        link.arducopter_disarm()
        link.motors_disarmed_wait(timeout=10)

    def set_mode(self, mode: str) -> None:
        link = self._link()
        available = link.mode_mapping()
        if mode.upper() not in available:
            raise ValueError("Unsupported autopilot mode")
        link.set_mode(available[mode.upper()])

    def send_command(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        from pymavlink import mavutil

        link = self._link()
        target = link.target_system
        comp = link.target_component
        if command == "position":
            link.mav.command_long_send(
                target,
                comp,
                mavutil.mavlink.MAV_CMD_DO_REPOSITION,
                0,
                -1,
                0,
                0,
                float(payload.get("heading_deg", 0)),
                float(payload["latitude"]),
                float(payload["longitude"]),
                float(payload.get("altitude_m", 0)),
            )
        elif command == "heading":
            link.mav.command_long_send(
                target,
                comp,
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                0,
                float(payload["heading_deg"]),
                float(payload.get("speed_deg_s", 10)),
                0,
                0,
                0,
                0,
                0,
            )
        else:
            raise ValueError("Only position and heading commands are permitted")
        return {"accepted": True, "command": command, "target_system": target}

    def telemetry_stream(self) -> Iterator[dict[str, Any]]:
        link = self._link()
        while True:
            message = link.recv_match(
                type=["HEARTBEAT", "GLOBAL_POSITION_INT", "ATTITUDE"], blocking=True, timeout=2
            )
            if message is None:
                continue
            yield {"type": message.get_type(), "fields": message.to_dict()}
