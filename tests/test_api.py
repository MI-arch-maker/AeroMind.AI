import os

os.environ.setdefault('AEROMIND_SESSION_SECRET', 'local-development-secret-with-at-least-32-bytes')
os.environ.setdefault('AEROMIND_ENV', 'development')

from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app, base_url='http://localhost')


def test_health():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_capabilities_disable_physical_io():
    data = client.get('/api/capabilities').json()
    assert data['hardware_control'] is False
    assert data['mission_upload'] is False
    assert data['telemetry_write'] is False
