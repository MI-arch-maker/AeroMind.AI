"""Module 1 — autorisations de vol INTERNES + génération de dossier de PRÉPARATION DGAC/SORA.
NB : les autorisations officielles relèvent de la DGAC (AlphaTangent) ; la SORA officielle
(JARUS) doit être conduite par un évaluateur qualifié. Ce module prépare et trace."""
import json, math, uuid, datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .core import q, x, one, now_iso, new_id, register_file, append_audit
from .auth import require, current_user, Role

_r = APIRouter(prefix="/api/flightops")

# ---------- Zones contrôlées (échantillon — extensible) ----------
CONTROLLED_ZONES = [
    {"name": "CTR Toulouse-Blagnac (LFBO)", "lat": 43.6293, "lon": 1.3638, "radius_m": 9000},
    {"name": "CTR Paris-CDG (LFPG)",        "lat": 49.0097, "lon": 2.5479, "radius_m": 12000},
    {"name": "CTR Bordeaux-Mérignac (LFBD)","lat": 44.8283, "lon": -0.7156, "radius_m": 8000},
    {"name": "Paris intramuros (interdiction)", "lat": 48.8566, "lon": 2.3522, "radius_m": 10500},
]
MAX_ALT_OPEN_M = 120.0

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def check_point(lat, lon, alt_m):
    v = []
    for z in CONTROLLED_ZONES:
        d = haversine_m(lat, lon, z["lat"], z["lon"])
        if d < z["radius_m"]:
            v.append(f"Point dans {z['name']} (à {int(d)} m du centre)")
    if alt_m and alt_m > MAX_ALT_OPEN_M:
        v.append(f"Altitude {alt_m:.0f} m > plafond 120 m (catégorie ouverte)")
    return {"ok": not v, "violations": v, "checked_at": now_iso()}

# ---------- SORA simplifiée (indicative) ----------
POP_IGRC = {"sparse": 2, "moderate": 4, "dense": 6}
MITIG_GROUND = {"parachute": 1, "geo_awareness": 1}
SAIL_TABLE = {
    "a": {1:"I",2:"I",3:"II",4:"II",5:"III",6:"III",7:"IV"},
    "b": {1:"I",2:"II",3:"II",4:"III",5:"III",6:"IV",7:"V"},
    "c": {1:"II",2:"II",3:"III",4:"III",5:"IV",6:"V",7:"VI"},
    "d": {1:"II",2:"III",3:"III",4:"IV",5:"V",6:"VI",7:"VI"},
}

def sora_assessment(population, mtom_g, airspace, mitigations):
    igrc = POP_IGRC[population] + (1 if mtom_g > 4000 else 0)
    grc = max(1, igrc - sum(MITIG_GROUND.get(m, 0) for m in mitigations))
    return {"intrinsic_grc": igrc, "final_grc": grc, "arc": airspace,
            "sail": SAIL_TABLE[airspace][grc], "mitigations": mitigations,
            "note": "SORA simplifiée, à titre indicatif (préparation). L'évaluation officielle "
                    "JARUS doit être conduite par un évaluateur qualifié."}

# ---------- Modèles ----------
class FlightReq(BaseModel):
    operator_name: str; operator_contact: str
    uas_name: str; uas_class: str; mtom_g: int
    op_category: str; purpose: str
    center_lat: float; center_lon: float; radius_m: float
    alt_min_m: float; alt_max_m: float
    start_utc: str; end_utc: str
    population: str; airspace: str
    mitigations: list[str] = []

class ReviewBody(BaseModel):
    decision: str; comment: str = ""

class PointCheck(BaseModel):
    lat: float; lon: float; alt_m: float

def _row(r):
    d = dict(r)
    for k in ("mitigations", "zone_check", "approvers"):
        if isinstance(d.get(k), str):
            try: d[k] = json.loads(d[k])
            except Exception: pass
    return d

@_r.get("/zones")
def zones(user=Depends(current_user)): return CONTROLLED_ZONES

@_r.post("/zones/check")
def zone_check(p: PointCheck, user=Depends(current_user)):
    return check_point(p.lat, p.lon, p.alt_m)

