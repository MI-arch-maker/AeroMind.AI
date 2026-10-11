# app/auth/two_person.py
import time, uuid
from fastapi import HTTPException

DUAL_APPROVAL_TTL_S = 600
_pending: dict[str, dict] = {}   # en prod : table Redis/Postgres

def request_sensitive_action(action: str, target_id: str, requester: str) -> str:
    if action not in HIGH_RISK_ACTIONS:
        raise HTTPException(400, "action non sensible ou inconnue")
    token = uuid.uuid4().hex
    _pending[token] = {"action": action, "target": target_id,
                       "approvers": {requester}, "ts": time.time()}
    return token

def confirm(token: str, confirmer: str) -> dict:
    p = _pending.get(token)
    if not p or time.time() - p["ts"] > DUAL_APPROVAL_TTL_S:
        raise HTTPException(410, "demande expirée")
    if confirmer in p["approvers"]:
        raise HTTPException(409, "deux personnes DISTINCTES requises")
    p["approvers"].add(confirmer)
    if len(p["approvers"]) >= 2:
        del _pending[token]
        return p            # → exécuter l'action + écrire dans l'audit
    raise HTTPException(202, "en attente d'une seconde approbation")