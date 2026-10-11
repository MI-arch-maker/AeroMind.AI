"""Journal d'audit : consultation + vérification de la chaîne de hachage."""
import hashlib, json
from fastapi import APIRouter, Depends
from .core import q, one
from .auth import require, Role

_r = APIRouter(prefix="/api/audit")

def _canon(e): return json.dumps(e, sort_keys=True, separators=(",", ":")).encode()

@_r.get("")
def list_audit(limit: int = 200, user=Depends(require(Role.ADMIN))):
    return [dict(r) for r in q("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (min(limit, 2000),))]

@_r.get("/verify")
def verify(user=Depends(require(Role.ADMIN))):
    prev, ok, bad = "GENESIS", True, None
    rows = q("SELECT * FROM audit ORDER BY id")
    for r in rows:
        e = {"ts": r["ts"], "actor": r["actor"], "action": r["action"], "target": r["target"],
             "detail": json.loads(r["detail"]), "prev_hash": r["prev_hash"]}
        if r["prev_hash"] != prev or hashlib.sha256(_canon(e)).hexdigest() != r["entry_hash"]:
            ok, bad = False, r["id"]; break
        prev = r["entry_hash"]
    return {"valid": ok, "first_broken_id": bad, "entries": len(rows)}