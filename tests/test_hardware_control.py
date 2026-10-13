import os

os.environ.setdefault("AEROMIND_SESSION_SECRET", "local-development-secret-with-at-least-32-bytes")
os.environ.setdefault("AEROMIND_ENV", "development")
import pytest
from fastapi.testclient import TestClient

from hardware.control_link import MockAutopilot
from hardware.control_service import Geofence, HardwareControlService, SafetyError
from web.app import app
from web.oidc import _b64, _signed


def auth(email="pilot@example.com"):
    return {"aeromind_session": _signed(_b64(f"pilot-sub|{email}".encode()))}


def controller():
    link = MockAutopilot()
    events = []
    service = HardwareControlService(
        link,
        Geofence(45, 46, -74, -73),
        lambda command, payload, status: events.append((command, payload, status)),
    )
    return service, link, events


def test_arm_rejected_without_two_distinct_confirmations():
    service, link, _ = controller()
    service.select_mode("HARDWARE", True, True)
    with pytest.raises(SafetyError, match="Two distinct confirmations"):
        service.arm(True, False)
    assert not link.armed
    assert service.arm(True, True) == {"armed": True}


def test_emergency_disarm_needs_no_confirmation_and_purges_queue():
    service, link, events = controller()
    service.select_mode("HARDWARE", True, True)
    service.arm(True, True)
    service.queue.extend(
        [
            ("position", {"latitude": 45.5, "longitude": -73.5}),
            ("heading", {"latitude": 45.5, "longitude": -73.5}),
        ]
    )
    result = service.emergency_disarm()
    assert result == {"disarmed": True, "queue_purged": 2, "mode": "SIMULATION"}
    assert not link.armed and not service.queue
    assert events[-1][0] == "emergency_disarm"
    with pytest.raises(SafetyError, match="Emergency stop latched"):
        service.enqueue("position", {"latitude": 45.5, "longitude": -73.5})


def test_server_geofence_rejects_outside_position_and_heading():
    service, _, events = controller()
    service.select_mode("HARDWARE", True, True)
    with pytest.raises(SafetyError, match="outside configured geofence"):
        service.enqueue("position", {"latitude": 49, "longitude": -73.5})
    with pytest.raises(SafetyError, match="outside configured geofence"):
        service.enqueue("heading", {"latitude": 45.5, "longitude": -80, "heading_deg": 180})
    assert [x[2] for x in events[-2:]] == ["rejected_geofence", "rejected_geofence"]


def test_sent_commands_are_journaled_with_status():
    service, link, events = controller()
    service.select_mode("HARDWARE", True, True)
    result = service.enqueue("position", {"latitude": 45.5, "longitude": -73.5, "altitude_m": 10})
    assert result["accepted"] and link.commands[-1][0] == "position"
    assert events[-1] == (
        "position",
        {"latitude": 45.5, "longitude": -73.5, "altitude_m": 10},
        "sent",
    )


def test_flag_off_routes_never_construct_or_call_hardware_adapter(monkeypatch):
    import web.hardware_api as api

    calls = []
    monkeypatch.setenv("HARDWARE_CONTROL", "false")
    monkeypatch.setattr(api, "_get_controller", lambda *_: calls.append("called"))
    client = TestClient(app, base_url="http://localhost")
    response = client.post(
        "/api/control/mode",
        cookies=auth(),
        json={"mode": "HARDWARE", "confirm_operator": True, "confirm_safety": True},
    )
    arm = client.post(
        "/api/control/arm",
        cookies=auth(),
        json={"mode": "HARDWARE", "confirm_operator": True, "confirm_safety": True},
    )
    emergency = client.post("/api/control/emergency-stop", cookies=auth())
    assert response.status_code == 403 and arm.status_code == 403
    assert emergency.status_code == 200 and emergency.json()["hardware_called"] is False
    assert calls == []


def test_authenticated_clients_restore_project_drone_and_simulations_from_database():
    client_a = TestClient(app, base_url="http://localhost")
    client_b = TestClient(app, base_url="http://localhost")
    cookie_a = auth("owner@example.com")
    cookie_b = auth("OWNER@example.com")
    assert cookie_a != cookie_b
    created = client_a.post(
        "/api/projects",
        cookies=cookie_a,
        json={"name": "Multi-device", "data": {"mission": "mapping"}},
    )
    assert created.status_code == 201
    pid = created.json()["id"]
    cfg = {"airframe": "quadcopter", "motorCount": 8, "massKg": 3.4, "batteryWh": 1800}
    assert (
        client_a.put(f"/api/projects/{pid}/drone", cookies=cookie_a, json={"data": cfg}).status_code
        == 200
    )
    sim = client_a.post(
        f"/api/projects/{pid}/simulations",
        cookies=cookie_a,
        json={"data": {"runId": "SIM-REMOTE", "verdict": "pass"}},
    )
    assert sim.status_code == 201
    remote = client_b.get("/api/projects", cookies=cookie_b)
    restored = next(p for p in remote.json() if p["id"] == pid)
    assert restored["data"]["mission"] == "mapping"
    assert client_b.get(f"/api/projects/{pid}/drone", cookies=cookie_b).json()["config"] == cfg
    assert (
        client_b.get(f"/api/projects/{pid}/simulations", cookies=cookie_b).json()[0]["data"][
            "runId"
        ]
        == "SIM-REMOTE"
    )


def test_hardware_api_persists_commands_in_hardware_logs(monkeypatch):
    import web.hardware_api as api
    from web.database import SessionLocal
    from web.models import HardwareLog

    monkeypatch.setenv("HARDWARE_CONTROL", "true")
    client = TestClient(app, base_url="http://localhost")
    link = MockAutopilot()

    def journal(command, payload, status):
        with SessionLocal() as db:
            db.add(
                HardwareLog(
                    user_id="pilot-sub",
                    command=command,
                    payload_json=__import__("json").dumps(payload),
                    status=status,
                )
            )
            db.commit()

    service = HardwareControlService(link, Geofence(45, 46, -74, -73), journal)
    monkeypatch.setattr(api, "_get_controller", lambda _user: service)
    mode = client.post(
        "/api/control/mode",
        cookies=auth(),
        json={"mode": "HARDWARE", "confirm_operator": True, "confirm_safety": True},
    )
    assert mode.status_code == 200
    sent = client.post(
        "/api/control/command",
        cookies=auth(),
        json={"command": "position", "latitude": 45.5, "longitude": -73.5, "altitude_m": 8},
    )
    assert sent.status_code == 200
    records = client.get("/api/control/logs", cookies=auth()).json()
    assert any(row["command"] == "position" and row["status"] == "sent" for row in records)