@_r.post("/requests")
def create(fr: FlightReq, user=Depends(require(Role.OPERATOR))):
    rid = new_id()
    zc = check_point(fr.center_lat, fr.center_lon, fr.alt_max_m)
    x("""INSERT INTO flight_requests(id,created_by,created_at,status,operator_name,operator_contact,
        uas_name,uas_class,mtom_g,op_category,purpose,center_lat,center_lon,radius_m,alt_min_m,
        alt_max_m,start_utc,end_utc,population,airspace,mitigations,zone_check,approvers)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
      (rid, user["username"], now_iso(), "draft", fr.operator_name, fr.operator_contact,
       fr.uas_name, fr.uas_class, fr.mtom_g, fr.op_category, fr.purpose, fr.center_lat,
       fr.center_lon, fr.radius_m, fr.alt_min_m, fr.alt_max_m, fr.start_utc, fr.end_utc,
       fr.population, fr.airspace, json.dumps(fr.mitigations), json.dumps(zc), json.dumps([])))
    append_audit(user["username"], "flight.create", rid, {"uas": fr.uas_name, "zone_ok": zc["ok"]})
    return {"id": rid, "zone_check": zc}

@_r.get("/requests")
def list_req(user=Depends(current_user)):
    return [_row(r) for r in q("SELECT * FROM flight_requests ORDER BY created_at DESC")]

@_r.get("/requests/{rid}")
def get_req(rid, user=Depends(current_user)):
    r = one("SELECT * FROM flight_requests WHERE id=?", (rid,))
    if not r: raise HTTPException(404, "demande inconnue")
    return _row(r)

@_r.post("/requests/{rid}/submit")
def submit(rid, user=Depends(require(Role.OPERATOR))):
    r = one("SELECT * FROM flight_requests WHERE id=?", (rid,))
    if not r or r["status"] != "draft": raise HTTPException(409, "état incompatible")
    x("UPDATE flight_requests SET status='submitted' WHERE id=?", (rid,))
    append_audit(user["username"], "flight.submit", rid, {})
    return {"status": "submitted"}

@_r.post("/requests/{rid}/review")
def review(rid, body: ReviewBody, user=Depends(require(Role.ADMIN))):
    r = one("SELECT * FROM flight_requests WHERE id=?", (rid,))
    if not r or r["status"] != "submitted": raise HTTPException(409, "état incompatible")
    if body.decision == "reject":
        x("UPDATE flight_requests SET status='rejected',reviewer=?,review_comment=? WHERE id=?",
          (user["username"], body.comment, rid))
        append_audit(user["username"], "flight.reject", rid, {"comment": body.comment})
        return {"status": "rejected"}
    if body.decision != "approve": raise HTTPException(400, "decision ∈ approve|reject")
    x("UPDATE flight_requests SET status='pending_dual',reviewer=?,review_comment=? WHERE id=?",
      (user["username"], body.comment, rid))
    append_audit(user["username"], "flight.review1", rid, {})
    return {"status": "pending_dual"}

@_r.post("/requests/{rid}/confirm")
def confirm(rid, user=Depends(require(Role.ADMIN))):
    r = one("SELECT * FROM flight_requests WHERE id=?", (rid,))
    if not r or r["status"] != "pending_dual": raise HTTPException(409, "état incompatible")
    if user["username"] == r["reviewer"]:
        raise HTTPException(409, "deux personnes DISTINCTES requises (revu par " + r["reviewer"] + ")")
    serial = f"AM-{datetime.datetime.now(datetime.timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
    approvers = json.dumps([r["reviewer"], user["username"]])
    x("UPDATE flight_requests SET status='authorized',auth_serial=?,approvers=? WHERE id=?",
      (serial, approvers, rid))
    append_audit(user["username"], "flight.authorize", rid, {"serial": serial, "expires": r["end_utc"]})
    return {"status": "authorized", "auth_serial": serial, "expires": r["end_utc"]}

@_r.post("/requests/{rid}/dossier")
def dossier(rid, user=Depends(require(Role.OPERATOR))):
    r = one("SELECT * FROM flight_requests WHERE id=?", (rid,))
    if not r: raise HTTPException(404, "demande inconnue")
    d = _row(r)
    sora = sora_assessment(d["population"], d["mtom_g"], d["airspace"], d.get("mitigations") or [])
    md = build_dossier(d, sora)
    fid = register_file("dossier", f"dossier-{rid}.md", md)
    x("UPDATE flight_requests SET dossier_fid=? WHERE id=?", (fid, rid))
    append_audit(user["username"], "flight.dossier", rid, {"file": fid, "sail": sora["sail"]})
    return {"file_id": fid, "url": f"/api/files/{fid}", "sora": sora}

def build_dossier(d, sora):
    tip = one("SELECT entry_hash FROM audit ORDER BY id DESC LIMIT 1")
    zc = d.get("zone_check") or {}
    return f"""# DOSSIER DE PRÉPARATION D'OPÉRATION UAS — AeroMind.IA
> Document de PRÉPARATION généré le {now_iso()}.
> Ne remplace ni la déclaration AlphaTangent (DGAC) ni une SORA officielle conduite
> par un évaluateur qualifié. Autorisation interne : **{d.get('auth_serial') or 'en cours'}**

## 1. Opérateur
- Nom : {d['operator_name']} — Contact : {d['operator_contact']}
- Créateur du dossier : {d['created_by']}

## 2. Aéronef (UAS)
- Désignation : {d['uas_name']} — Classe : {d['uas_class']} — MTOM : {d['mtom_g']} g
- Scénario : {d['op_category']}

## 3. Opération
- Objectif : {d['purpose']}
- Volume : centre ({d['center_lat']:.5f}, {d['center_lon']:.5f}), rayon {d['radius_m']} m
- Altitudes : {d['alt_min_m']}–{d['alt_max_m']} m sol ; plafond catégorie ouverte : 120 m
- Créneau : {d['start_utc']} → {d['end_utc']} (UTC)

## 4. Contrôle de zone (automatique)
- Statut : {'CONFORME' if (zc or {}).get('ok') else 'AVERTISSEMENTS'}
{chr(10).join('- ⚠ ' + v for v in (zc or {}).get('violations', [])) or '- Aucune violation détectée'}

## 5. Évaluation du risque — SORA simplifiée (indicative)
- iGRC intrinsèque : {sora['intrinsic_grc']} → GRC final : {sora['final_grc']}
- ARC (classe d'espace aérien) : {sora['arc'].upper()}
- **SAIL estimé : {sora['sail']}**
- Mitigations retenues : {', '.join(sora['mitigations']) or 'aucune'}
- {sora['note']}

## 6. Checklists opérationnelles (extrait)
- [ ] Inspection pré-vol cellule, hélices, liaisons radio
- [ ] Batteries chargées et fixées ; autonomie vérifiée (module Propulsion)
- [ ] Géorepérage chargé ; CTR vérifiées (contrôle de zone ci-dessus)
- [ ] Procédure d'interruption (RTL) briefée ; observateur désigné si requis
- [ ] Journal de vol prêt ; télémétrie banc d'essai archivée (module Bench)

## 7. Traçabilité
- Identifiant interne : {d['id']} — Statut : {d['status']}
- Approbateurs : {d.get('approvers') or 'en attente'}
- Empreinte du journal d'audit au moment de l'émission : `{tip['entry_hash'] if tip else 'GENESIS'}`
"""