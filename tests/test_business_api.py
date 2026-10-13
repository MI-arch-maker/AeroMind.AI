import os

os.environ.setdefault("AEROMIND_SESSION_SECRET", "local-development-secret-with-at-least-32-bytes")
os.environ.setdefault("AEROMIND_ENV", "development")
from fastapi.testclient import TestClient

from web.app import app
from web.database import Base, engine
from web.oidc import _b64, _signed

Base.metadata.create_all(engine)
client = TestClient(app, base_url="http://localhost")


def session(sub="business-user", email="business@example.com"):
    return {"aeromind_session": _signed(_b64(f"{sub}|{email}".encode()))}


def test_project_crud_default_drone_and_owner_scope():
    auth = session()
    created = client.post(
        "/api/projects",
        cookies=auth,
        json={"name": "Projet test", "data": {"mission": "inspection"}},
    )
    assert created.status_code == 201
    project = created.json()
    assert project["active_drone_id"]
    assert client.get("/api/projects", cookies=auth).json()[0]["id"] == project["id"]
    assert (
        client.get(f"/api/projects/{project['id']}/drone", cookies=auth).json()["config"][
            "motor_count"
        ]
        == 4
    )
    assert (
        client.get(f"/api/projects/{project['id']}", cookies=session("someone-else")).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/projects/{project['id']}",
            cookies=auth,
            json={"name": "Renommé", "data": {"mission": "mapping"}},
        ).json()["name"]
        == "Renommé"
    )
    assert client.delete(f"/api/projects/{project['id']}", cookies=auth).status_code == 204
    assert client.get(f"/api/projects/{project['id']}", cookies=auth).status_code == 404


def test_child_resource_crud_and_validation():
    auth = session("child-user")
    project = client.post("/api/projects", cookies=auth, json={"name": "P"}).json()
    pid = project["id"]
    for resource in ("simulations", "reports", "lab-sessions"):
        created = client.post(
            f"/api/projects/{pid}/{resource}", cookies=auth, json={"data": {"value": 1}}
        )
        assert created.status_code == 201
        item = created.json()
        assert (
            client.get(f"/api/projects/{pid}/{resource}", cookies=auth).json()[0]["id"]
            == item["id"]
        )
        assert (
            client.get(f"/api/projects/{pid}/{resource}/{item['id']}", cookies=auth).status_code
            == 200
        )
        assert (
            client.patch(
                f"/api/projects/{pid}/{resource}/{item['id']}",
                cookies=auth,
                json={"data": {"value": 2}},
            ).status_code
            == 200
        )
        assert (
            client.delete(f"/api/projects/{pid}/{resource}/{item['id']}", cookies=auth).status_code
            == 204
        )
        assert (
            client.delete(f"/api/projects/{pid}/{resource}/missing", cookies=auth).status_code
            == 404
        )


def test_validation_auth_and_settings_persistence():
    assert client.post("/api/projects", json={"name": "bad", "unknown": 1}).status_code == 422
    assert client.get("/api/projects").status_code == 401
    auth = session("settings-user")
    assert (
        client.put(
            "/api/settings", cookies=auth, json={"key": "theme", "value": "dark"}
        ).status_code
        == 200
    )
    assert client.get("/api/settings", cookies=auth).json()["theme"] == "dark"


def test_health_reports_database_and_simulation_mode():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["version"] and response.json()["database"] == "connected"
    assert response.json()["mode"] == "simulation"
