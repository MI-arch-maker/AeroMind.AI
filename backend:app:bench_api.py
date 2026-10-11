"""Module 3 — sessions de banc d'essai, contrôle REST, télémétrie WebSocket temps réel.
ARMEMENT MOTEUR soumis à la règle des deux personnes (deux admins distincts)."""
import asyncio, json, math
from fastapi import APIRouter, HTTPException, Depends, WebSocket
from pydantic import BaseModel
from .core import one, now_iso, new_id, append_audit
from .auth import require, current_user, Role, consume_dual, parse_token
from .flightops import check_point
from .bench_sim import QuadSim, FixedWingSim

_r = APIRouter(prefix="/api/bench")
SESSIONS = {}

class CreateBody(BaseModel):
    kind: str = "quad"                 # quad | fw | external
    flight_request_id: str | None = None
    params: dict = {}
class ArmBody(BaseModel):
    dual_token: str
class ModeBody(BaseModel):
    mode: str; target: dict | None = None
class MissionBody(BaseModel):
    waypoints: list[dict]              # {x,y,z} mètres ou {lat,lon,alt}
class GotoBody(BaseModel):
    x: float; y: float; z: float

def _get(sid):
    s = SESSIONS.get(sid)
    if not s: raise HTTPException(404, "session inconnue")
    return s

def _to_local(sim, w):
    if "lat" in w and getattr(sim, "lat0", None) is not None:
        x = (w["lon"] - sim.lon0)*111320*math.cos(math.radians(sim.lat0))
        y = (w["lat"] - sim.lat0)*110540
        return {"x": x, "y": y, "z": w.get("alt", 50.0)}, w
    return {"x": w.get("x", 0), "y": w.get("y", 0), "z": w.get("z", 50.0)}, None

async def _loop(s):
    try:
        while s["id"] in SESSIONS:
            await asyncio.sleep(0.05)
            try:
                s["sim"].step(0.05)
            except Exception as e:
                s["last_error"] = str(e)
            for v in s["sim"].pop_violations():
                append_audit("bench", "bench.violation", s["id"], {"msg": v})
            msg = json.dumps(s["sim"].telemetry())
            for ws in list(s["clients"]):
                try: await ws.send_text(msg)
                except Exception: s["clients"].discard(ws)
    except asyncio.CancelledError:
        pass

@_r.post("/sessions")
async def create(b: CreateBody, user=Depends(require(Role.OPERATOR))):
    if b.flight_request_id:
        fr = one("SELECT status FROM flight_requests WHERE id=?", (b.flight_request_id,))
        if not fr: raise HTTPException(404, "demande de vol inconnue")
        if fr["status"] != "authorized":
            raise HTTPException(403, "le vol doit être AUTORISÉ avant tout essai")
    sid = new_id()
    if b.kind == "quad": sim = QuadSim(**b.params)
    elif b.kind == "fw": sim = FixedWingSim(**b.params)
    elif b.kind == "external":
        from .bench_mavlink import ExternalSITL
        sim = ExternalSITL(b.params.get("url", "tcp:127.0.0.1:5760"))
    else: raise HTTPException(400, "kind ∈ quad|fw|external")
    SESSIONS[sid] = {"id": sid, "kind": b.kind, "sim": sim, "clients": set(),
                     "created_by": user["username"], "created_at": now_iso(),
                     "flight_request_id": b.flight_request_id}
    SESSIONS[sid]["task"] = asyncio.create_task(_loop(SESSIONS[sid]))
    append_audit(user["username"], "bench.create", sid, {"kind": b.kind, "fr": b.flight_request_id})
    return {"id": sid, "kind": b.kind}

@_r.get("/sessions")
def list_s(user=Depends(current_user)):
    return [{"id": s["id"], "kind": s["kind"], "created_by": s["created_by"],
             "created_at": s["created_at"], "flight_request_id": s["flight_request_id"]}
            for s in SESSIONS.values()]

@_r.get("/sessions/{sid}")
def detail(sid, user=Depends(current_user)):
    s = _get(sid)
    return {"id": sid, "kind": s["kind"], "created_by": s["created_by"],
            "mission": [w.tolist() for w in getattr(s["sim"], "mission", [])],
            "telemetry": s["sim"].telemetry()}

@_r.delete("/sessions/{sid}")
async def delete_s(sid, user=Depends(require(Role.OPERATOR))):
    s = SESSIONS.pop(sid, None)
    if not s: raise HTTPException(404, "session inconnue")
    s["task"].cancel()
    append_audit(user["username"], "bench.delete", sid, {})
    return {"ok": True}

@_r.post("/sessions/{sid}/arm")
def arm(sid, body: ArmBody, user=Depends(require(Role.ADMIN))):
    s = _get(sid)
    consume_dual(body.dual_token, "bench_arm", sid)     # deux humains distincts requis
    s["sim"].arm()
    append_audit(user["username"], "bench.arm", sid, {})
    return {"armed": True, "mode": s["sim"].mode}

@_r.post("/sessions/{sid}/disarm")
def disarm(sid, user=Depends(require(Role.ADMIN))):
    s = _get(sid); s["sim"].disarm()
    append_audit(user["username"], "bench.disarm", sid, {})
    return {"armed": False}

@_r.post("/sessions/{sid}/mode")
def set_mode(sid, b: ModeBody, user=Depends(require(Role.OPERATOR))):
    s = _get(sid)
    try: s["sim"].set_mode(b.mode, b.target)
    except ValueError as e: raise HTTPException(409, str(e))
    append_audit(user["username"], "bench.mode", sid, {"mode": b.mode})
    return {"mode": b.mode}

@_r.post("/sessions/{sid}/mission")
def mission(sid, b: MissionBody, user=Depends(require(Role.OPERATOR))):
    s = _get(sid)
    local, warnings = [], []
    for w in b.waypoints:
        lw, geo = _to_local(s["sim"], w)
        local.append(lw)
        if geo:
            zc = check_point(geo["lat"], geo["lon"], geo.get("alt", 50.0))
            warnings += zc["violations"]
    s["sim"].load_mission(local)
    append_audit(user["username"], "bench.mission", sid, {"n": len(local), "warnings": warnings})
    return {"loaded": len(local), "warnings": warnings}

@_r.post("/sessions/{sid}/goto")
def goto(sid, b: GotoBody, user=Depends(require(Role.OPERATOR))):
    s = _get(sid); s["sim"].goto(b.x, b.y, b.z)
    return {"ok": True}

@_r.websocket("/ws/{sid}")
async def ws(sock: WebSocket, sid: str, token: str = ""):
    if not parse_token(token):
        await sock.close(code=4401); return
    s = SESSIONS.get(sid)
    if not s:
        await sock.close(code=4404); return
    await sock.accept(); s["clients"].add(sock)
    try:
        while True: await sock.receive_text()
    except Exception:
        pass
    finally:
        s["clients"].discard(sock)