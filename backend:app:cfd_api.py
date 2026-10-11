"""Module 2 — routes CFD."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .core import x, now_iso, new_id, append_audit
from .auth import current_user, require, Role
from . import cfd_panel, cfd_openfoam

_r = APIRouter(prefix="/api/cfd")

class SolveBody(BaseModel):
    code: str = "2412"; alpha_deg: float = 4.0; re: float = 1e6; ar: float | None = None
class SweepBody(BaseModel):
    code: str = "2412"; alpha_min: float = -6.0; alpha_max: float = 16.0
    step: float = 1.0; re: float = 1e6; ar: float | None = None
class FieldBody(BaseModel):
    code: str = "2412"; alpha_deg: float = 4.0
class OFBody(BaseModel):
    U: float = 20.0; aoa_deg: float = 4.0

@_r.get("/capabilities")
def caps(user=Depends(current_user)):
    return {"panel_method": True, "openfoam": cfd_openfoam.available()}

@_r.post("/airfoil/solve")
def solve(b: SolveBody, user=Depends(current_user)):
    res = cfd_panel.solve_full(b.code, b.alpha_deg, b.re, b.ar)
    _save("solve", b.model_dump(), res, user); return res

@_r.post("/airfoil/sweep")
def sweep(b: SweepBody, user=Depends(current_user)):
    res = cfd_panel.sweep(b.code, b.alpha_min, b.alpha_max, b.step, b.re, b.ar)
    _save("sweep", b.model_dump(), {k: (v[:6] if isinstance(v, list) else v) for k, v in res.items()}, user)
    return res

@_r.post("/airfoil/field")
def field(b: FieldBody, user=Depends(current_user)):
    fid = cfd_panel.field_file(b.code, b.alpha_deg)
    _save("field", b.model_dump(), {"file_id": fid}, user)
    return {"file_id": fid, "url": f"/api/files/{fid}"}

@_r.post("/airfoil/openfoam")
def of_run(b: OFBody, user=Depends(require(Role.OPERATOR))):
    if not cfd_openfoam.available():
        raise HTTPException(503, "OpenFOAM indisponible dans ce déploiement — utilisez "
                                 "Dockerfile.openfoam (plan payé) ou la méthode de panneaux.")
    res = cfd_openfoam.run_airfoil2d(b.U, b.aoa_deg)
    _save("openfoam", b.model_dump(), {k: v for k, v in res.items() if "tail" not in k}, user)
    return res

def _save(kind, params, result, user):
    rid = new_id()
    x("INSERT INTO cfd_runs(id,ts,kind,params,result) VALUES(?,?,?,?,?)",
      (rid, now_iso(), kind, json.dumps(params), json.dumps(result)[:20000]))
    append_audit(user["username"], f"cfd.{kind}", rid, params)