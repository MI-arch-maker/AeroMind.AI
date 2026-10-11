"""AeroMind.IA — noyau : config, SQLite, audit chaîné, helpers."""
import os, sqlite3, threading, datetime, uuid, hashlib, secrets, json

DATA_DIR = os.environ.get("DATA_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data")))
os.makedirs(DATA_DIR, exist_ok=True)
FILES_DIR = os.path.join(DATA_DIR, "files"); os.makedirs(FILES_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "aeromind.db")

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-a-changer-en-prod")
JWT_EXP_S = int(os.environ.get("JWT_EXP_S", "86400"))
SEED = {
    "admin@aeromind.local":    ("AeroMind!2025",  "super_admin"),
    "admin2@aeromind.local":   ("Admin2!2025",    "admin"),
    "operator@aeromind.local": ("Operator!2025",  "operator"),
}
if os.environ.get("ADMIN_PASS"):
    SEED["admin@aeromind.local"] = (os.environ["ADMIN_PASS"], "super_admin")

_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
_conn.execute("PRAGMA journal_mode=WAL")
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
  salt TEXT NOT NULL, pw_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, actor TEXT NOT NULL,
  action TEXT NOT NULL, target TEXT NOT NULL, detail TEXT NOT NULL,
  prev_hash TEXT NOT NULL, entry_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dual_tokens(
  token TEXT PRIMARY KEY, action TEXT NOT NULL, target TEXT NOT NULL,
  approvers TEXT NOT NULL, ts REAL NOT NULL);
CREATE TABLE IF NOT EXISTS flight_requests(
  id TEXT PRIMARY KEY, created_by TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL,
  operator_name TEXT, operator_contact TEXT, uas_name TEXT, uas_class TEXT, mtom_g INTEGER,
  op_category TEXT, purpose TEXT, center_lat REAL, center_lon REAL, radius_m REAL,
  alt_min_m REAL, alt_max_m REAL, start_utc TEXT, end_utc TEXT, population TEXT, airspace TEXT,
  mitigations TEXT, zone_check TEXT, review_comment TEXT, reviewer TEXT,
  approvers TEXT, auth_serial TEXT, dossier_fid TEXT);
CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY, kind TEXT, name TEXT, path TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS cfd_runs(id TEXT PRIMARY KEY, ts TEXT, kind TEXT, params TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS certs(serial TEXT PRIMARY KEY, issued_at TEXT, drone_id TEXT, doc TEXT);
CREATE TABLE IF NOT EXISTS releases(
  id TEXT PRIMARY KEY, ts TEXT, category TEXT, lat REAL, lon REAL, alt_m REAL,
  status TEXT, created_by TEXT);
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
"""

def init_db():
    with _lock:
        _conn.executescript(SCHEMA)
        if not one("SELECT id FROM users LIMIT 1"):
            for u, (pw, role) in SEED.items():
                salt, h = hash_pw(pw)
                _conn.execute("INSERT INTO users(username,salt,pw_hash,role,created_at) VALUES(?,?,?,?,?)",
                              (u, salt, h, role, now_iso()))
        _conn.commit()

def q(sql, args=()):
    with _lock: return _conn.execute(sql, args).fetchall()

def x(sql, args=()):
    with _lock:
        cur = _conn.execute(sql, args); _conn.commit(); return cur.lastrowid

def one(sql, args=()):
    rows = q(sql, args); return rows[0] if rows else None

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def new_id(): return uuid.uuid4().hex[:12]

def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 120_000).hex()
    return salt, h

def check_pw(pw, salt, h):
    return secrets.compare_digest(hash_pw(pw, salt)[1], h)

def kv_get(k):
    r = one("SELECT v FROM kv WHERE k=?", (k,)); return r["v"] if r else None

def kv_set(k, v):
    x("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))

def register_file(kind, name, content):
    fid = new_id()
    path = os.path.join(FILES_DIR, f"{fid}_{name}")
    with open(path, "wb" if isinstance(content, (bytes, bytearray)) else "w") as f:
        f.write(content)
    x("INSERT INTO files(id,kind,name,path,ts) VALUES(?,?,?,?,?)", (fid, kind, name, path, now_iso()))
    return fid

def append_audit(actor, action, target, detail):
    """Journal append-only chaîné par SHA-256 (inaltérabilité vérifiable)."""
    prev = one("SELECT entry_hash FROM audit ORDER BY id DESC LIMIT 1")
    prev_hash = prev["entry_hash"] if prev else "GENESIS"
    e = {"ts": now_iso(), "actor": actor, "action": action, "target": str(target),
         "detail": detail, "prev_hash": prev_hash}
    e["entry_hash"] = hashlib.sha256(json.dumps(e, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    x("INSERT INTO audit(ts,actor,action,target,detail,prev_hash,entry_hash) VALUES(?,?,?,?,?,?,?)",
      (e["ts"], e["actor"], e["action"], e["target"], json.dumps(detail), prev_hash, e["entry_hash"]))
    return e["entry_hash"]