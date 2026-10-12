from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .auth import JwtSettings, validate_tokens_parallel
from .config import DemoCredentials
from .external_control import AttitudeCommand, MockExternalControl, PositionCommand
from .flight_state import FlightMode, FlightStateError, VirtualFlightController
from .hal import RawRcInput, VirtualHal
from .payload import PayloadState, VirtualPayload

router = APIRouter(prefix="/api/sitl", tags=["SITL"])
controller = VirtualFlightController(safety_switch=False)
external_control = MockExternalControl()
hal = VirtualHal()
payloads = {
    "rgb-camera": VirtualPayload("rgb-camera", "rgb-camera"),
    "gimbal": VirtualPayload("gimbal", "stabilized-gimbal"),
}


class ArmRequest(BaseModel):
    demo_only: bool = Field(default=True, description="Doit rester vrai pour le banc virtuel")


class ModeRequest(BaseModel):
    mode: Literal["Manual", "Guided", "Auto"]


class AttitudeRequest(BaseModel):
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    thrust: float
    source: str = "api-mock"


class PositionRequest(BaseModel):
    latitude: float
    longitude: float
    altitude_m: float
    frame: str = "local"
    source: str = "api-mock"


class RcRequest(BaseModel):
    roll: int = 1500
    pitch: int = 1500
    yaw: int = 1500
    throttle: int = 1000


class JwtBatchRequest(BaseModel):
    tokens: list[str] = Field(min_length=1, max_length=128)


def _state() -> dict:
    return {
        "armed": controller.armed,
        "mode": controller.mode.value,
        "altitude_m": controller.altitude_m,
        "safety_switch": controller.safety_switch,
        "event_log": controller.event_log[-20:],
        "hardware_control": False,
        "transport": "in-memory-sitl",
    }


@router.get("/status")
def sitl_status() -> dict:
    return {
        "enabled": True,
        "environment": "SITL",
        "hardware_control": False,
        "modules": ["mavlink-like", "flight-fsm", "external-control-mock", "payload", "hal", "jwt-parallel", "openfoam-runner"],
        "flight": _state(),
        "payloads": {key: {"id": value.payload_id, "kind": value.kind, "state": value.state.value, "trigger_count": value.trigger_count} for key, value in payloads.items()},
    }


@router.post("/flight/arm")
def arm(request: ArmRequest) -> dict:
    if not request.demo_only:
        raise HTTPException(400, "Le module SITL n'accepte que des scénarios de démonstration")
    try:
        controller.arm()
    except FlightStateError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _state()


@router.post("/flight/disarm")
def disarm() -> dict:
    try:
        controller.disarm()
    except FlightStateError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _state()


@router.post("/flight/mode")
def set_mode(request: ModeRequest) -> dict:
    try:
        controller.set_mode(FlightMode(request.mode))
    except FlightStateError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _state()


@router.post("/flight/takeoff")
def takeoff(altitude_m: float = 10.0) -> dict:
    try:
        controller.takeoff(altitude_m)
    except (FlightStateError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc
    return _state()


@router.post("/flight/land")
def land() -> dict:
    controller.land()
    return _state()


@router.post("/control/attitude")
async def attitude(request: AttitudeRequest) -> dict:
    command = AttitudeCommand(request.roll_deg, request.pitch_deg, request.yaw_deg, request.thrust)
    try:
        await external_control.publish_attitude(command, request.source)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"accepted": True, "kind": "attitude", "hardware_control": False, "command": asdict(command)}


@router.post("/control/position")
async def position(request: PositionRequest) -> dict:
    command = PositionCommand(request.latitude, request.longitude, request.altitude_m, request.frame)
    try:
        await external_control.publish_position(command, request.source)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"accepted": True, "kind": "position", "hardware_control": False, "command": asdict(command)}


@router.post("/hal/rc")
def rc_input(request: RcRequest) -> dict:
    try:
        inputs = hal.read_rc(RawRcInput(request.roll, request.pitch, request.yaw, request.throttle))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"inputs": asdict(inputs), "hardware_control": False}


@router.post("/payload/{payload_id}/power-on")
def payload_power_on(payload_id: str) -> dict:
    payload = payloads.get(payload_id)
    if payload is None:
        raise HTTPException(404, "charge utile inconnue")
    payload.power_on()
    return {"payload_id": payload_id, "state": payload.state.value, "hardware_control": False}


@router.post("/payload/{payload_id}/trigger")
def payload_trigger(payload_id: str, event: str = "capture") -> dict:
    payload = payloads.get(payload_id)
    if payload is None:
        raise HTTPException(404, "charge utile inconnue")
    try:
        result = payload.trigger(event)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"accepted": True, "event": result, "state": payload.state.value, "hardware_control": False}


@router.post("/auth/validate")
async def validate_jwt(request: JwtBatchRequest) -> dict:
    credentials = DemoCredentials.from_env()
    results = await validate_tokens_parallel(request.tokens, JwtSettings(credentials.jwt_secret))
    return {"results": [asdict(result) for result in results], "hardware_control": False}
