import os

os.environ.setdefault('AEROMIND_SESSION_SECRET', 'local-development-secret-with-at-least-32-bytes')
os.environ.setdefault('AEROMIND_ENV', 'development')

from fastapi.testclient import TestClient
from web.app import app
from web.config import Settings
from web.oidc import _b64, _signed

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


def test_superadmin_email_allowlist_is_case_insensitive():
    settings = Settings(
        AEROMIND_SESSION_SECRET='local-development-secret-with-at-least-32-bytes',
        AEROMIND_SUPERADMIN_EMAILS=' Admin@Example.com, second@example.com ',
    )
    assert settings.is_superadmin_email('admin@example.com')
    assert settings.is_superadmin_email('SECOND@EXAMPLE.COM')
    assert not settings.is_superadmin_email('other@example.com')


def test_primary_superadmin_is_configured_by_default():
    settings = Settings(AEROMIND_SESSION_SECRET='local-development-secret-with-at-least-32-bytes')
    assert settings.is_superadmin_email('mcgregoralvin14@gmail.com')


def test_logout_clears_oidc_cookies():
    response = client.post('/api/auth/oidc/logout')
    assert response.status_code == 200
    assert response.json() == {'logged_out': True}
    assert 'aeromind_session=' in response.headers['set-cookie']
    assert 'aeromind_oidc_state=' in response.headers['set-cookie']


def test_superadmin_api_requires_allowlisted_oidc_identity():
    import web.app as app_module

    original = app_module.settings.superadmin_emails
    app_module.settings.superadmin_emails = 'admin@example.com'
    try:
        assert client.get('/api/trpc/superAdmin/accounts').status_code == 401
        regular = _signed(_b64(b'sub-regular|user@example.com'))
        assert client.get('/api/trpc/superAdmin/accounts', cookies={'aeromind_session': regular}).status_code == 403
        admin = _signed(_b64(b'sub-admin|ADMIN@example.com'))
        assert client.get('/api/trpc/superAdmin/accounts', cookies={'aeromind_session': admin}).status_code == 200
    finally:
        app_module.settings.superadmin_emails = original
