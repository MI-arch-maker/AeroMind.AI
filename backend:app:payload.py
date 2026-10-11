"""Charge utile CIVILE gouvernée (largage médical/balise/capteur) — catégorie contrôlée,
contrôle de zone + double validation humaine + actionneur simulé."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .core import x, q, one, now_iso, new_id, append_audit
from .auth import require, Role, consume_dual
from .flightops import check_point

_r = APIRouter(prefix="/api/payload")
ALLOWED = {"medical_drop", "beacon", "sensor_pod", "light"}

class ArmBody(BaseModel):
    category: str; lat: float; lon: float; alt_m: float; dual_token: str

@_r.get("/categories")
def cats(user=Depends(require(Role.OPERATOR))): return sorted(ALLOWED)

@_r.post("/arm")
def arm(b: ArmBody, user=Depends(require(Role.ADMIN))):
    if b.category not in ALLOWED:
        raise HTTPException(400, "catégorie non autorisée — charges civiles uniquement")
    zc = check_point(b.lat, b.lon, b.alt_m)
    if not zc["ok"]:
        raise HTTPException(403, {"message": "zone interdite", "violations": zc["violations"]})
    approvers = consume_dual(b.dual_token, "payload_arm", b.category)
    rid = new_id()
    x("INSERT INTO releases(id,ts,category,lat,lon,alt_m,status,created_by) VALUES(?,?,?,?,?,?,?,?)",
      (rid, now_iso(), b.category, b.lat, b.lon, b.alt_m, "armed", user["username"]))
    append_audit(user["username"], "payload.arm", rid,
                 {"category": b.category, "approvers": approvers})
    return {"release_id": rid, "status": "armed"}

@_r.post("/execute/{rid}")
def execute(rid, user=Depends(require(Role.ADMIN))):
    row = one("SELECT * FROM releases WHERE id=?", (rid,))
    if not row or row["status"] != "armed": raise HTTPException(409, "largage non armé")
    x("UPDATE releases SET status='executed' WHERE id=?", (rid,))
    append_audit(user["username"], "payload.execute", rid, {})
    return {"release_id": rid, "status": "executed (actionneur simulé)"}

@_r.get("")
def list_r(user=Depends(require(Role.OPERATOR))):
    return [dict(r) for r in q("SELECT * FROM releases ORDER BY ts DESC")]