import os

os.environ.setdefault('AEROMIND_SESSION_SECRET', 'local-development-secret-with-at-least-32-bytes')
os.environ.setdefault('AEROMIND_ENV', 'development')

from fastapi.testclient import TestClient
from web.app import app
from web.config import Settings

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


def test_external_urls_are_normalized():
    settings = Settings(
        AEROMIND_SESSION_SECRET='local-development-secret-with-at-least-32-bytes',
        OIDC_ISSUER='login.microsoftonline.com/example/v2.0',
        OIDC_CLIENT_ID='client',
        OIDC_CLIENT_SECRET='secret',
        OIDC_REDIRECT_URI='https://localhost/callback',
        OPENAI_API_BASE='api.openai.com/v1',
    )
    assert settings.oidc['issuer'].startswith('https://')
    assert settings.openai_api_base == 'https://api.openai.com/v1'
