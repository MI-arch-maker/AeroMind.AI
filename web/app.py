from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import get_settings
from .copilot import router as copilot_router
from .oidc import router as oidc_router


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


@app.exception_handler(Exception)
async def safe_error(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={'error': 'internal_error', 'type': type(exc).__name__})
