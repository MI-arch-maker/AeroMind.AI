# app/audit/chain.py
import hashlib, json, datetime

def _canon(entry: dict) -> bytes:
    return json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()

def append_audit(conn, actor: str, action: str, target: str, detail: dict):
    prev = conn.execute("SELECT entry_hash FROM audit ORDER BY id DESC LIMIT 1"
                        ).fetchone()
    prev_hash = prev[0] if prev else "GENESIS"
    entry = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "actor": actor, "action": action, "target": target,
             "detail": detail, "prev_hash": prev_hash}
    entry["entry_hash"] = hashlib.sha256(_canon(entry)).hexdigest()
    conn.execute(
        "INSERT INTO audit (ts, actor, action, target, detail, prev_hash, entry_hash)"
        " VALUES (:ts,:actor,:action,:target,:detail,:prev_hash,:entry_hash)", entry)
    conn.commit()