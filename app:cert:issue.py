# app/cert/issue.py
import hashlib, json, datetime, uuid
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def _canon(o): return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()

def generate_keypair():
    k = Ed25519PrivateKey.generate()
    return (k.private_bytes(serialization.Encoding.PEM,
                            serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()),
            k.public_key().public_bytes(serialization.Encoding.PEM,
                                        serialization.PublicFormat.SubjectPublicKeyInfo))

def issue_certificate(payload: dict, private_pem: bytes) -> dict:
    """payload = {drone_id, cfd_report_hash, bench_report_hash, test_log_ref...}"""
    payload = {**payload, "issued_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    doc = {"type": "AeroMind.InternalPerformanceCertificate",  # PAS une certification officielle
           "version": 1, "serial": uuid.uuid4().hex,
           "issuer": "AeroMind.IA (interne, sans valeur réglementaire)",
           "payload": payload}
    body = {k: v for k, v in doc.items()}
    doc["sha256"] = hashlib.sha256(_canon(body)).hexdigest()
    key = serialization.load_pem_private_key(private_pem, password=None)
    doc["signature"] = key.sign(bytes.fromhex(doc["sha256"])).hex()
    return doc   # à stocker + publier la clé publique pour vérification publique

def verify(doc: dict, public_pem: bytes) -> bool:
    sig, h = bytes.fromhex(doc.pop("signature")), doc.pop("sha256")
    ok_hash = hashlib.sha256(_canon(doc)).hexdigest() == h
    pub = serialization.load_pem_public_key(public_pem)
    try:
        pub.verify(sig, bytes.fromhex(h)); return ok_hash
    except Exception:
        return False