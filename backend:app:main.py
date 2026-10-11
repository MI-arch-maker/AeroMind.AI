"""AeroMind.IA — point d'entrée. Compatible Render : écoute sur $PORT, health check /api/health."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from . import core
from .core import one
from .auth import parse_token
from . import auth as auth_mod, audit as audit_mod, flightops, cfd_api
from . import bench_api, propulsion, cert, payload

app = FastAPI(title="AeroMind.IA — centre opérationnel", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _startup(): core.init_db()

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AeroMind.IA", "version": app.version}

@app.get("/api/files/{fid}")
def get_file(fid: str, token: str = ""):
    """Fichiers générés (dossiers, VTP). Auth par ?token= (nécessaire pour ParaView Glance)."""
    if not parse_token(token): raise HTTPException(401, "jeton requis (?token=)")
    row = one("SELECT * FROM files WHERE id=?", (fid,))
    if not row: raise HTTPException(404, "fichier inconnu")
    return FileResponse(row["path"], filename=row["name"],
                        media_type="text/markdown" if row["name"].endswith(".md")
                        else "application/octet-stream",
                        headers={"Access-Control-Allow-Origin": "*"})

for router in (auth_mod._r, audit_mod._r, flightops._r, cfd_api._r,
               bench_api._r, propulsion._r, cert._r, payload._r):
    app.include_router(router)

_static = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static"))
if os.path.isdir(_static):
    app.mount("/", StaticFiles(directory=_static, html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))