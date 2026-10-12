import asyncio

import jwt
import pytest

from sitl_modules.auth import JwtSettings, validate_tokens_parallel
from sitl_modules.external_control import AttitudeCommand, MockExternalControl
from sitl_modules.flight_state import FlightMode, FlightStateError, VirtualFlightController
from sitl_modules.hal import RawRcInput, VirtualHal
from sitl_modules.mavlink import Heartbeat, SimMessage
from sitl_modules.payload import PayloadState, VirtualPayload


def test_mavlink_like_round_trip_and_heartbeat():
    message = Heartbeat(True, "Guided").to_message(7)
    assert Heartbeat.from_message(SimMessage.decode(message.encode())) == Heartbeat(True, "Guided")


def test_flight_state_requires_safe_arm_sequence():
    controller = VirtualFlightController(safety_switch=False)
    controller.arm()
    controller.set_mode(FlightMode.GUIDED)
    controller.takeoff()
    controller.set_mode(FlightMode.AUTO)
    assert controller.mode is FlightMode.AUTO
    controller.land()
    controller.disarm()
    assert controller.armed is False


def test_external_control_queue_and_payload():
    async def scenario():
        port = MockExternalControl()
        await port.publish_attitude(AttitudeCommand(1, 2, 3, 0.5))
        received = await port.receive()
        assert received.source == "mock-aircraft"
    asyncio.run(scenario())
    payload = VirtualPayload("cam-1", "rgb-camera")
    payload.power_on()
    assert payload.trigger()["sequence"] == 1
    assert payload.state is PayloadState.ACTIVE


def test_hal_rc_mapping():
    inputs = VirtualHal().read_rc(RawRcInput(1000, 2000, 1500, 1750))
    assert inputs == pytest.approx(type(inputs)(-1.0, 1.0, 0.0, 0.75))


def test_parallel_jwt_validation():
    settings = JwtSettings("test-secret")
    valid = jwt.encode({"sub": "demo", "aud": settings.audience, "iss": settings.issuer}, settings.secret, algorithm=settings.algorithm)
    results = asyncio.run(validate_tokens_parallel([valid, "invalid"], settings))
    assert [result.valid for result in results] == [True, False]
