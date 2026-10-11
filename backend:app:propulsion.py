"""Module 4 — dimensionnement propulsion : élec (LiPo/Li-ion), hydrogène (700 bar + PAC),
thermique (2T/4T). Puissance (théorie de la quantité de mouvement), endurance, autonomie,
budget masse et courbes de charge utile."""
import math
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from .core import append_audit
from .auth import current_user

_r = APIRouter(prefix="/api/propulsion")
RHO, G = 1.225, 9.81

SOURCES = {
    "lipo":   {"label": "Batterie LiPo",           "wh_per_kg": 180.0,   "eff": 0.80, "color": "#38bdf8"},
    "liion":  {"label": "Batterie Li-ion",         "wh_per_kg": 250.0,   "eff": 0.80, "color": "#818cf8"},
    "h2_fc":  {"label": "Hydrogène 700 bar + PAC", "wh_per_kg": 650.0,   "eff": 0.50, "color": "#34d399"},
    "gas_2t": {"label": "Essence 2-temps",         "wh_per_kg": 12000.0, "eff": 0.20, "color": "#f59e0b"},
    "gas_4t": {"label": "Essence 4-temps",         "wh_per_kg": 12000.0, "eff": 0.28, "color": "#f97316"},
}

def hover_power_w(mass, n_props, prop_d, k=1.15):
    """P = k·T^1,5/√(2ρA) par hélice (quantité de mouvement)."""
    T = mass*G/n_props
    A = math.pi/4*prop_d**2
    return k*n_props*T**1.5/math.sqrt(2*RHO*A)

def cruise_power_w(mass, v, ld, eff=0.70):
    return mass*G*v/ld/eff

class CompareBody(BaseModel):
    mtom_kg: float = 7.0; n_props: int = 4; prop_d_m: float = 0.33
    payload_kg: float = 1.0; energy_kg: float = 1.0
    mode: str = "hover"; v_cruise: float = 20.0; ld: float = 10.0
    f_struct: float = 0.32; m_fixed_kg: float = 0.5
    sources: list[str] = list(SOURCES)

@_r.get("/sources")
def sources(user=Depends(current_user)): return SOURCES

@_r.post("/compare")
def compare(b: CompareBody, user=Depends(current_user)):
    P = hover_power_w(b.mtom_kg, b.n_props, b.prop_d_m) if b.mode == "hover" \
        else cruise_power_w(b.mtom_kg, b.v_cruise, b.ld)
    out = []
    for s in b.sources:
        if s not in SOURCES: continue
        src = SOURCES[s]
        e_wh = b.energy_kg*src["wh_per_kg"]*src["eff"]
        out.append({"key": s, "label": src["label"], "color": src["color"],
                    "wh_per_kg": src["wh_per_kg"], "eff": src["eff"],
                    "power_w": round(P), "energy_kg": b.energy_kg, "usable_wh": round(e_wh),
                    "endurance_h": round(e_wh/P, 2),
                    "range_km": round(b.v_cruise*e_wh/P/1000, 1) if b.mode == "cruise" else None})
    append_audit(user["username"], "propulsion.compare", "-", b.model_dump())
    return {"mode": b.mode, "power_w": round(P), "results": out,
            "budget": {"mtom_kg": b.mtom_kg, "payload_kg": b.payload_kg,
                       "structure_kg": round(b.f_struct*b.mtom_kg, 2),
                       "fixed_kg": b.m_fixed_kg}}

class CurveBody(CompareBody):
    t_max_h: float = 2.0; n_points: int = 25

@_r.post("/payload-curve")
def payload_curve(b: CurveBody, user=Depends(current_user)):
    P = hover_power_w(b.mtom_kg, b.n_props, b.prop_d_m) if b.mode == "hover" \
        else cruise_power_w(b.mtom_kg, b.v_cruise, b.ld)
    ts = [round(b.t_max_h*i/(b.n_points-1), 2) for i in range(b.n_points)]
    series = []
    for s in b.sources:
        if s not in SOURCES: continue
        e_rate = SOURCES[s]["wh_per_kg"]*SOURCES[s]["eff"]
        pts = [[t, round(max(0.0, b.mtom_kg*(1-b.f_struct) - b.m_fixed_kg - P*t/e_rate), 3)] for t in ts]
        series.append({"key": s, "label": SOURCES[s]["label"], "color": SOURCES[s]["color"], "points": pts})
    return {"mode": b.mode, "power_w": round(P), "t": ts, "series": series,
            "note": f"charge utile = MTOM·(1−f_struct) − fixes − masse d'énergie ; "
                    f"f_struct={b.f_struct}, fixes={b.m_fixed_kg} kg"}