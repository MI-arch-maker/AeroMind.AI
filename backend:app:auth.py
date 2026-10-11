"""Authentification JWT, hiérarchie de rôles, règle des deux personnes."""
import time, uuid, json
import jwt
from enum import Enum
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from . import core
from .core import one, now_iso

class Role(str, Enum):
    VIEWER = "viewer"; OPERATOR = "operator"; ADMIN = "admin"; SUPER_ADMIN = "super_admin"

HIERARCHY = {Role.VIEWER: 0, Role.OPERATOR: 1, Role.ADMIN: 2, Role.SUPER_ADMIN: 3}
HIGH_RISK = {"bench_arm", "cert_issue", "payload_arm"}
DUAL_TTL_S = 600

_bearer = HTTPBearer(auto_error=False)
_r = APIRouter(prefix="/api/auth")

class Creds(BaseModel):
    username: str; password: str

class NewUser(BaseModel):
    username: str; password: str; role: Role

class DualReq(BaseModel):
    action: str; target: str

def make_token(username, role):
    return jwt.encode({"sub": username, "role": role, "exp": int(time.time()) + core.JWT_EXP_S},
                      core.JWT_SECRET, algorithm="HS256")

def parse_token(token):
    try: return jwt.decode(token, core.JWT_SECRET, algorithms=["HS256"])
    except Exception: return None

def current_user(cred: HTTPAuthorizationCredentials = Depends(_bearer)):
    if not cred: raise HTTPException(401, "authentification requise")
    data = parse_token(cred.credentials)
    if not data: raise HTTPException(401, "jeton invalide ou expiré")
    return {"username": data["sub"], "role": data["role"]}

def require(min_role: Role):
    def dep(user=Depends(current_user)):
        if HIERARCHY[Role(user["role"])] < HIERARCHY[min_role]:
            raise HTTPException(403, f"rôle {min_role.value} requis")
        return user
    return dep

@_r.post("/login")
def login(c: Creds):
    u = one("SELECT * FROM users WHERE username=?", (c.username,))
    if not u or not core.check_pw(c.password, u["salt"], u["pw_hash"]):
        raise HTTPException(401, "identifiants invalides")
    core.append_audit(u["username"], "auth.login", u["username"], {})
    return {"token": make_token(u["username"], u["role"]), "username": u["username"], "role": u["role"]}

@_r.get("/me")
def me(user=Depends(current_user)): return user

@_r.get("/users")
def list_users(user=Depends(require(Role.SUPER_ADMIN))):
    from .core import q
    return [{"username": r["username"], "role": r["role"], "created_at": r["created_at"]}
            for r in q("SELECT * FROM users ORDER BY created_at")]

@_r.post("/users")
def create_user(nu: NewUser, user=Depends(require(Role.SUPER_ADMIN))):
    if one("SELECT id FROM users WHERE username=?", (nu.username,)):
        raise HTTPException(409, "utilisateur existant")
    salt, h = core.hash_pw(nu.password)
    from .core import x
    x("INSERT INTO users(username,salt,pw_hash,role,created_at) VALUES(?,?,?,?,?)",
      (nu.username, salt, h, nu.role.value, now_iso()))
    core.append_audit(user["username"], "user.create", nu.username, {"role": nu.role.value})
    return {"ok": True}

# ---------- Règle des deux personnes ----------
@_r.post("/dual")
def dual_request(req: DualReq, user=Depends(require(Role.ADMIN))):
    if req.action not in HIGH_RISK:
        raise HTTPException(400, f"action non sensible ; autorisées : {sorted(HIGH_RISK)}")
    token = uuid.uuid4().hex
    from .core import x
    x("INSERT INTO dual_tokens(token,action,target,approvers,ts) VALUES(?,?,?,?,?)",
      (token, req.action, req.target, json.dumps([user["username"]]), time.time()))
    core.append_audit(user["username"], "dual.request", req.target, {"action": req.action, "token": token})
    return {"token": token, "status": "awaiting_second_approval", "ttl_s": DUAL_TTL_S}

@_r.post("/dual/{token}/confirm")
def dual_confirm(token: str, user=Depends(require(Role.ADMIN))):
    row = one("SELECT * FROM dual_tokens WHERE token=?", (token,))
    if not row or time.time() - row["ts"] > DUAL_TTL_S:
        raise HTTPException(410, "demande inconnue ou expirée")
    approvers = json.loads(row["approvers"])
    if user["username"] in approvers:
        raise HTTPException(409, "une deuxième personne DISTINCTE doit confirmer")
    approvers.append(user["username"])
    from .core import x
    x("UPDATE dual_tokens SET approvers=? WHERE token=?", (json.dumps(approvers), token))
    core.append_audit(user["username"], "dual.confirm", row["target"], {"action": row["action"]})
    return {"token": token, "status": "confirmed", "action": row["action"], "target": row["target"]}

def consume_dual(token: str, action: str, target: str):
    """Valide (2 approbateurs distincts, non expiré, action/cible cohérentes) puis détruit le jeton."""
    row = one("SELECT * FROM dual_tokens WHERE token=?", (token or "",))
    if not row or time.time() - row["ts"] > DUAL_TTL_S:
        raise HTTPException(410, "jeton double-approbation inconnu ou expiré")
    approvers = json.loads(row["approvers"])
    if len(approvers) < 2 or row["action"] != action or row["target"] != str(target):
        raise HTTPException(403, "double approbation incomplète ou incohérente")
    from .core import x
    x("DELETE FROM dual_tokens WHERE token=?", (token,))
    return approvers