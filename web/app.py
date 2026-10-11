import base64
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import get_settings
from .copilot import router as copilot_router
from .oidc import _verified, router as oidc_router


def _engine_status():
    try:
        from main import AeroMindAI
        engine = AeroMindAI()
        return {'loaded': True, 'profiles': len(engine.compatibility_engine._known_profiles), 'safety': engine.run_safety_check()}
    except Exception as exc:
        return {'loaded': False, 'error': type(exc).__name__}


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Path('data').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)
    yield


settings = get_settings()
app = FastAPI(title='AeroMind AI API', version='2.0.0', docs_url='/docs' if settings.environment != 'production' else None, redoc_url=None, lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hosts)
if settings.origins:
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True, allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type', 'X-Request-ID'])

FRONTEND_DIR = Path('frontend/dist')
FRONTEND_INDEX = FRONTEND_DIR / 'index.html'
if FRONTEND_DIR.is_dir():
    app.mount('/assets', StaticFiles(directory=FRONTEND_DIR / 'assets'), name='frontend-assets')

app.include_router(oidc_router)
app.include_router(copilot_router)


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    if settings.environment == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.get('/api/platform/config.js', include_in_schema=False)
def platform_config():
    """Public, non-secret runtime configuration consumed by the React cockpit."""
    oidc_enabled = bool(settings.oidc)
    provider = 'Microsoft Entra ID' if oidc_enabled else ''
    script = (
        'window.__MANUS_CONFIG__ = '
        + __import__('json').dumps({
            'projectId': 'aeromind-ai',
            'oauthPortalUrl': '/api/auth/oidc/login',
            'apiUrl': '/api',
            'apiBrowserKey': '',
            'externalOidcEnabled': oidc_enabled,
            'externalOidcProvider': provider,
        }, separators=(',', ':'))
        + ';'
    )
    return Response(content=script, media_type='application/javascript', headers={'Cache-Control': 'no-store'})


def _current_user(aeromind_session: str | None):
    if not aeromind_session:
        return None
    try:
        verified = _verified(aeromind_session)
        raw = base64.urlsafe_b64decode(verified + '=' * (-len(verified) % 4)).decode()
        subject, email = raw.split('|', 1)
        return {'id': subject, 'email': email, 'name': email, 'role': 'user'}
    except Exception:
        return None


@app.get('/api/trpc/{procedure:path}', include_in_schema=False)
async def trpc_compat(procedure: str, aeromind_session: str | None = Cookie(default=None)):
    """Small compatibility bridge for the legacy React query layer.

    Business operations remain on the Python API; these responses prevent the
    old client bootstrap queries from failing while the cockpit migrates away
    from the former Node/tRPC server.
    """
    name = procedure.split('?')[0].rstrip('/')
    if name.endswith('auth.me'):
        data = _current_user(aeromind_session)
    elif name.endswith('identity.providers'):
        data = [{'id': 'entra', 'name': 'Microsoft Entra ID', 'type': 'oidc', 'enabled': bool(settings.oidc)}]
    elif name.endswith('ai.status'):
        data = {'available': bool(settings.openai_api_key), 'provider': 'OpenAI-compatible' if settings.openai_api_key else 'local'}
    elif name.endswith('labBench.status'):
        data = {'ready': True, 'mode': 'safe-python'}
    else:
        data = None
    # The legacy React client uses the SuperJSON transformer. Its wire format
    # wraps serialized values under `data.json`; returning a plain object here
    # makes the query look unauthenticated even though the OIDC cookie is valid.
    response = JSONResponse([{'result': {'data': {'json': data}}}])
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Vary'] = 'Cookie'
    return response


@app.get('/api/oidc/login', include_in_schema=False)
def legacy_oidc_login():
    return RedirectResponse('/api/auth/oidc/login', status_code=307)


@app.get('/', response_class=HTMLResponse)
def home():
    if FRONTEND_INDEX.is_file():
        return FileResponse(FRONTEND_INDEX)
    return """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AeroMind AI</title></head><body style="font-family:system-ui;max-width:760px;margin:4rem auto;padding:0 1.5rem">
<h1>AeroMind AI</h1><p>API d’ingénierie et de simulation opérationnelle.</p>
<p id="auth">Vérification de la session…</p>
<p><a href="/api/health">Health</a> · <a href="/api/capabilities">Capabilities</a> · <a href="/api/auth/oidc/login">Connexion Entra/OIDC</a></p>
<script>fetch('/api/auth/oidc/me').then(r=>r.ok?r.json():null).then(x=>{document.getElementById('auth').textContent=x?'Session active : '+x.email:'Non authentifié';}).catch(()=>{document.getElementById('auth').textContent='Session non vérifiée';});</script>
</body></html>"""


@app.get('/favicon.ico', include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get('/api/ready')
def ready():
    return {'ready': True, 'database': 'not-configured', 'mode': 'in-memory-safe'}


@app.get('/api/capabilities')
def capabilities():
    return {'service': 'aeromind-ai', 'version': '2.0.0', 'oidc': bool(settings.oidc), 'llm': bool(settings.openai_api_key), 'hardware_control': False, 'mission_upload': False, 'telemetry_write': False}


@app.get('/api/system/status')
def system_status():
    return _engine_status()


@app.get('/api/safety/check')
def safety_check():
    result = _engine_status()
    return {'safe': bool(result.get('loaded')), 'hardware_control': False, 'result': result}


@app.get('/{path:path}', include_in_schema=False)
def frontend_routes(path: str):
    if path.startswith('api/'):
        raise HTTPException(404, 'Not found')
    requested = FRONTEND_DIR / path
    if requested.is_file():
        return FileResponse(requested)
    if FRONTEND_INDEX.is_file():
        return FileResponse(FRONTEND_INDEX)
    raise HTTPException(404, 'Frontend not built')


@app.exception_handler(Exception)
async def safe_error(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={'error': 'internal_error', 'type': type(exc).__name__})
