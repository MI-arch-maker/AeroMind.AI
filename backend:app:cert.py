"""Certification INTERNE signée Ed25519 — preuve d'intégrité/traçabilité, sans valeur réglementaire."""
import hashlib, json, uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from .core import kv_get, kv_set, q, one, now_iso, x, append_audit
from .auth import require, Role, consume_dual, current_user

_r = APIRouter(prefix="/api/cert")

class CertBody(BaseModel):
    drone_id: str
    cfd_run_id: str | None = None
    bench_session_id: str | None = None
    flight_request_id: str | None = None
    notes: str = ""
    dual_token: str = ""

def _canon(o): return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()

def _keypair():
    priv = kv_get("cert_priv")
    if priv: return priv.encode(), kv_get("cert_pub").encode()
    k = Ed25519PrivateKey.generate()
    priv = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption())
    pub = k.public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo)
    kv_set("cert_priv", priv.decode()); kv_set("cert_pub", pub.decode())
    return priv, pub

@_r.post("/issue")
def issue(b: CertBody, user=Depends(require(Role.ADMIN))):
    approvers = consume_dual(b.dual_token, "cert_issue", b.drone_id)   # deux humains
    priv, _ = _keypair()
    payload = {**b.model_dump(exclude={"dual_token"}), "issued_at": now_iso(),
               "issuer": user["username"], "approvers": approvers}
    doc = {"type": "AeroMind.InternalPerformanceCertificate", "version": 1,
           "serial": f"CERT-{uuid.uuid4().hex[:10].upper()}", "payload": payload,
           "disclaimer": "Certification INTERNE AeroMind.IA — preuve d'intégrité et de "
                         "traçabilité. Sans valeur réglementaire (ni DGAC ni EASA)."}
    doc["sha256"] = hashlib.sha256(_canon(doc)).hexdigest()
    doc["signature"] = serialization.load_pem_private_key(priv, password=None)\
        .sign(bytes.fromhex(doc["sha256"])).hex()
    x("INSERT INTO certs(serial,issued_at,drone_id,doc) VALUES(?,?,?,?)",
      (doc["serial"], payload["issued_at"], b.drone_id, json.dumps(doc)))
    append_audit(user["username"], "cert.issue", doc["serial"], {"drone": b.drone_id})
    return doc

@_r.get("")
def list_c(user=Depends(current_user)):
    return [json.loads(r["doc"]) for r in q("SELECT doc FROM certs ORDER BY issued_at DESC")]

@_r.get("/verify/{serial}")
def verify(serial, user=Depends(current_user)):
    row = one("SELECT doc FROM certs WHERE serial=?", (serial,))
    if not row: raise HTTPException(404, "certificat inconnu")
    doc = json.loads(row["doc"])
    sig = bytes.fromhex(doc.pop("signature")); h = doc.pop("sha256")
    ok_h = hashlib.sha256(_canon(doc)).hexdigest() == h
    _, pub = _keypair()
    try:
        serialization.load_pem_public_key(pub).verify(sig, bytes.fromhex(h)); ok_s = True
    except Exception: ok_s = False
    return {"serial": serial, "hash_ok": ok_h, "signature_ok": ok_s,
            "valid": ok_h and ok_s, "payload": doc.get("payload")}

@_r.get("/pubkey")
def pubkey(user=Depends(current_user)):
    return {"public_key_pem": (kv_get("cert_pub") or _keypair()[1].decode())}