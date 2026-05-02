# =============================================================================
#  TECHDIALECT TRANSLATION ENGINE  v6.1
#  Multi-user · Admin approval · User-managed languages · PythonAnywhere ready
#  Single-file Flask app · SQLite · HuggingFace Inference API · Bootstrap 5
#
#  NEW IN v6.0:
#    - Contributor badge system (Seed → Bronze → Silver → Gold → Platinum → Legend)
#    - Shareable badge cards at /badge/<username>
#    - User-to-admin messaging with weekly export + auto-cleanup
#    - Admin message inbox (read/export/clear)
#    - Password change for users
#    - Top contributors leaderboard
#    - BUGFIX: HF_MODEL_URL was pointing to wrong endpoint (Llama instead of NLLB)
# =============================================================================
#
#  ╔══════════════════════════════════════════════════════════════════════════╗
#  ║                    PYTHONANYWHERE DEPLOYMENT GUIDE                       ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║                                                                          ║
#  ║  STEP 1 — Upload this file                                               ║
#  ║    Dashboard → Files → upload smart_translation_system.py               ║
#  ║    to /home/Silabs/                                                      ║
#  ║                                                                          ║
#  ║  STEP 2 — WSGI file (/var/www/silabs_pythonanywhere_com_wsgi.py)        ║
#  ║    Replace ALL content with:                                             ║
#  ║                                                                          ║
#  ║        import sys, os                                                    ║
#  ║        sys.path.insert(0, '/home/Silabs')                               ║
#  ║        os.environ['SECRET_KEY'] = 'your-long-random-secret'             ║
#  ║        os.environ['HF_TOKEN']   = 'hf_xxxxxxxxxxxxxxxxxxxx'             ║
#  ║        os.environ['DAILY_GOAL'] = '20'                                  ║
#  ║        from smart_translation_system import app as application           ║
#  ║                                                                          ║
#  ║  STEP 3 — Install dependencies (Bash console)                           ║
#  ║        pip install --user flask python-dotenv requests werkzeug          ║
#  ║                                                                          ║
#  ║  STEP 4 — Reload web app in Web tab                                     ║
#  ║                                                                          ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║  LOCAL (PyCharm): pip install flask python-dotenv requests werkzeug      ║
#  ║  Right-click → Run → http://127.0.0.1:5000                              ║
#  ║                                                                          ║
#  ║  .env file:  SECRET_KEY=x   HF_TOKEN=hf_xxx   DAILY_GOAL=20            ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║  ADMIN: Silabstechdialect / Techdialect@2024  (change after first login)║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║  BADGE CARDS:  /badge/<username>  (shareable, screenshottable)          ║
#  ║  MESSAGES:     /contact  (users → admin)                                ║
#  ║                /admin/messages  (admin inbox + export + clear)          ║
#  ╚══════════════════════════════════════════════════════════════════════════╝

import os, csv, io, sqlite3, difflib, datetime, textwrap, re, hashlib, base64
import time
from functools import wraps

from flask import (
    Flask, request, render_template_string, redirect, url_for,
    flash, Response, session, jsonify, g, send_from_directory
)
from dotenv import load_dotenv

try:
    import requests as http_requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    def generate_password_hash(pw):
        return hashlib.sha256(pw.encode()).hexdigest()
    def check_password_hash(hashed, pw):
        return hashed == hashlib.sha256(pw.encode()).hexdigest()

load_dotenv()

# =============================================================================
#  CONFIGURATION
# =============================================================================

SECRET_KEY           = os.getenv("SECRET_KEY", "techdialect-dev-key-change-in-prod")
HF_TOKEN             = os.getenv("HF_TOKEN")
DAILY_GOAL           = int(os.getenv("DAILY_GOAL", "20"))
SIMILARITY_THRESHOLD = 0.55
SHORT_QUERY_THRESHOLD = 0.72
MIN_FUZZY_QUERY_LEN   = 3
MAX_INPUT_CHARS      = 450
MAX_CHUNK_CHARS      = 400

# ── BUGFIX v6.0: was pointing to meta-llama/Llama-3.2-3B (wrong model/endpoint)
# ── Correct endpoint for NLLB-200 inference API:
HF_MODEL_URL = "https://api-inference.huggingface.co/models/facebook/nllb-200-distilled-600M"
SOURCE_LANG  = "eng_Latn"
HF_MAX_RETRIES = 2

DB_PATH        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "techdialect.db")
SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')
NON_WORD_RE    = re.compile(r"[^\w\s]", re.UNICODE)
MULTISPACE_RE  = re.compile(r"\s+")

DEFAULT_ADMIN_USERNAME = "Silabstechdialect"
DEFAULT_ADMIN_PASSWORD = "Techdialect@2024"

# ── Badge levels ──────────────────────────────────────────────────────────────
BADGE_LEVELS = [
    (1000, "legend",   "🏆", "Legend",    "#f59e0b", "#78350f"),
    ( 500, "platinum", "💎", "Platinum",  "#06b6d4", "#164e63"),
    ( 100, "gold",     "🥇", "Gold",      "#eab308", "#713f12"),
    (  50, "silver",   "🥈", "Silver",    "#94a3b8", "#1e293b"),
    (  10, "bronze",   "🥉", "Bronze",    "#c2914f", "#431407"),
    (   1, "seed",     "🌱", "Seed",      "#22c55e", "#14532d"),
]

def get_badge(count):
    """Return (slug, emoji, label, colour, dark) for a contribution count."""
    for threshold, slug, emoji, label, colour, dark in BADGE_LEVELS:
        if count >= threshold:
            return slug, emoji, label, colour, dark
    return "none", "—", "No badge yet", "#6b7280", "#111827"

def normalize_english_text(text):
    """Canonicalize English source text for matching/deduplication."""
    text = (text or "").strip().lower()
    text = NON_WORD_RE.sub(" ", text)
    text = MULTISPACE_RE.sub(" ", text)
    return text.strip()

CATEGORIES = [
    "Greetings & Farewells","Family & Relationships","Body & Health",
    "Food & Cooking","Clothing & Fashion","Housing & Community",
    "Travel & Direction","Marketplace & Trade","Money & Finance",
    "Time & Calendar","Numbers & Counting","Colors & Shapes",
    "Animals & Birds","Plants & Trees","Farming & Agriculture",
    "Weather & Seasons","Land & Geography","Water & Rivers",
    "Emotions & Feelings","Character & Values","Religion & Spirituality",
    "Proverbs & Idioms","Arts & Music","Sports & Games",
    "Celebrations & Culture","History & Heritage",
    "Government & Law","Education & School","Work & Occupation",
    "War & Conflict","Media & Communication",
    "Verbs & Actions","Adjectives & Descriptions",
    "Conjunctions & Prepositions","Sentence Starters",
    "Mathematics","Biology","Chemistry","Physics",
    "Computer Science","Engineering","Medicine & Anatomy",
    "Environment & Ecology","General",
]

# =============================================================================
#  FLASK APP
# =============================================================================

app = Flask(__name__)
app.secret_key = SECRET_KEY
DB_BOOTSTRAPPED = False

# =============================================================================
#  DATABASE
# =============================================================================

def get_db():
    global DB_BOOTSTRAPPED
    if not DB_BOOTSTRAPPED:
        try:
            init_db()
            DB_BOOTSTRAPPED = True
        except Exception as exc:
            # Keep error visible in logs but allow request cycle to raise naturally.
            print(f"[DB bootstrap error] {exc}")
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db: db.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT    NOT NULL UNIQUE,
        email         TEXT    NOT NULL UNIQUE,
        password_hash TEXT    NOT NULL,
        role          TEXT    NOT NULL DEFAULT 'user',
        approved      INTEGER NOT NULL DEFAULT 0,
        created_at    TEXT    NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS languages (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT    NOT NULL UNIQUE,
        nllb_code  TEXT,
        added_by   INTEGER,
        approved   INTEGER NOT NULL DEFAULT 0,
        created_at TEXT    NOT NULL,
        FOREIGN KEY (added_by) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS translations (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        english_text TEXT    NOT NULL,
        english_norm TEXT,
        local_text   TEXT    NOT NULL,
        target_lang  TEXT    NOT NULL,
        category     TEXT    NOT NULL DEFAULT 'General',
        source       TEXT    NOT NULL DEFAULT 'manual',
        quality_status TEXT  NOT NULL DEFAULT 'verified',
        confidence   REAL,
        verified_by  INTEGER,
        verified_at  TEXT,
        added_by     INTEGER,
        created_at   TEXT    NOT NULL,
        UNIQUE (english_text, target_lang),
        FOREIGN KEY (added_by) REFERENCES users(id),
        FOREIGN KEY (verified_by) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS daily_log (
        log_date TEXT PRIMARY KEY,
        count    INTEGER NOT NULL DEFAULT 0
    )""")

    # NEW v6.0 — messages table
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        subject    TEXT    NOT NULL,
        body       TEXT    NOT NULL,
        created_at TEXT    NOT NULL,
        read_at    TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # ── v6.1 migration: add profile_photo column if missing ─────────────
    try:
        c.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")
        conn.commit()
    except Exception:
        pass  # column already exists — safe to ignore

    # ── v6.2+ migrations: align older databases with new translation schema ──
    for sql in [
        "ALTER TABLE translations ADD COLUMN english_norm TEXT",
        "ALTER TABLE translations ADD COLUMN quality_status TEXT NOT NULL DEFAULT 'verified'",
        "ALTER TABLE translations ADD COLUMN confidence REAL",
        "ALTER TABLE translations ADD COLUMN verified_by INTEGER",
        "ALTER TABLE translations ADD COLUMN verified_at TEXT",
    ]:
        try:
            c.execute(sql)
            conn.commit()
        except Exception:
            pass  # column already exists — safe to ignore

    # Backfill normalized English text
    rows = conn.execute(
        "SELECT id, english_text FROM translations WHERE english_norm IS NULL OR english_norm=''"
    ).fetchall()
    for r in rows:
        norm = normalize_english_text(r["english_text"])
        conn.execute("UPDATE translations SET english_norm=? WHERE id=?", (norm, r["id"]))
    conn.commit()

    # Indexes
    for sql in [
        "CREATE INDEX IF NOT EXISTS idx_trans_lang     ON translations (target_lang)",
        "CREATE INDEX IF NOT EXISTS idx_trans_eng_lang ON translations (english_text, target_lang)",
        "CREATE INDEX IF NOT EXISTS idx_trans_norm_lang ON translations (english_norm, target_lang)",
        "CREATE INDEX IF NOT EXISTS idx_trans_category ON translations (category)",
        "CREATE INDEX IF NOT EXISTS idx_trans_user     ON translations (added_by)",
        "CREATE INDEX IF NOT EXISTS idx_lang_approved  ON languages    (approved)",
        "CREATE INDEX IF NOT EXISTS idx_users_approved ON users        (approved)",
        "CREATE INDEX IF NOT EXISTS idx_messages_user  ON messages     (user_id)",
        "CREATE INDEX IF NOT EXISTS idx_messages_read  ON messages     (read_at)",
    ]:
        c.execute(sql)

    conn.commit()

    # Seed admin
    if not conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone():
        conn.execute(
            "INSERT OR IGNORE INTO users (username,email,password_hash,role,approved,created_at) VALUES (?,?,?,'admin',1,?)",
            (DEFAULT_ADMIN_USERNAME,"admin@techdialect.com",
             generate_password_hash(DEFAULT_ADMIN_PASSWORD),
             datetime.datetime.utcnow().isoformat())
        )
        conn.commit()

    # Seed languages
    for name, code in [("Tiv","tiv_Latn"),("Yoruba","yor_Latn"),
                        ("Hausa","hau_Arab"),("Igbo","ibo_Latn"),("Nigerian Pidgin","pcm_Latn")]:
        c.execute("INSERT OR IGNORE INTO languages (name,nllb_code,added_by,approved,created_at) VALUES (?,?,NULL,1,?)",
                  (name, code, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

# ── DB helpers ────────────────────────────────────────────────────────────────

def db_approved_languages():
    return get_db().execute("SELECT * FROM languages WHERE approved=1 ORDER BY name").fetchall()

def db_all_languages():
    return get_db().execute(
        "SELECT l.*, u.username as proposer FROM languages l "
        "LEFT JOIN users u ON l.added_by=u.id ORDER BY l.approved DESC, l.name"
    ).fetchall()

def db_lang_names():
    return {r["name"] for r in db_approved_languages()}

def db_translations(lang=None, category=None, limit=None, added_by=None):
    wheres, params = [], []
    if lang:     wheres.append("target_lang=?"); params.append(lang)
    if category: wheres.append("category=?");    params.append(category)
    if added_by: wheres.append("added_by=?");    params.append(added_by)
    w = ("WHERE " + " AND ".join(wheres)) if wheres else ""
    l = f"LIMIT {int(limit)}" if limit else ""
    return get_db().execute(
        f"SELECT t.*, u.username as contributor FROM translations t "
        f"LEFT JOIN users u ON t.added_by=u.id {w} ORDER BY t.created_at DESC {l}", params
    ).fetchall()

def db_exact(english, lang):
    norm = normalize_english_text(english)
    return get_db().execute(
        "SELECT * FROM translations WHERE english_norm=? AND target_lang=?",
        (norm, lang)
    ).fetchone()

def db_insert(english, local, lang, category, source="manual", added_by=None, allow_update_pending=True):
    try:
        db = get_db()
        cleaned_english = english.strip()
        english_norm = normalize_english_text(cleaned_english)
        if not english_norm:
            return False
        # enforce canonical uniqueness (e.g., punctuation/case variants)
        exists = db.execute(
            "SELECT id FROM translations WHERE english_norm=? AND target_lang=? LIMIT 1",
            (english_norm, lang)
        ).fetchone()
        if exists:
            if allow_update_pending:
                existing = db.execute(
                    "SELECT id, local_text, quality_status FROM translations WHERE id=?",
                    (exists["id"],)
                ).fetchone()
                if existing and existing["local_text"] == "[PENDING]":
                    db.execute(
                        "UPDATE translations SET local_text=?, category=?, source=?, quality_status='verified', added_by=?, created_at=? WHERE id=?",
                        (local.strip(), category or "General", source, added_by, datetime.datetime.utcnow().isoformat(), exists["id"])
                    )
                    db.commit()
                    return True
            return False
        db.execute(
            "INSERT INTO translations (english_text,english_norm,local_text,target_lang,category,source,quality_status,added_by,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (cleaned_english,english_norm,local.strip(),lang,category or "General",source,
             "pending_review" if source in ("csv_seed", "csv_seed_admin") else "verified",
             added_by, datetime.datetime.utcnow().isoformat())
        )
        db.commit()
        today = datetime.date.today().isoformat()
        db.execute(
            "INSERT INTO daily_log (log_date,count) VALUES (?,1) ON CONFLICT(log_date) DO UPDATE SET count=count+1",
            (today,)
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def db_count(lang=None, category=None):
    wheres, params = [], []
    if lang:     wheres.append("target_lang=?"); params.append(lang)
    if category: wheres.append("category=?");    params.append(category)
    w = ("WHERE " + " AND ".join(wheres)) if wheres else ""
    return get_db().execute(f"SELECT COUNT(*) FROM translations {w}", params).fetchone()[0]

def db_lang_counts():
    rows = get_db().execute("SELECT target_lang, COUNT(*) as cnt FROM translations GROUP BY target_lang").fetchall()
    return {r["target_lang"]: r["cnt"] for r in rows}

def db_coverage(lang):
    rows = get_db().execute(
        "SELECT category, COUNT(*) as cnt FROM translations WHERE target_lang=? GROUP BY category", (lang,)
    ).fetchall()
    m = {r["category"]: r["cnt"] for r in rows}
    result = [{"category": c, "count": m.get(c, 0)} for c in CATEGORIES]
    result.sort(key=lambda x: x["count"])
    return result

def db_pending_translations(limit=200):
    return get_db().execute(
        "SELECT t.*, u.username as contributor FROM translations t "
        "LEFT JOIN users u ON t.added_by=u.id "
        "WHERE t.quality_status='pending_review' "
        "ORDER BY t.created_at DESC LIMIT ?",
        (int(limit),)
    ).fetchall()

def db_update_translation_review(tid, status, reviewer_id):
    db = get_db()
    if status == "verified":
        db.execute(
            "UPDATE translations SET quality_status='verified', verified_by=?, verified_at=? WHERE id=?",
            (reviewer_id, datetime.datetime.utcnow().isoformat(), tid)
        )
    elif status == "rejected":
        db.execute(
            "UPDATE translations SET quality_status='rejected', verified_by=?, verified_at=? WHERE id=?",
            (reviewer_id, datetime.datetime.utcnow().isoformat(), tid)
        )
    db.commit()

def db_user_contrib_count(uid):
    return get_db().execute(
        "SELECT COUNT(*) FROM translations WHERE added_by=?", (uid,)
    ).fetchone()[0]

def db_get_photo(uid):
    """Return base64 profile photo string for a user, or None."""
    row = get_db().execute("SELECT profile_photo FROM users WHERE id=?", (uid,)).fetchone()
    return row["profile_photo"] if row and row["profile_photo"] else None

def db_set_photo(uid, b64_str):
    db = get_db()
    db.execute("UPDATE users SET profile_photo=? WHERE id=?", (b64_str, uid))
    db.commit()

def db_leaderboard(limit=10):
    """Return leaderboard rows with badge data pre-computed for Jinja2."""
    rows = get_db().execute(
        "SELECT u.id, u.username, COUNT(t.id) as cnt "
        "FROM users u LEFT JOIN translations t ON t.added_by=u.id "
        "WHERE u.approved=1 "
        "GROUP BY u.id ORDER BY cnt DESC LIMIT ?", (limit,)
    ).fetchall()
    result = []
    for r in rows:
        slug, emoji, label, colour, dark = get_badge(r["cnt"])
        result.append({
            "id":           r["id"],
            "username":     r["username"],
            "cnt":          r["cnt"],
            "badge_slug":   slug,
            "badge_emoji":  emoji,
            "badge_label":  label,
            "badge_colour": colour,
        })
    return result

# ── Daily stats ───────────────────────────────────────────────────────────────

def today_count():
    today = datetime.date.today().isoformat()
    row   = get_db().execute("SELECT count FROM daily_log WHERE log_date=?", (today,)).fetchone()
    return row["count"] if row else 0

def get_streak():
    rows = get_db().execute("SELECT log_date FROM daily_log WHERE count>0 ORDER BY log_date DESC").fetchall()
    if not rows: return 0
    dates = [datetime.date.fromisoformat(r["log_date"]) for r in rows]
    today = datetime.date.today()
    if dates[0] < today - datetime.timedelta(days=1): return 0
    streak, check = 0, today
    for d in dates:
        if d >= check - datetime.timedelta(days=1):
            streak += 1; check = d - datetime.timedelta(days=1)
        else: break
    return streak

def total_days():
    return get_db().execute("SELECT COUNT(*) FROM daily_log WHERE count>0").fetchone()[0]

# ── Message helpers ───────────────────────────────────────────────────────────

def db_send_message(user_id, subject, body):
    db = get_db()
    db.execute(
        "INSERT INTO messages (user_id,subject,body,created_at) VALUES (?,?,?,?)",
        (user_id, subject.strip(), body.strip(), datetime.datetime.utcnow().isoformat())
    )
    db.commit()

def db_get_messages(unread_only=False):
    q = "SELECT m.*, u.username FROM messages m LEFT JOIN users u ON m.user_id=u.id "
    q += "WHERE m.read_at IS NULL " if unread_only else ""
    q += "ORDER BY m.created_at DESC"
    return get_db().execute(q).fetchall()

def db_mark_read(msg_id):
    db = get_db()
    db.execute("UPDATE messages SET read_at=? WHERE id=?",
               (datetime.datetime.utcnow().isoformat(), msg_id))
    db.commit()

def db_mark_all_read():
    db = get_db()
    db.execute("UPDATE messages SET read_at=? WHERE read_at IS NULL",
               (datetime.datetime.utcnow().isoformat(),))
    db.commit()

def db_delete_old_messages(days=7):
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
    db = get_db()
    n = db.execute("SELECT COUNT(*) FROM messages WHERE created_at < ?", (cutoff,)).fetchone()[0]
    db.execute("DELETE FROM messages WHERE created_at < ?", (cutoff,))
    db.commit()
    return n

def db_unread_count():
    return get_db().execute("SELECT COUNT(*) FROM messages WHERE read_at IS NULL").fetchone()[0]

# =============================================================================
#  AUTH HELPERS
# =============================================================================

def get_user(uid): return get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
def get_user_by_name(u): return get_db().execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
def get_pending_users(): return get_db().execute("SELECT * FROM users WHERE approved=0 AND role='user' ORDER BY created_at DESC").fetchall()
def get_all_users(): return get_db().execute("SELECT * FROM users ORDER BY approved DESC, created_at DESC").fetchall()
def current_user(): uid = session.get("user_id"); return get_user(uid) if uid else None

def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not session.get("user_id"):
            flash("Please log in.", "warning"); return redirect(url_for("login"))
        u = current_user()
        if not u or not u["approved"]:
            session.clear(); flash("Account pending approval.", "warning"); return redirect(url_for("login"))
        return f(*a, **kw)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a, **kw):
        u = current_user()
        if not u or u["role"] != "admin":
            flash("Admin access required.", "danger"); return redirect(url_for("dashboard"))
        return f(*a, **kw)
    return dec

# =============================================================================
#  TRANSLATION ENGINE
# =============================================================================

def find_fuzzy(english, lang):
    q_norm = normalize_english_text(english)
    if len(q_norm) < MIN_FUZZY_QUERY_LEN:
        return None, 0.0, []
    rows = db_fuzzy_candidates(q_norm, lang)
    if not rows: return None, 0.0, []
    best_row, best_score = None, 0.0
    scored = []
    q_tokens = set(q_norm.split())
    for row in rows:
        target_norm = normalize_english_text(row["english_text"])
        seq_score = difflib.SequenceMatcher(None, q_norm, target_norm).ratio()
        t_tokens = set(target_norm.split())
        token_score = (len(q_tokens & t_tokens) / len(q_tokens | t_tokens)) if (q_tokens or t_tokens) else 0.0
        score = max(seq_score, (0.65 * seq_score + 0.35 * token_score))
        scored.append((row, score))
        if score > best_score:
            best_score = score
            best_row = row
    threshold = SHORT_QUERY_THRESHOLD if len(q_norm) <= 5 else SIMILARITY_THRESHOLD
    scored.sort(key=lambda x: x[1], reverse=True)
    suggestions = [
        {"english": r["english_text"], "local": r["local_text"], "category": r["category"], "score": s}
        for r, s in scored[:3]
    ]
    return ((best_row, best_score, suggestions) if best_score >= threshold else (None, best_score, suggestions))

def db_fuzzy_candidates(english_norm, lang, limit=250):
    db = get_db()
    first_token = english_norm.split()[0] if english_norm else ""
    prefix = english_norm[:4]
    rows = db.execute(
        "SELECT * FROM translations WHERE target_lang=? AND (english_norm LIKE ? OR english_norm LIKE ?) LIMIT ?",
        (lang, f"{first_token}%", f"{prefix}%", int(limit))
    ).fetchall()
    if rows:
        return rows
    return db.execute(
        "SELECT * FROM translations WHERE target_lang=? ORDER BY created_at DESC LIMIT ?",
        (lang, min(int(limit), 120))
    ).fetchall()

def get_nllb_code(lang):
    row = get_db().execute("SELECT nllb_code FROM languages WHERE name=? AND approved=1", (lang,)).fetchone()
    return row["nllb_code"] if row and row["nllb_code"] else None

def parse_hf_generated_text(data):
    """Extract generated translation text from HuggingFace response payload."""
    if isinstance(data, list) and data:
        text = (data[0].get("generated_text") or "").strip()
        return text or None
    if isinstance(data, dict):
        text = (data.get("generated_text") or "").strip()
        return text or None
    return None

def call_hf_api_detailed(english, lang):
    if not HF_TOKEN or not REQUESTS_AVAILABLE:
        return {"ok": False, "error": "hf_unavailable", "translation": None}
    nllb_code = get_nllb_code(lang)
    if not nllb_code: return {"ok": False, "error": "nllb_code_missing", "translation": None}
    safe = textwrap.shorten(english.strip(), width=MAX_INPUT_CHARS, placeholder="…")
    if not safe:
        return {"ok": False, "error": "empty_input", "translation": None}
    examples = get_db().execute(
        "SELECT english_text,local_text FROM translations WHERE target_lang=? ORDER BY RANDOM() LIMIT 5", (lang,)
    ).fetchall()
    ex_block = "".join(f"English: {e['english_text']}\n{lang}: {e['local_text']}\n\n" for e in examples)
    prompt = (
        f"Translate the following English text to {lang} ({nllb_code}).\n"
        "Return only the translated text. Do not add labels, notes, or explanations.\n\n"
        f"{ex_block}English: {safe}"
    )
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 150, "temperature": 0.2, "do_sample": False}}
    for attempt in range(HF_MAX_RETRIES + 1):
        start = time.time()
        try:
            r = http_requests.post(
                HF_MODEL_URL,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json=payload,
                timeout=30
            )
            latency_ms = int((time.time() - start) * 1000)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < HF_MAX_RETRIES:
                time.sleep(0.6 * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            translation = parse_hf_generated_text(data)
            if translation:
                return {"ok": True, "error": None, "translation": translation, "latency_ms": latency_ms}
            return {"ok": False, "error": "empty_model_output", "translation": None, "latency_ms": latency_ms}
        except Exception as exc:
            if attempt < HF_MAX_RETRIES:
                time.sleep(0.6 * (attempt + 1))
                continue
            print(f"  HF API error ({lang}): {exc}")
            return {"ok": False, "error": "request_failed", "translation": None}
    return {"ok": False, "error": "request_failed", "translation": None}

def call_hf_api(english, lang):
    result = call_hf_api_detailed(english, lang)
    if not isinstance(result, dict):
        return None
    return result.get("translation")

def translate(english, lang):
    english = english.strip()
    if not english: return {"status":"error","message":"Please enter some text."}
    if lang not in db_lang_names(): return {"status":"error","message":f"Unknown language: {lang}"}
    row = db_exact(english, lang)
    if row: return {"status":"exact","source":"Database (exact match)","english":row["english_text"],"local":row["local_text"],"lang":lang,"category":row["category"],"saved":True}
    fuzzy_row, score, suggestions = find_fuzzy(english, lang)
    if fuzzy_row: return {"status":"fuzzy","source":f"Database (fuzzy — {score:.0%} similar)","english":fuzzy_row["english_text"],"local":fuzzy_row["local_text"],"lang":lang,"category":fuzzy_row["category"],"score":score,"saved":True,"original_query":english,"suggestions":suggestions}
    ai_text = call_hf_api(english, lang)
    if ai_text: return {"status":"ai","source":f"AI (HuggingFace → {lang})","english":english,"local":ai_text,"lang":lang,"category":"General","saved":False}
    hint = "" if HF_TOKEN else " (set HF_TOKEN to enable AI)"
    return {"status":"not_found","source":"Not found","english":english,"local":"","lang":lang,"saved":False,"message":f"No {lang} translation found{hint}. Add it manually below."}

def split_chunks(text):
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) <= MAX_CHUNK_CHARS: chunks.append(para); continue
        sentences = SENTENCE_SPLIT.split(para)
        current = ""
        for sent in sentences:
            sent = sent.strip()
            if not sent: continue
            if len(current) + len(sent) + 1 <= MAX_CHUNK_CHARS:
                current = (current + " " + sent).strip()
            else:
                if current: chunks.append(current)
                if len(sent) > MAX_CHUNK_CHARS: sent = textwrap.shorten(sent, width=MAX_CHUNK_CHARS, placeholder="…")
                current = sent
        if current: chunks.append(current)
    return [c for c in chunks if c.strip()]

def translate_article(text, lang):
    text = text.strip()
    if not text: return {"status":"error","message":"No text provided."}
    if lang not in db_lang_names(): return {"status":"error","message":f"Unknown language: {lang}"}
    if not HF_TOKEN: return {"status":"no_ai","message":"HF_TOKEN not set. Article translation requires AI."}
    chunks = split_chunks(text)
    results, parts = [], []
    success_count, fail_count = 0, 0
    total_latency = 0
    for i, chunk in enumerate(chunks):
        db_row = db_exact(chunk, lang)
        if db_row:
            local = db_row["local_text"]
            src = "db"
            chunk_status = "from_db"
            success_count += 1
        else:
            ai_result = call_hf_api_detailed(chunk, lang)
            local = (ai_result or {}).get("translation") or ""
            src = "ai"
            chunk_status = "translated" if local else f"failed_{(ai_result or {}).get('error', 'unknown')}"
            if local:
                success_count += 1
                total_latency += int((ai_result or {}).get("latency_ms") or 0)
            else:
                fail_count += 1
        results.append({"index":i,"english":chunk,"local":local,"source":src,"status":chunk_status})
        parts.append(local if local else "[translation unavailable]")
    avg_latency = int(total_latency / success_count) if success_count else 0
    return {
        "status":"ok","lang":lang,"chunks":results,"total_chunks":len(results),
        "success_count":success_count,"fail_count":fail_count,"avg_latency_ms":avg_latency,
        "full_translation":"\n\n".join(parts)
    }

# =============================================================================
#  HTML TEMPLATES
# =============================================================================

AUTH_HTML = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Techdialect — {{ page_title }}</title>
<meta name="description" content="Nigerian Language Dataset Engine — Building the future of local language technology.">
<meta property="og:title" content="Techdialect">
<meta property="og:description" content="Translating English into Nigerian languages using AI while building community-powered datasets.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://silabs.pythonanywhere.com">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#e85d04">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
<style>
body{background:linear-gradient(135deg,#1a1a2e,#16213e);min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:'Segoe UI',system-ui,sans-serif;}
.auth-card{background:#fff;border-radius:1.2rem;padding:2.5rem 2rem;box-shadow:0 8px 40px rgba(0,0,0,.35);width:100%;max-width:420px;}
.brand{font-size:1.5rem;font-weight:900;color:#1a1a2e;}.brand span{color:#e85d04;}
.sub{font-size:.78rem;color:#6c757d;margin-bottom:1.5rem;}
.btn-primary{background:linear-gradient(135deg,#e85d04,#f48c06);border:none;font-weight:700;}
.form-label{font-weight:600;font-size:.88rem;}
</style></head><body>
<div class="auth-card">
  <div class="text-center mb-4">
    <div class="brand"><i class="bi bi-translate me-2"></i>Tech<span>dialect</span></div>
    <div class="sub">Nigerian Language Dataset Engine</div>
  </div>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}<div class="alert alert-{{ cat }} py-2 small">{{ msg }}</div>{% endfor %}
  {% endwith %}
  {{ form_html | safe }}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>"""

# ── BADGE CARD TEMPLATE ───────────────────────────────────────────────────────
BADGE_HTML = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{{ username }} — Techdialect Badge</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body { background:#0a0f1e; display:flex; align-items:center; justify-content:center;
         min-height:100vh; font-family:'Segoe UI',system-ui,sans-serif; margin:0; }
  .badge-card {
    width:480px; background:linear-gradient(135deg,#0d1b2a,#0a0f1e);
    border-radius:1.4rem; padding:2.5rem 2rem; text-align:center;
    border:2px solid {{ badge_colour }};
    box-shadow:0 0 40px {{ badge_colour }}55, 0 4px 30px rgba(0,0,0,.5);
  }
  .brand { font-size:1rem; font-weight:800; color:#fff; letter-spacing:.08em; }
  .brand span { color:#e85d04; }
  .motto { font-size:.72rem; color:#6b7280; letter-spacing:.1em; margin-bottom:1.5rem; }
  .badge-emoji { font-size:4.5rem; line-height:1; margin:1rem 0 .5rem; }
  .badge-level { font-size:1.6rem; font-weight:900; color:{{ badge_colour }}; margin-bottom:.25rem; }
  .badge-name  { font-size:1.1rem; font-weight:700; color:#fff; margin-bottom:.15rem; }
  .badge-count { font-size:.9rem; color:#9ca3af; margin-bottom:1.5rem; }
  .lang-grid { display:flex; flex-wrap:wrap; gap:.4rem; justify-content:center; margin-bottom:1.5rem; }
  .lang-pill { background:{{ badge_colour }}22; border:1px solid {{ badge_colour }}88;
               color:{{ badge_colour }}; border-radius:2rem; padding:.2rem .7rem; font-size:.75rem; font-weight:600; }
  .url { font-size:.75rem; color:#4b5563; margin-top:1rem; }
  .url a { color:#e85d04; text-decoration:none; }
  hr { border-color:#1f2937; margin:1.2rem 0; }
  .next-badge { font-size:.78rem; color:#6b7280; margin-top:.5rem; }
  .next-badge span { color:{{ next_colour }}; font-weight:600; }
</style>
</head><body>
<div class="badge-card">
  <div class="brand">TECH<span>DIALECT</span></div>
  <div class="motto">TECHNOLOGIA OMNIBUS</div>
  {% if user_photo %}
  <div style="margin:1rem 0 .5rem">
    <img src="data:image/jpeg;base64,{{ user_photo }}"
         style="width:90px;height:90px;border-radius:50%;object-fit:cover;
                border:4px solid {{ badge_colour }};
                box-shadow:0 0 20px {{ badge_colour }}66">
  </div>
  {% else %}
  <div class="badge-emoji">{{ badge_emoji }}</div>
  {% endif %}
  <div class="badge-level">{{ badge_label }} Contributor</div>
  <div class="badge-name">{{ username }}</div>
  <div class="badge-count">{{ contrib_count }} translation{{ 's' if contrib_count != 1 else '' }} contributed</div>
  <hr/>
  {% if lang_breakdown %}
  <div class="lang-grid">
    {% for lang, cnt in lang_breakdown %}<span class="lang-pill">{{ lang }}: {{ cnt }}</span>{% endfor %}
  </div>
  {% endif %}
  <div class="url">
    <a href="https://silabs.pythonanywhere.com">silabs.pythonanywhere.com</a>
  </div>
  <div style="margin-top:.6rem">
    <a href="/badge/{{ username }}/download"
       style="display:inline-block;background:{{ badge_colour }};color:#fff;
              text-decoration:none;padding:.3rem 1rem;border-radius:2rem;
              font-size:.75rem;font-weight:700;">
      ⬇ Download PNG Badge
    </a>
  </div>
  {% if next_label %}
  <div class="next-badge">Next: <span>{{ next_emoji }} {{ next_label }}</span> at {{ next_at }} contributions</div>
  {% endif %}
</div>
</body></html>"""

# ── MAIN TEMPLATE ──────────────────────────────────────────────────────────────
MAIN_HTML = r"""
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Techdialect · {{ selected_lang }}</title>
<meta name="description" content="Nigerian Language Dataset Engine — Building the future of local language technology.">
<meta property="og:title" content="Techdialect">
<meta property="og:description" content="Translating English into Nigerian languages using AI while building community-powered datasets.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://silabs.pythonanywhere.com">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#e85d04">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
<style>
:root{--td:#e85d04;--primary:#0d6efd;--bg:#f5f7ff;--radius:.9rem;}
body{background:var(--bg);font-family:'Segoe UI',system-ui,sans-serif;font-size:.95rem;}
.navbar{background:linear-gradient(135deg,#1a1a2e,#16213e)!important;}
.brand-main{font-weight:800;font-size:1.15rem;color:#fff;}.brand-main span{color:#e85d04;}
.brand-sub{font-size:.68rem;color:#adb5bd;}
.chip{background:#fff;border:1px solid #dee2e6;border-radius:2rem;padding:.26rem .8rem;font-size:.78rem;font-weight:600;display:inline-flex;align-items:center;gap:.3rem;}
.chip.streak{border-color:#f48c06;color:#e85d04;}.chip.goal{border-color:#0d6efd;color:#0d6efd;}.chip.total{border-color:#198754;color:#198754;}
.goal-bar-wrap{background:#e9ecef;border-radius:2rem;height:9px;overflow:hidden;}
.goal-bar{height:100%;border-radius:2rem;background:linear-gradient(90deg,#0d6efd,#20c997);transition:width .4s;}
.goal-bar.done{background:linear-gradient(90deg,#198754,#20c997);}
.card{border:none;border-radius:var(--radius);box-shadow:0 2px 14px rgba(0,0,0,.07);}
.card-header{border-radius:var(--radius) var(--radius) 0 0!important;font-weight:600;font-size:.9rem;}
.lang-pill{padding:.26rem .8rem;border-radius:2rem;font-size:.78rem;font-weight:600;text-decoration:none;border:2px solid transparent;transition:all .16s;display:inline-flex;align-items:center;gap:.3rem;}
.lang-pill.active{background:var(--td);color:#fff;border-color:var(--td);}
.lang-pill.inactive{background:#fff;color:#495057;border-color:#dee2e6;}
.lang-pill.inactive:hover{border-color:var(--td);color:var(--td);}
.quick-entry{background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:var(--radius);padding:1.3rem;}
.quick-entry .form-control,.quick-entry .form-select{background:#2a2a4a;border:1px solid #3a3a5c;color:#fff;border-radius:.5rem;}
.quick-entry .form-control::placeholder{color:#adb5bd;}
.quick-entry .form-control:focus,.quick-entry .form-select:focus{background:#2a2a4a;border-color:#e85d04;color:#fff;box-shadow:0 0 0 3px rgba(232,93,4,.2);}
.quick-entry .form-select option{background:#2a2a4a;color:#fff;}
.quick-entry label{color:#adb5bd;font-size:.76rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;}
.save-btn{background:linear-gradient(135deg,var(--td),#f48c06);border:none;color:#fff;font-weight:700;padding:.55rem 1.4rem;border-radius:.5rem;}
.save-btn:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(232,93,4,.4);color:#fff;}
.ai-hint{background:#2a2a4a;border:1px solid #3a3a5c;border-radius:.5rem;padding:.4rem .7rem;font-size:.82rem;margin-top:.28rem;min-height:32px;display:flex;align-items:center;gap:.5rem;}
.ai-hint-text{color:#fff;font-weight:600;cursor:pointer;}.ai-hint-text:hover{color:#f48c06;}
.result-box{border-radius:.75rem;padding:1rem 1.3rem;margin-top:.7rem;border-left:4px solid var(--primary);background:linear-gradient(135deg,#e8f4fd,#f0fff4);}
.result-box.ai{border-color:#6f42c1;background:linear-gradient(135deg,#f3e8ff,#fdf0ff);}
.result-box.fuzzy{border-color:#0d6efd;}.result-box.notfound{border-color:#dc3545;background:#fff5f5;}
.result-local{font-size:1.45rem;font-weight:800;color:#1a1a2e;line-height:1.3;}
.article-section{background:#fff;border-radius:var(--radius);box-shadow:0 2px 14px rgba(0,0,0,.07);margin-bottom:2rem;}
.article-header{background:linear-gradient(135deg,#6f42c1,#0d6efd);color:#fff;padding:.9rem 1.3rem;border-radius:var(--radius) var(--radius) 0 0;font-weight:700;font-size:.95rem;display:flex;align-items:center;gap:.5rem;}
.article-pane{min-height:220px;resize:vertical;font-size:.9rem;line-height:1.7;border:2px solid #dee2e6;border-radius:.6rem;padding:.8rem;width:100%;}
.article-pane:focus{border-color:#6f42c1;outline:none;box-shadow:0 0 0 3px rgba(111,66,193,.18);}
.chunk-row{border-bottom:1px solid #f0f0f0;padding:.8rem 0;}.chunk-row:last-child{border-bottom:none;}
.chunk-en{color:#495057;font-size:.87rem;line-height:1.6;}.chunk-tiv{color:#1a1a2e;font-weight:600;font-size:.93rem;line-height:1.6;}
.badge-ai{background:#6f42c1;color:#fff;font-size:.67rem;padding:.1rem .42rem;border-radius:.3rem;}
.badge-db{background:#198754;color:#fff;font-size:.67rem;padding:.1rem .42rem;border-radius:.3rem;}
.progress-art{height:7px;border-radius:2rem;background:#e9ecef;overflow:hidden;margin:.6rem 0;}
.progress-art-bar{height:100%;border-radius:2rem;width:0%;background:linear-gradient(90deg,#6f42c1,#0d6efd);transition:width .3s;}
.art-btn{background:linear-gradient(135deg,#6f42c1,#0d6efd);border:none;color:#fff;font-weight:700;padding:.55rem 1.5rem;border-radius:.5rem;}
.art-btn:hover{opacity:.9;color:#fff;}.art-btn:disabled{opacity:.55;cursor:not-allowed;}
.cov-table th,.tbl th{font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;}
.cov-table td,.tbl td{vertical-align:middle!important;font-size:.8rem;}
.export-btn{background:linear-gradient(135deg,#198754,#20c997);border:none;color:#fff;font-weight:700;padding:.5rem 1.3rem;border-radius:2rem;text-decoration:none;display:inline-block;font-size:.87rem;}
.export-btn:hover{opacity:.9;color:#fff;}
.big-num{font-size:2.2rem;font-weight:900;line-height:1;}
.nav-tabs .nav-link{font-size:.83rem;font-weight:600;color:#6c757d;}
.nav-tabs .nav-link.active{color:#1a1a2e;}
/* Badge pill in navbar */
.user-badge{border-radius:2rem;padding:.22rem .65rem;font-size:.72rem;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;gap:.25rem;}
/* Leaderboard */
.lb-row{display:flex;align-items:center;gap:.75rem;padding:.5rem .75rem;border-radius:.5rem;}
.lb-row:nth-child(odd){background:rgba(255,255,255,.04);}
.lb-rank{font-size:.85rem;font-weight:800;width:22px;text-align:center;}
@media(max-width:576px){.result-local{font-size:1.1rem;}.big-num{font-size:1.6rem;}}
</style></head><body>

<nav class="navbar navbar-dark shadow-sm py-2">
  <div class="container-lg">
    <div><div class="brand-main"><i class="bi bi-translate me-2"></i>Tech<span>dialect</span></div>
    <div class="brand-sub">NIGERIAN LANGUAGE DATASET ENGINE</div></div>
    <div class="d-flex align-items-center gap-2 flex-wrap mt-1 mt-sm-0">
      {% if streak > 0 %}<span class="chip streak"><i class="bi bi-fire"></i>{{ streak }}d</span>{% endif %}
      <span class="chip goal"><i class="bi bi-bullseye"></i>{{ today_c }}/{{ daily_goal }}</span>
      <span class="chip total"><i class="bi bi-database-fill"></i>{{ total_count }}</span>
      {% if ai_active %}<span class="chip"><i class="bi bi-cpu text-success"></i>AI on</span>
      {% else %}<span class="chip"><i class="bi bi-cpu text-danger"></i>DB only</span>{% endif %}
      {% if user.role == 'admin' %}
        <a href="{{ url_for('admin_panel') }}" class="chip text-decoration-none text-warning">
          <i class="bi bi-shield-lock"></i>Admin
          {% if unread_msgs > 0 %}<span class="badge bg-danger" style="font-size:.6rem">{{ unread_msgs }}</span>{% endif %}
        </a>
      {% endif %}
      <!-- User badge -->
      <a href="{{ url_for('badge_card', username=user.username) }}" target="_blank"
         class="user-badge text-decoration-none d-flex align-items-center gap-1"
         style="background:{{ badge_colour }}22;border:1px solid {{ badge_colour }}88;color:{{ badge_colour }}">
        {% if user_photo %}<img src="data:image/jpeg;base64,{{ user_photo }}"
             style="width:22px;height:22px;border-radius:50%;object-fit:cover;border:1px solid {{ badge_colour }}">
        {% else %}{{ badge_emoji }}{% endif %}
        {{ badge_label }}
      </a>
      <a href="{{ url_for('propose_language') }}" class="chip text-decoration-none text-primary">
        <i class="bi bi-plus-circle"></i>Add Language
      </a>
      <a href="{{ url_for('contact') }}" class="chip text-decoration-none text-info">
        <i class="bi bi-envelope"></i>Contact
      </a>
      <a href="{{ url_for('logout') }}" class="chip text-decoration-none text-danger">
        <i class="bi bi-box-arrow-right"></i>{{ user.username }}
      </a>
    </div>
  </div>
</nav>

<div class="container-lg mt-2">
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for cat, msg in messages %}
    <div class="alert alert-{{ cat }} alert-dismissible fade show py-2 small">{{ msg }}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>
  {% endfor %}
{% endwith %}
</div>

<div class="container-lg mt-2 mb-3">
  <div class="d-flex align-items-center gap-3">
    <div class="flex-grow-1">
      <div class="d-flex justify-content-between mb-1">
        <small class="fw-semibold text-muted">Today <span class="text-primary fw-bold">{{ today_c }}</span> / {{ daily_goal }} terms</small>
        <small class="text-muted">{{ t_days }} days active · {{ total_count }} total</small>
      </div>
      <div class="goal-bar-wrap">
        {% set pct = [today_c * 100 // daily_goal, 100] | min %}
        <div class="goal-bar {{ 'done' if today_c >= daily_goal else '' }}" style="width:{{ pct }}%"></div>
      </div>
    </div>
    {% if today_c >= daily_goal %}<span class="badge bg-success">Goal hit!</span>{% endif %}
  </div>
</div>

<div class="container-lg mb-3">
  <div class="d-flex align-items-center gap-2 flex-wrap">
    <small class="text-muted fw-semibold me-1"><i class="bi bi-globe2 me-1"></i>Language:</small>
    {% for lang in languages %}
      <a href="/?lang={{ lang.name | urlencode }}"
         class="lang-pill {{ 'active' if lang.name == selected_lang else 'inactive' }}">
        {{ lang.name }} <span style="opacity:.7;font-weight:400">({{ lang_counts.get(lang.name, 0) }})</span>
      </a>
    {% endfor %}
  </div>
</div>

<div class="container-lg pb-4">
  <div class="row g-4">
    <div class="col-lg-7">

      <div class="quick-entry mb-4">
        <div class="d-flex align-items-center justify-content-between mb-3">
          <h6 class="text-white mb-0 fw-bold"><i class="bi bi-lightning-charge-fill text-warning me-2"></i>Quick Entry
          <small class="text-muted fw-normal ms-2">add {{ selected_lang }} terms fast</small></h6>
          <small class="text-muted"><kbd class="bg-dark text-white">Ctrl+Enter</kbd></small>
        </div>
        <form method="POST" action="/add" id="quickForm">
          <input type="hidden" name="target_lang" value="{{ selected_lang }}">
          <div class="row g-2">
            <div class="col-md-4"><label>English Term</label>
              <input type="text" name="english_text" id="engInput" class="form-control" placeholder="e.g. photosynthesis" autocomplete="off" required></div>
            <div class="col-md-4"><label>{{ selected_lang }} Translation</label>
              <input type="text" name="local_text" id="localInput" class="form-control" placeholder="Translation…" autocomplete="off" required>
              <div class="ai-hint d-none" id="aiHintBox">
                <i class="bi bi-cpu text-info"></i>
                <span class="text-muted me-1" style="font-size:.74rem">AI:</span>
                <span class="ai-hint-text" id="aiHintText" onclick="useHint()"></span>
                <span class="text-muted ms-auto" style="font-size:.7rem">click to use</span>
              </div></div>
            <div class="col-md-3"><label>Category</label>
              <select name="category" id="catSelect" class="form-select">
                {% for cat in categories %}<option value="{{ cat }}" {{ 'selected' if cat == last_cat else '' }}>{{ cat }}</option>{% endfor %}
              </select></div>
            <div class="col-md-1 d-flex align-items-end">
              <button type="submit" class="save-btn w-100"><i class="bi bi-plus-lg"></i></button></div>
          </div>
        </form>
      </div>

      <div class="card mb-4">
        <div class="card-header bg-primary text-white"><i class="bi bi-search me-2"></i>Look Up / Translate — English → {{ selected_lang }}</div>
        <div class="card-body">
          <form method="POST" action="/translate">
            <input type="hidden" name="target_lang" value="{{ selected_lang }}">
            <div class="input-group">
              <input type="text" name="english_text" class="form-control" placeholder="Type English to search or translate…" value="{{ last_query }}" maxlength="{{ max_chars }}" required>
              <button type="submit" class="btn btn-primary"><i class="bi bi-arrow-right-circle me-1"></i>Translate</button>
            </div>
          </form>
          {% if result %}{% set r = result %}
          <div class="result-box {{ r.status if r.status in ['ai','fuzzy','not_found'] else '' }}">
            <div class="mb-2">
              {% if r.status=='exact' %}<span class="badge bg-success">{{ r.source }}</span>
              {% elif r.status=='fuzzy' %}<span class="badge bg-primary">{{ r.source }}</span>
              {% elif r.status=='ai' %}<span class="badge text-white" style="background:#6f42c1">{{ r.source }}</span>
              {% else %}<span class="badge bg-danger">{{ r.source }}</span>{% endif %}
            </div>
            {% if r.status in ['error','not_found'] %}<p class="text-danger mb-2 small">{{ r.get('message','') }}</p>
              {% if r.status=='not_found' %}
              <a href="#quickForm" class="btn btn-sm btn-outline-primary"><i class="bi bi-plus-circle me-1"></i>Add this translation now</a>
              {% endif %}
            {% else %}
              {% if r.status=='fuzzy' and r.get('original_query') %}<small class="text-muted d-block mb-1">You searched: "<em>{{ r.original_query }}</em>" → closest:</small>{% endif %}
              <div class="text-muted small mb-1"><strong>English:</strong> {{ r.english }}</div>
              <div class="result-local mb-1">{{ r.local }}</div>
              <small class="text-muted"><i class="bi bi-tag me-1"></i>{{ r.category or 'General' }}</small>
              {% if not r.saved %}
              <hr class="my-2"/>
              <p class="small text-muted mb-2"><i class="bi bi-info-circle me-1"></i>AI result — save to improve future lookups.</p>
              <form method="POST" action="/save" class="row g-2 align-items-end">
                <input type="hidden" name="english_text" value="{{ r.english }}">
                <input type="hidden" name="local_text" value="{{ r.local }}">
                <input type="hidden" name="target_lang" value="{{ r.lang }}">
                <div class="col-sm-5"><select name="category" class="form-select form-select-sm">{% for cat in categories %}<option>{{ cat }}</option>{% endfor %}</select></div>
                <div class="col-sm-4"><button type="submit" class="btn btn-success btn-sm w-100"><i class="bi bi-cloud-upload me-1"></i>Save</button></div>
              </form>{% endif %}
            {% endif %}
          </div>{% endif %}
        </div>
      </div>

      <div class="card">
        <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
          <span><i class="bi bi-clock-history me-2"></i>Recent {{ selected_lang }} Entries</span>
          <span class="badge bg-secondary">{{ lang_counts.get(selected_lang, 0) }} total</span>
        </div>
        <div class="card-body p-0">
          {% if recent_entries %}
          <div class="table-responsive" style="max-height:340px;overflow-y:auto;">
            <table class="table table-sm table-hover tbl mb-0">
              <thead class="table-light sticky-top"><tr><th>English</th><th>{{ selected_lang }}</th><th>Category</th><th>By</th></tr></thead>
              <tbody>{% for t in recent_entries %}
                <tr><td>{{ t.english_text }}</td><td class="fw-semibold text-primary">{{ t.local_text }}</td>
                <td><span class="badge bg-light text-dark border" style="font-size:.68rem">{{ t.category }}</span></td>
                <td class="text-muted" style="font-size:.78rem">{{ t.contributor or '—' }}</td></tr>
              {% endfor %}</tbody>
            </table>
          </div>
          {% else %}
          <div class="text-center py-4 text-muted"><i class="bi bi-database-slash fs-2 d-block mb-2"></i>No {{ selected_lang }} entries yet — use Quick Entry above!</div>
          {% endif %}
        </div>
      </div>
    </div>

    <div class="col-lg-5">
      <div class="card mb-4">
        <div class="card-header" style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;"><i class="bi bi-calendar3 me-2"></i>Today · {{ today_date }}</div>
        <div class="card-body">
          <div class="row text-center g-2">
            <div class="col-4"><div class="big-num text-primary">{{ today_c }}</div><small class="text-muted">Added today</small></div>
            <div class="col-4"><div class="big-num text-success">{{ daily_goal }}</div><small class="text-muted">Daily goal</small></div>
            <div class="col-4"><div class="big-num" style="color:var(--td)">{{ streak }}</div><small class="text-muted">Day streak</small></div>
          </div>
          <div class="goal-bar-wrap mt-3">
            {% set pct = [today_c * 100 // daily_goal, 100] | min %}
            <div class="goal-bar {{ 'done' if today_c >= daily_goal else '' }}" style="width:{{ pct }}%"></div>
          </div>
          <div class="text-center mt-2"><small class="text-muted">
            {% set rem = daily_goal - today_c %}
            {% if rem > 0 %}<span class="text-primary fw-semibold">{{ rem }} more</span> to hit today's goal
            {% else %}<span class="text-success fw-semibold">🎉 Goal complete!</span>{% endif %}
          </small></div>
          <!-- My badge card link -->
          <div class="text-center mt-3">
            <a href="{{ url_for('badge_card', username=user.username) }}" target="_blank"
               class="btn btn-sm w-100 fw-semibold"
               style="background:{{ badge_colour }}22;border:1px solid {{ badge_colour }};color:{{ badge_colour }}">
              {{ badge_emoji }} View My Badge Card
            </a>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header p-0 border-0 bg-transparent">
          <ul class="nav nav-tabs px-3 pt-2">
            <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tabCov"><i class="bi bi-grid-3x3-gap me-1"></i>Coverage</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabLB"><i class="bi bi-trophy me-1"></i>Top</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabUp"><i class="bi bi-upload me-1"></i>Upload</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabEx"><i class="bi bi-download me-1"></i>Export</button></li>
          </ul>
        </div>
        <div class="card-body tab-content pt-3">

          <div class="tab-pane fade show active" id="tabCov">
            <p class="text-muted small mb-2"><strong>{{ selected_lang }}</strong> terms per category — sorted empty-first.</p>
            {% if coverage_rows %}
            <div class="table-responsive" style="max-height:400px;overflow-y:auto;">
              <table class="table table-sm mb-0 cov-table">
                <thead class="table-light sticky-top"><tr><th style="min-width:130px">Category</th><th class="text-center">Terms</th><th>Bar</th></tr></thead>
                <tbody>{% for row in coverage_rows %}
                  <tr><td class="small fw-semibold">{{ row.category }}</td>
                  <td class="text-center">{% if row.count > 0 %}<span class="badge {{ 'bg-success' if row.count >= 20 else 'bg-warning text-dark' }}">{{ row.count }}</span>{% else %}<span class="text-muted small">—</span>{% endif %}</td>
                  <td><div class="goal-bar-wrap" style="height:6px;">{% set pct=[row.count*100//20,100]|min %}<div class="goal-bar {{ 'done' if row.count>=20 else '' }}" style="width:{{ pct }}%"></div></div></td></tr>
                {% endfor %}</tbody>
              </table>
            </div>{% else %}
            <div class="text-center py-3 text-muted"><i class="bi bi-bar-chart-line fs-2 d-block mb-2"></i>No entries yet.</div>{% endif %}
          </div>

          <div class="tab-pane fade" id="tabLB">
            <p class="text-muted small mb-2">Top contributors across all languages.</p>
            {% if leaderboard %}
            <div>{% for row in leaderboard %}
              <div class="lb-row">
                <div class="lb-rank text-muted">{{ loop.index }}</div>
                <div class="flex-grow-1">
                  <div class="fw-semibold small">{{ row.username }}</div>
                  <div style="font-size:.72rem;color:{{ row.badge_colour }}">{{ row.badge_emoji }} {{ row.badge_label }}</div>
                </div>
                <div class="fw-bold small" style="color:{{ row.badge_colour }}">{{ row.cnt }}</div>
              </div>
            {% endfor %}</div>
            {% else %}<div class="text-center py-3 text-muted">No contributions yet.</div>{% endif %}
          </div>

          <div class="tab-pane fade" id="tabUp">
            <p class="text-muted small mb-3">Required: <code>english_text</code>, <code>local_text</code>.<br>Optional: <code>category</code>, <code>target_lang</code> (defaults to <strong>{{ selected_lang }}</strong>).</p>
            <form method="POST" action="/upload_csv" enctype="multipart/form-data">
              <input type="hidden" name="target_lang" value="{{ selected_lang }}">
              <div class="mb-3"><input type="file" name="csv_file" class="form-control" accept=".csv" required></div>
              {% if user.role == 'admin' %}<div class="small text-muted mb-2">Admin tip: upload CSV with only <code>english_text</code> to seed all approved languages as <code>[PENDING]</code>, then fill translations gradually.</div>{% endif %}
              <button type="submit" class="btn btn-warning text-dark fw-semibold w-100"><i class="bi bi-upload me-2"></i>Upload CSV</button>
            </form>
          </div>

          <div class="tab-pane fade" id="tabEx">
            <p class="text-muted small mb-3">Download your dataset as CSV.</p>
            <div class="d-grid gap-2">
              <a href="/export_csv?lang={{ selected_lang | urlencode }}" class="export-btn text-center"><i class="bi bi-download me-2"></i>Export {{ selected_lang }} ({{ lang_counts.get(selected_lang, 0) }} terms)</a>
              <a href="/export_csv" class="btn btn-outline-success fw-semibold"><i class="bi bi-download me-1"></i>Export ALL ({{ total_count }} terms)</a>
            </div>
            <hr class="my-3"/>
            <p class="text-muted small mb-1"><strong>REST API:</strong></p>
            <code style="font-size:.76rem">/api/translate?text=hello&lang={{ selected_lang | urlencode }}</code><br>
            <code style="font-size:.76rem">/api/languages</code> &nbsp;<code style="font-size:.76rem">/api/stats</code>
          </div>

        </div>
      </div>
    </div>
  </div>
</div>

<div class="container-lg pb-4">
  <div class="article-section">
    <div class="article-header">
      <i class="bi bi-file-text"></i>Article / Long Text Translation
      <span style="font-weight:400;font-size:.78rem;opacity:.85;margin-left:.4rem">— paste any paragraph, article or essay</span>
      {% if not ai_active %}<span class="badge bg-warning text-dark ms-auto" style="font-size:.7rem"><i class="bi bi-exclamation-triangle me-1"></i>Needs HF_TOKEN</span>{% endif %}
    </div>
    <div class="p-3 p-md-4">
      <div class="row g-3 mb-3">
        <div class="col-lg-6">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <label class="fw-semibold small text-muted"><i class="bi bi-pencil-square me-1"></i>English Text</label>
            <span class="text-muted small" id="charCount">0 chars</span>
          </div>
          <textarea id="articleInput" class="article-pane" rows="10" placeholder="Paste your article here…"></textarea>
        </div>
        <div class="col-lg-6">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <label class="fw-semibold small text-muted"><i class="bi bi-translate me-1"></i>Translation</label>
            <div class="d-flex gap-2">
              <button class="btn btn-outline-secondary btn-sm d-none" id="copyBtn" onclick="copyTranslation()"><i class="bi bi-clipboard me-1"></i>Copy</button>
              <button class="btn btn-outline-success btn-sm d-none" id="dlBtn" onclick="downloadTranslation()"><i class="bi bi-download me-1"></i>Save</button>
            </div>
          </div>
          <textarea id="articleOutput" class="article-pane" rows="10" placeholder="Translation appears here…" readonly></textarea>
        </div>
      </div>
      <div class="d-flex align-items-center gap-3 flex-wrap mb-3">
        <div class="d-flex align-items-center gap-2">
          <label class="fw-semibold small text-muted mb-0">Language:</label>
          <select id="articleLang" class="form-select form-select-sm" style="width:auto">
            {% for lang in languages %}<option value="{{ lang.name }}" {{ 'selected' if lang.name==selected_lang else '' }}>{{ lang.name }}</option>{% endfor %}
          </select>
        </div>
        <button class="art-btn" id="artBtn" onclick="translateArticle()" {{ 'disabled' if not ai_active else '' }}><i class="bi bi-arrow-right-circle me-2"></i>Translate Article</button>
        <button class="btn btn-outline-secondary btn-sm d-none" id="clearBtn" onclick="clearArticle()"><i class="bi bi-x-circle me-1"></i>Clear</button>
        <span class="text-muted small ms-auto d-none" id="artStatus"></span>
      </div>
      <div class="progress-art d-none" id="artProgress"><div class="progress-art-bar" id="artProgressBar"></div></div>
      <div style="display:none" id="artResultWrap">
        <hr class="my-3"/>
        <div class="d-flex justify-content-between align-items-center mb-2">
          <span class="fw-semibold small text-muted"><i class="bi bi-list-ul me-1"></i>Paragraph breakdown</span>
          <span class="badge bg-secondary small" id="chunkBadge"></span>
        </div>
        <div id="chunkResults"></div>
      </div>
    </div>
  </div>
</div>

<!-- PASSWORD CHANGE MODAL -->
<div class="modal fade" id="pwModal" tabindex="-1">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header border-0 pb-0">
        <h5 class="modal-title fw-bold"><i class="bi bi-lock me-2"></i>Change Password</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <form method="POST" action="/change_password" id="pwForm">
          <div class="mb-3">
            <label class="form-label fw-semibold small">Current Password</label>
            <input type="password" name="current_password" class="form-control" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-semibold small">New Password</label>
            <input type="password" name="new_password" class="form-control" required minlength="6">
          </div>
          <div class="mb-3">
            <label class="form-label fw-semibold small">Confirm New Password</label>
            <input type="password" name="confirm_password" class="form-control" required minlength="6">
          </div>
          <div class="d-flex gap-2">
            <button type="submit" class="btn btn-primary fw-semibold flex-grow-1">Update Password</button>
            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</div>

<!-- PROFILE PHOTO MODAL -->
<div class="modal fade" id="photoModal" tabindex="-1">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header border-0 pb-0">
        <h5 class="modal-title fw-bold"><i class="bi bi-person-circle me-2"></i>Edit Profile Photo</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        {% if user_photo %}
        <div class="text-center mb-3">
          <img src="data:image/jpeg;base64,{{ user_photo }}" alt="Current photo"
               style="width:100px;height:100px;border-radius:50%;object-fit:cover;border:3px solid {{ badge_colour }}">
          <div class="text-muted small mt-1">Current photo</div>
        </div>
        {% endif %}
        <form method="POST" action="/profile" enctype="multipart/form-data">
          <div class="mb-3">
            <label class="form-label fw-semibold small">Upload New Photo</label>
            <input type="file" name="photo" class="form-control" accept="image/*" required>
            <div class="form-text">JPG/PNG · Max 2MB · Square crop recommended</div>
          </div>
          <div class="d-flex gap-2">
            <button type="submit" class="btn btn-primary fw-semibold flex-grow-1"><i class="bi bi-upload me-2"></i>Upload Photo</button>
            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</div>

<footer class="text-center text-muted small py-3 border-top bg-white">
  Techdialect Engine v6.1 &nbsp;·&nbsp; Logged in as <strong>{{ user.username }}</strong>
  &nbsp;·&nbsp; <a href="/badge/{{ user.username }}" target="_blank" class="text-decoration-none" style="color:{{ badge_colour }}">{{ badge_emoji }} My Badge</a>
  &nbsp;·&nbsp; <a href="/badge/{{ user.username }}/download" class="text-decoration-none text-success fw-semibold"><i class="bi bi-download"></i> Download Badge</a>
  &nbsp;·&nbsp; <a href="#" data-bs-toggle="modal" data-bs-target="#photoModal" class="text-decoration-none text-primary"><i class="bi bi-person-circle"></i> Profile Photo</a>
  &nbsp;·&nbsp; <a href="#" data-bs-toggle="modal" data-bs-target="#pwModal" class="text-decoration-none text-secondary"><i class="bi bi-lock"></i> Change Password</a>
  &nbsp;·&nbsp; <a href="/docs" class="text-primary text-decoration-none fw-semibold"><i class="bi bi-code-slash"></i> API Docs</a>
  &nbsp;·&nbsp; <a href="/export_csv" class="text-success text-decoration-none fw-semibold"><i class="bi bi-download"></i> Export All</a>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
window.addEventListener('DOMContentLoaded',function(){var e=document.getElementById('engInput');if(e)e.focus();});
document.addEventListener('keydown',function(e){if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){var f=document.getElementById('quickForm');if(f)f.submit();}});
var hintTimer=null,engInput=document.getElementById('engInput'),localInput=document.getElementById('localInput'),hintBox=document.getElementById('aiHintBox'),hintText=document.getElementById('aiHintText'),selLang="{{ selected_lang }}",aiActive={{ 'true' if ai_active else 'false' }};
function useHint(){if(hintText&&localInput){localInput.value=hintText.textContent;localInput.focus();}}
if(engInput&&aiActive){engInput.addEventListener('input',function(){clearTimeout(hintTimer);var v=engInput.value.trim();if(v.length<3){if(hintBox)hintBox.classList.add('d-none');return;}hintTimer=setTimeout(function(){if(localInput&&localInput.value.trim())return;fetch('/api/translate?text='+encodeURIComponent(v)+'&lang='+encodeURIComponent(selLang)).then(function(r){return r.json();}).then(function(d){if(d.local&&d.status!=='not_found'&&d.status!=='error'){hintText.textContent=d.local;hintBox.classList.remove('d-none');}else{hintBox.classList.add('d-none');}}).catch(function(){hintBox.classList.add('d-none');});},900);});}
var artLang=document.getElementById('articleLang'),artInput=document.getElementById('articleInput'),artOutput=document.getElementById('articleOutput'),artStatus=document.getElementById('artStatus'),artProg=document.getElementById('artProgress'),artProgBar=document.getElementById('artProgressBar'),artBtn=document.getElementById('artBtn'),artWrap=document.getElementById('artResultWrap'),chunkRes=document.getElementById('chunkResults'),chunkBadge=document.getElementById('chunkBadge'),copyBtn=document.getElementById('copyBtn'),dlBtn=document.getElementById('dlBtn'),clearBtn=document.getElementById('clearBtn'),charCount=document.getElementById('charCount');
if(artInput){artInput.addEventListener('input',function(){if(charCount)charCount.textContent=artInput.value.length.toLocaleString()+' chars';});}
function setStatus(m,c){if(!artStatus)return;artStatus.textContent=m;artStatus.className='text-'+(c||'muted')+' small ms-auto';artStatus.classList.remove('d-none');}
function setProg(p){if(!artProg)return;artProg.classList.remove('d-none');artProgBar.style.width=Math.min(p,100)+'%';}
function translateArticle(){var text=artInput?artInput.value.trim():'',lang=artLang?artLang.value:selLang;if(!text){setStatus('Paste some text first.','danger');return;}
if(artBtn){artBtn.disabled=true;artBtn.innerHTML='<i class="bi bi-hourglass-split me-2"></i>Translating…';}
if(artOutput)artOutput.value='';if(chunkRes)chunkRes.innerHTML='';if(artWrap)artWrap.style.display='none';if(copyBtn)copyBtn.classList.add('d-none');if(dlBtn)dlBtn.classList.add('d-none');if(clearBtn)clearBtn.classList.remove('d-none');setProg(8);setStatus('Sending to AI…','primary');
fetch('/translate_article',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text,lang:lang})}).then(function(r){return r.json();}).then(function(d){
if(d.status==='error'||d.status==='no_ai'){setProg(0);artProg.classList.add('d-none');setStatus(d.message||'Failed.','danger');if(artBtn){artBtn.disabled=false;artBtn.innerHTML='<i class="bi bi-arrow-right-circle me-2"></i>Translate Article';}return;}
if(artOutput)artOutput.value=d.full_translation||'';setProg(100);setStatus('Done — '+d.total_chunks+' chunk'+(d.total_chunks!==1?'s':'')+' translated.','success');if(copyBtn)copyBtn.classList.remove('d-none');if(dlBtn)dlBtn.classList.remove('d-none');
	if(chunkRes&&d.chunks&&d.chunks.length){if(chunkBadge)chunkBadge.textContent=d.chunks.length+' paragraphs';var html='';d.chunks.forEach(function(c){var b=c.source==='db'?'<span class="badge-db">DB</span>':'<span class="badge-ai">AI</span>';html+='<div class="chunk-row"><div class="row g-2"><div class="col-md-6 chunk-en">'+esc(c.english)+'</div><div class="col-md-6 chunk-tiv">'+b+' '+esc(c.local||'—')+'</div></div></div>';});chunkRes.innerHTML=html;artWrap.style.display='block';}
if(artBtn){artBtn.disabled=false;artBtn.innerHTML='<i class="bi bi-arrow-right-circle me-2"></i>Translate Article';}}).catch(function(e){setStatus('Error: '+e,'danger');if(artBtn)artBtn.disabled=false;});}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function copyTranslation(){if(!artOutput)return;navigator.clipboard.writeText(artOutput.value).then(function(){var o=copyBtn.innerHTML;copyBtn.innerHTML='<i class="bi bi-check me-1"></i>Copied!';setTimeout(function(){copyBtn.innerHTML=o;},1800);});}
function downloadTranslation(){var t=artOutput?artOutput.value:'',lang=artLang?artLang.value:'translation';var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([t],{type:'text/plain;charset=utf-8'}));a.download='techdialect_'+lang.toLowerCase().replace(/\s+/g,'_')+'_translation.txt';a.click();}
function clearArticle(){if(artInput)artInput.value='';if(artOutput)artOutput.value='';if(chunkRes)chunkRes.innerHTML='';if(artWrap)artWrap.style.display='none';if(artProg){artProg.classList.add('d-none');artProgBar.style.width='0%';}if(artStatus)artStatus.classList.add('d-none');if(copyBtn)copyBtn.classList.add('d-none');if(dlBtn)dlBtn.classList.add('d-none');if(clearBtn)clearBtn.classList.add('d-none');if(charCount)charCount.textContent='0 chars';if(artInput)artInput.focus();}
</script></body></html>"""

# ── ADMIN TEMPLATE ─────────────────────────────────────────────────────────────
ADMIN_HTML = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Techdialect Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
<style>
body{background:#f5f7ff;font-family:'Segoe UI',system-ui,sans-serif;}
.navbar{background:linear-gradient(135deg,#1a1a2e,#16213e)!important;}
.brand{font-weight:800;color:#fff;font-size:1.1rem;}.brand span{color:#e85d04;}
.card{border:none;border-radius:.9rem;box-shadow:0 2px 14px rgba(0,0,0,.07);}
.card-header{border-radius:.9rem .9rem 0 0!important;font-weight:600;}
th{font-size:.76rem;text-transform:uppercase;letter-spacing:.04em;}
td{vertical-align:middle!important;font-size:.85rem;}
.msg-body{font-size:.83rem;color:#374151;max-width:400px;white-space:pre-wrap;}
</style></head><body>
<nav class="navbar navbar-dark shadow-sm py-2 mb-4">
  <div class="container">
    <span class="brand"><i class="bi bi-shield-lock me-2"></i>Tech<span>dialect</span> Admin</span>
    <div>
      <a href="{{ url_for('dashboard') }}" class="btn btn-outline-light btn-sm me-2"><i class="bi bi-arrow-left me-1"></i>Dashboard</a>
      <a href="{{ url_for('logout') }}" class="btn btn-outline-danger btn-sm">Logout</a>
    </div>
  </div>
</nav>
<div class="container pb-5">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}<div class="alert alert-{{ cat }} alert-dismissible fade show py-2 small">{{ msg }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>{% endfor %}
  {% endwith %}
  <div class="row g-4">

    <div class="col-lg-6">
      <div class="card">
        <div class="card-header bg-warning text-dark"><i class="bi bi-person-exclamation me-2"></i>Pending Approvals <span class="badge bg-dark ms-2">{{ pending_users|length }}</span></div>
        <div class="card-body p-0">
          {% if pending_users %}
          <table class="table table-sm table-hover mb-0">
            <thead class="table-light"><tr><th>Username</th><th>Email</th><th>Registered</th><th></th></tr></thead>
            <tbody>{% for u in pending_users %}
              <tr><td class="fw-semibold">{{ u.username }}</td><td class="text-muted">{{ u.email }}</td><td class="text-muted small">{{ u.created_at[:10] }}</td>
              <td>
                <form method="POST" action="/admin/approve/{{ u.id }}" class="d-inline"><button class="btn btn-success btn-sm">Approve</button></form>
                <form method="POST" action="/admin/reject/{{ u.id }}" class="d-inline ms-1"><button class="btn btn-danger btn-sm">Reject</button></form>
              </td></tr>
            {% endfor %}</tbody>
          </table>
          {% else %}<div class="text-center py-4 text-muted small"><i class="bi bi-check-circle fs-2 d-block mb-2 text-success"></i>No pending approvals.</div>{% endif %}
        </div>
      </div>
    </div>

    <div class="col-lg-6">
      <div class="card">
        <div class="card-header bg-info text-white"><i class="bi bi-globe2 me-2"></i>Language Proposals <span class="badge bg-white text-dark ms-2">{{ pending_langs|length }} pending</span></div>
        <div class="card-body p-0">
          {% if pending_langs %}
          <table class="table table-sm table-hover mb-0">
            <thead class="table-light"><tr><th>Language</th><th>NLLB Code</th><th>Proposed by</th><th></th></tr></thead>
            <tbody>{% for l in pending_langs %}
              <tr><td class="fw-semibold">{{ l.name }}</td><td><code>{{ l.nllb_code or '—' }}</code></td><td class="text-muted small">{{ l.proposer or 'system' }}</td>
              <td>
                <form method="POST" action="/admin/approve_lang/{{ l.id }}" class="d-inline"><button class="btn btn-success btn-sm">Approve</button></form>
                <form method="POST" action="/admin/reject_lang/{{ l.id }}" class="d-inline ms-1"><button class="btn btn-danger btn-sm">Reject</button></form>
              </td></tr>
            {% endfor %}</tbody>
          </table>
          {% else %}<div class="text-center py-4 text-muted small"><i class="bi bi-check-circle fs-2 d-block mb-2 text-success"></i>No pending language proposals.</div>{% endif %}
        </div>
      </div>
    </div>

    <!-- MESSAGES INBOX -->
    <div class="col-12">
      <div class="card">
        <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
          <span><i class="bi bi-envelope me-2"></i>User Messages
          {% if unread_count > 0 %}<span class="badge bg-warning text-dark ms-2">{{ unread_count }} unread</span>{% endif %}</span>
          <div class="d-flex gap-2">
            <a href="/admin/messages/export" class="btn btn-light btn-sm"><i class="bi bi-download me-1"></i>Export CSV</a>
            <form method="POST" action="/admin/messages/mark_all_read" class="d-inline">
              <button class="btn btn-outline-light btn-sm">Mark all read</button>
            </form>
            <form method="POST" action="/admin/messages/clear_old" class="d-inline">
              <button class="btn btn-outline-danger btn-sm" onclick="return confirm('Delete messages older than 7 days?')">
                <i class="bi bi-trash me-1"></i>Clear old (7d+)
              </button>
            </form>
          </div>
        </div>
        <div class="card-body p-0">
          {% if messages_list %}
          <div class="table-responsive" style="max-height:400px;overflow-y:auto;">
            <table class="table table-sm table-hover mb-0">
              <thead class="table-light sticky-top"><tr><th>From</th><th>Subject</th><th>Message</th><th>Sent</th><th>Status</th></tr></thead>
              <tbody>{% for m in messages_list %}
                <tr class="{{ '' if m.read_at else 'table-warning' }}">
                  <td class="fw-semibold">{{ m.username or '?' }}</td>
                  <td>{{ m.subject }}</td>
                  <td><div class="msg-body">{{ m.body[:120] }}{% if m.body|length > 120 %}…{% endif %}</div></td>
                  <td class="text-muted small">{{ m.created_at[:16].replace('T',' ') }}</td>
                  <td>{% if m.read_at %}<span class="badge bg-secondary">Read</span>
                  {% else %}<form method="POST" action="/admin/messages/read/{{ m.id }}" class="d-inline"><button class="btn btn-success btn-sm py-0">Mark read</button></form>{% endif %}</td>
                </tr>
              {% endfor %}</tbody>
            </table>
          </div>
          {% else %}<div class="text-center py-4 text-muted small"><i class="bi bi-inbox fs-2 d-block mb-2"></i>No messages yet.</div>{% endif %}
        </div>
      </div>
    </div>

    <!-- AI REVIEW QUEUE -->
    <div class="col-12">
      <div class="card">
        <div class="card-header bg-secondary text-white">
          <i class="bi bi-shield-check me-2"></i>AI Translation Review Queue
          <span class="badge bg-warning text-dark ms-2">{{ pending_translations|length }} pending</span>
        </div>
        <div class="card-body p-0">
          {% if pending_translations %}
          <div class="table-responsive">
            <table class="table table-sm table-hover mb-0">
              <thead class="table-light"><tr><th>English</th><th>Translation</th><th>Language</th><th>Contributor</th><th>Added</th><th></th></tr></thead>
              <tbody>{% for t in pending_translations %}
                <tr>
                  <td class="fw-semibold">{{ t.english_text }}</td>
                  <td>{{ t.local_text }}</td>
                  <td><span class="badge bg-light text-dark">{{ t.target_lang }}</span></td>
                  <td class="text-muted small">{{ t.contributor or 'unknown' }}</td>
                  <td class="text-muted small">{{ t.created_at[:16].replace('T',' ') }}</td>
                  <td>
                    <form method="POST" action="/admin/translations/{{ t.id }}/approve" class="d-inline">
                      <button class="btn btn-success btn-sm py-0">Approve</button>
                    </form>
                    <form method="POST" action="/admin/translations/{{ t.id }}/reject" class="d-inline ms-1">
                      <button class="btn btn-outline-danger btn-sm py-0">Reject</button>
                    </form>
                  </td>
                </tr>
              {% endfor %}</tbody>
            </table>
          </div>
          {% else %}
            <div class="text-center py-4 text-muted small"><i class="bi bi-check2-circle fs-2 d-block mb-2 text-success"></i>No pending AI translations.</div>
          {% endif %}
        </div>
      </div>
    </div>

    <div class="col-12">
      <div class="card">
        <div class="card-header bg-dark text-white"><i class="bi bi-people me-2"></i>All Users</div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-sm table-hover mb-0">
              <thead class="table-light"><tr><th>#</th><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th>Joined</th><th>Contributions</th><th>Badge</th></tr></thead>
              <tbody>{% for u in all_users %}
  <tr>
                  <td class="text-muted">{{ u.id }}</td><td class="fw-semibold">{{ u.username }}</td>
                  <td class="text-muted">{{ u.email }}</td>
<td>
                      <span class="badge {{ 'bg-danger' if u.role=='admin' else 'bg-secondary' }}">{{ u.role }}</span>
                      {% if user.username == DEFAULT_ADMIN_USERNAME or user.role == 'admin' %}
                        {% if u.role == 'user' %}
                          <form method="POST" action="/admin/promote/{{ u.id }}" class="d-inline ms-1">
                            <button class="btn btn-outline-danger btn-sm py-0" style="font-size: .65rem;" onclick="return confirm('Promote {{ u.username }} to Admin?')">Promote</button>
                          </form>
                        {% elif u.role == 'admin' and u.username != DEFAULT_ADMIN_USERNAME %}
                          <form method="POST" action="/admin/demote/{{ u.id }}" class="d-inline ms-1">
                            <button class="btn btn-outline-secondary btn-sm py-0" style="font-size: .65rem;" onclick="return confirm('Demote {{ u.username }} to User?')">Demote</button>
                          </form>
                        {% endif %}
                      {% endif %}
                    </td>
	                  <td><span class="badge {{ 'bg-success' if u.approved else 'bg-warning text-dark' }}">{{ 'Active' if u.approved else 'Pending' }}</span></td>
	                  <td class="text-muted small">{{ u.created_at[:10] }}</td>
	                  <td class="text-muted">{{ user_contrib.get(u.id,0) }}</td>
	                  <td><span style="font-size:.82rem;font-weight:600">{{ user_badges.get(u.id, {}).get('emoji','—') }} {{ user_badges.get(u.id, {}).get('label','') }}</span></td>
	                </tr>
              {% endfor %}</tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div class="col-12">
      <div class="card">
        <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
          <span><i class="bi bi-translate me-2"></i>All Languages</span>
          <a href="{{ url_for('propose_language') }}" class="btn btn-light btn-sm"><i class="bi bi-plus me-1"></i>Add Language</a>
        </div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-sm table-hover mb-0">
              <thead class="table-light"><tr><th>#</th><th>Name</th><th>NLLB Code</th><th>Status</th><th>Proposed by</th><th>Terms</th></tr></thead>
              <tbody>{% for l in all_langs %}
                <tr><td class="text-muted">{{ l.id }}</td><td class="fw-semibold">{{ l.name }}</td>
                <td><code>{{ l.nllb_code or '—' }}</code></td>
                <td><span class="badge {{ 'bg-success' if l.approved else 'bg-warning text-dark' }}">{{ 'Live' if l.approved else 'Pending' }}</span></td>
                <td class="text-muted small">{{ l.proposer or 'system' }}</td>
                <td class="text-muted">{{ lang_counts.get(l.name,0) }}</td></tr>
              {% endfor %}</tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>"""

PROPOSE_LANG_HTML = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Techdialect — Propose Language</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#f5f7ff;font-family:'Segoe UI',system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;}
.card{border:none;border-radius:1rem;box-shadow:0 4px 24px rgba(0,0,0,.1);padding:2rem;max-width:480px;width:100%;}
.brand{font-weight:800;color:#1a1a2e;}.brand span{color:#e85d04;}</style></head><body>
<div class="card">
  <div class="mb-4 text-center"><div class="brand fs-4"><i class="bi bi-translate me-2"></i>Tech<span>dialect</span></div>
  <p class="text-muted small mt-1">Propose a new language for the dataset engine</p></div>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}<div class="alert alert-{{ cat }} py-2 small">{{ msg }}</div>{% endfor %}
  {% endwith %}
  <form method="POST">
    <div class="mb-3"><label class="form-label fw-semibold">Language Name <span class="text-danger">*</span></label>
    <input type="text" name="name" class="form-control" placeholder="e.g. Fulfulde, Kanuri, Efik" required></div>
    <div class="mb-3"><label class="form-label fw-semibold">NLLB-200 Code <small class="text-muted fw-normal">(optional)</small></label>
    <input type="text" name="nllb_code" class="form-control" placeholder="e.g. fuv_Latn, kau_Arab">
    <div class="form-text">Find at <a href="https://github.com/facebookresearch/flores/blob/main/flores200/README.md" target="_blank">FLORES-200 list</a>. Format: <code>iso_Script</code></div></div>
    <div class="alert alert-info py-2 small"><i class="bi bi-info-circle me-1"></i>Your proposal will be reviewed by an admin before going live.</div>
    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-primary fw-semibold flex-grow-1"><i class="bi bi-send me-2"></i>Submit Proposal</button>
      <a href="{{ url_for('dashboard') }}" class="btn btn-outline-secondary">Cancel</a>
    </div>
  </form>
</div></body></html>"""

CONTACT_HTML = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Techdialect — Contact Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#f5f7ff;font-family:'Segoe UI',system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;}
.card{border:none;border-radius:1rem;box-shadow:0 4px 24px rgba(0,0,0,.1);padding:2rem;max-width:520px;width:100%;}
.brand{font-weight:800;color:#1a1a2e;}.brand span{color:#e85d04;}</style></head><body>
<div class="card">
  <div class="mb-4 text-center"><div class="brand fs-4"><i class="bi bi-envelope me-2"></i>Tech<span>dialect</span></div>
  <p class="text-muted small mt-1">Send a message to the Techdialect admin team</p></div>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}<div class="alert alert-{{ cat }} py-2 small">{{ msg }}</div>{% endfor %}
  {% endwith %}
  <form method="POST">
    <div class="mb-3"><label class="form-label fw-semibold">Subject <span class="text-danger">*</span></label>
    <input type="text" name="subject" class="form-control" placeholder="e.g. Bug report, Feature request, Language question" required></div>
    <div class="mb-3"><label class="form-label fw-semibold">Message <span class="text-danger">*</span></label>
    <textarea name="body" class="form-control" rows="5" placeholder="Describe your message…" required></textarea></div>
    <div class="alert alert-light py-2 small border"><i class="bi bi-person me-1"></i>Sending as: <strong>{{ username }}</strong></div>
    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-primary fw-semibold flex-grow-1"><i class="bi bi-send me-2"></i>Send Message</button>
      <a href="{{ url_for('dashboard') }}" class="btn btn-outline-secondary">Cancel</a>
    </div>
  </form>
</div></body></html>"""

# =============================================================================
#  RENDER HELPER
# =============================================================================

def render_main(result=None, last_query="", last_category="General", lang=None):
    if lang is None:
        lang = session.get("selected_lang", "Tiv")
    languages = db_approved_languages()
    lang_names = [l["name"] for l in languages]
    if lang not in lang_names:
        lang = lang_names[0] if lang_names else ""
    u = current_user()
    contrib = db_user_contrib_count(u["id"]) if u else 0
    slug, emoji, label, colour, dark = get_badge(contrib)
    # Next badge info
    next_badge = None
    for threshold, s, em, lb, col, dk in BADGE_LEVELS:
        if contrib < threshold:
            next_badge = (threshold, em, lb, col)
            break
    return render_template_string(
        MAIN_HTML,
        result=result, last_query=last_query,
        last_cat=session.get("last_category", last_category),
        selected_lang=lang, languages=languages,
        lang_counts=db_lang_counts(), categories=CATEGORIES,
        today_c=today_count(), daily_goal=DAILY_GOAL,
        streak=get_streak(), total_count=db_count(),
        t_days=total_days(),
        today_date=datetime.date.today().strftime("%d %b %Y"),
        recent_entries=db_translations(lang, limit=50),
        coverage_rows=db_coverage(lang),
        leaderboard=db_leaderboard(),
        ai_active=bool(HF_TOKEN and REQUESTS_AVAILABLE),
        max_chars=MAX_INPUT_CHARS,
        user=u, contrib_count=contrib,
        badge_emoji=emoji, badge_label=label, badge_colour=colour,
        unread_msgs=db_unread_count() if u and u["role"]=="admin" else 0,
        user_photo=db_get_photo(u["id"]) if u else None,
    )

# =============================================================================
#  AUTH ROUTES
# =============================================================================

@app.route("/login", methods=["GET","POST"])
def login():
    if session.get("user_id"): return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        u = get_user_by_name(username)
        if not u or not check_password_hash(u["password_hash"], password):
            flash("Invalid username or password.","danger"); return redirect(url_for("login"))
        if not u["approved"]:
            flash("Your account is awaiting admin approval.","warning"); return redirect(url_for("login"))
        session.clear()
        session["user_id"] = u["id"]; session["username"] = u["username"]; session["role"] = u["role"]
        flash(f"Welcome back, {u['username']}!","success"); return redirect(url_for("dashboard"))
    form_html = """<form method="POST"><h5 class="fw-bold mb-4">Sign In</h5>
    <div class="mb-3"><label class="form-label">Username</label><input type="text" name="username" class="form-control" required autofocus></div>
    <div class="mb-3"><label class="form-label">Password</label><input type="password" name="password" class="form-control" required></div>
    <button type="submit" class="btn btn-primary w-100 mb-3">Sign In</button>
    <div class="text-center"><small class="text-muted">No account? <a href="/register">Register here</a></small></div></form>"""
    return render_template_string(AUTH_HTML, page_title="Login", form_html=form_html)

@app.route("/register", methods=["GET","POST"])
def register():
    if session.get("user_id"): return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username","").strip()
        email    = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        confirm  = request.form.get("confirm","")
        if not username or not email or not password:
            flash("All fields are required.","danger"); return redirect(url_for("register"))
        if len(username) < 3:
            flash("Username must be at least 3 characters.","danger"); return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.","danger"); return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters.","danger"); return redirect(url_for("register"))
        try:
            db = get_db()
            db.execute("INSERT INTO users (username,email,password_hash,role,approved,created_at) VALUES (?,?,?,'user',0,?)",
                       (username,email,generate_password_hash(password),datetime.datetime.utcnow().isoformat()))
            db.commit()
            flash("Account created! An admin will approve it shortly. You'll be able to log in once approved.","success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists.","danger"); return redirect(url_for("register"))
    form_html = """<form method="POST"><h5 class="fw-bold mb-4">Create Account</h5>
    <div class="mb-3"><label class="form-label">Username</label><input type="text" name="username" class="form-control" required autofocus></div>
    <div class="mb-3"><label class="form-label">Email</label><input type="email" name="email" class="form-control" required></div>
    <div class="mb-3"><label class="form-label">Password</label><input type="password" name="password" class="form-control" required></div>
    <div class="mb-3"><label class="form-label">Confirm Password</label><input type="password" name="confirm" class="form-control" required></div>
    <div class="alert alert-info py-2 small mb-3"><i class="bi bi-info-circle me-1"></i>After registering, an admin must approve your account before you can log in.</div>
    <button type="submit" class="btn btn-primary w-100 mb-3">Register</button>
    <div class="text-center"><small class="text-muted">Have an account? <a href="/login">Sign in</a></small></div></form>"""
    return render_template_string(AUTH_HTML, page_title="Register", form_html=form_html)

@app.route("/logout")
def logout():
    session.clear(); flash("You have been logged out.","info"); return redirect(url_for("login"))

@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    """Handles the password change modal form — POST only, always redirects to dashboard."""
    u          = current_user()
    current_pw = request.form.get("current_password","")
    new_pw     = request.form.get("new_password","")
    confirm_pw = request.form.get("confirm_password","")
    if not check_password_hash(u["password_hash"], current_pw):
        flash("Current password is incorrect.","danger")
    elif len(new_pw) < 6:
        flash("New password must be at least 6 characters.","danger")
    elif new_pw != confirm_pw:
        flash("New passwords do not match.","danger")
    else:
        db = get_db()
        db.execute("UPDATE users SET password_hash=? WHERE id=?",
                   (generate_password_hash(new_pw), u["id"]))
        db.commit()
        flash("Password changed successfully! Please log in again.","success")
        session.clear()
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

# =============================================================================
#  BADGE ROUTES
# =============================================================================

@app.route("/badge/<username>")
def badge_card(username):
    """Public shareable badge card — no login required."""
    u = get_user_by_name(username)
    if not u or not u["approved"]:
        return "User not found.", 404
    contrib = db_user_contrib_count(u["id"])
    slug, emoji, label, colour, dark = get_badge(contrib)
    # Language breakdown
    rows = get_db().execute(
        "SELECT target_lang, COUNT(*) as cnt FROM translations WHERE added_by=? GROUP BY target_lang ORDER BY cnt DESC LIMIT 6",
        (u["id"],)
    ).fetchall()
    lang_breakdown = [(r["target_lang"], r["cnt"]) for r in rows]
    # Next badge
    next_at = next_label = next_emoji = next_colour = None
    for threshold, s, em, lb, col, dk in reversed(BADGE_LEVELS):
        if contrib < threshold:
            next_at = threshold; next_emoji = em; next_label = lb; next_colour = col
    return render_template_string(
        BADGE_HTML,
        username=username, contrib_count=contrib,
        badge_emoji=emoji, badge_label=label, badge_colour=colour, badge_dark=dark,
        lang_breakdown=lang_breakdown,
        next_at=next_at, next_label=next_label, next_emoji=next_emoji, next_colour=next_colour or colour,
        user_photo=db_get_photo(u["id"]),
    )

@app.route("/profile", methods=["POST"])
@login_required
def profile_upload():
    """Upload a profile photo — stored as base64 JPEG in the DB."""
    u   = current_user()
    f   = request.files.get("photo")
    if not f or not f.filename:
        flash("No file selected.", "warning")
        return redirect(url_for("dashboard"))
    try:
        # Read file bytes
        raw = f.read()
        if len(raw) > 2 * 1024 * 1024:
            flash("Photo must be under 2 MB.", "danger")
            return redirect(url_for("dashboard"))

        # Process with Pillow — resize + crop to square, compress to JPEG
        try:
            from PIL import Image as PILImage, ImageOps
            import io as _io
            img = PILImage.open(_io.BytesIO(raw)).convert("RGB")
            # Square-crop: take centre
            w, h = img.size
            side  = min(w, h)
            left  = (w - side) // 2
            top   = (h - side) // 2
            img   = img.crop((left, top, left + side, top + side))
            img   = img.resize((400, 400), PILImage.LANCZOS)
            buf   = _io.BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            b64   = base64.b64encode(buf.getvalue()).decode()
        except Exception:
            # Pillow not available — store raw as-is
            b64 = base64.b64encode(raw).decode()

        db_set_photo(u["id"], b64)
        flash("Profile photo updated!", "success")
    except Exception as exc:
        flash(f"Upload failed: {exc}", "danger")
    return redirect(url_for("dashboard"))


@app.route("/badge/<username>/download")
def badge_download(username):
    """
    Render the badge as a PNG using Pillow and return it as a download.
    Requires Pillow: pip install pillow
    Falls back to redirecting to the HTML badge page if Pillow is unavailable.
    """
    u = get_user_by_name(username)
    if not u or not u["approved"]:
        return "User not found.", 404

    try:
        from PIL import Image, ImageDraw, ImageFont, ImageEnhance
        import io as _io
    except ImportError:
        # Pillow not installed — redirect to HTML badge
        flash("Install Pillow to download PNG badges: pip install pillow", "warning")
        return redirect(url_for("badge_card", username=username))

    contrib = db_user_contrib_count(u["id"])
    slug, emoji_char, label, colour, dark = get_badge(contrib)

    # Language breakdown
    lang_rows = get_db().execute(
        "SELECT target_lang, COUNT(*) as cnt FROM translations WHERE added_by=? "
        "GROUP BY target_lang ORDER BY cnt DESC LIMIT 5", (u["id"],)
    ).fetchall()

    # Next badge
    next_label_str = ""
    for threshold, s, em, lb, col, dk in reversed(BADGE_LEVELS):
        if contrib < threshold:
            next_label_str = f"Next: {em} {lb} at {threshold} contributions"
            break

    # ── Canvas ────────────────────────────────────────────────────────────────
    W, H   = 600, 720
    card   = Image.new("RGB", (W, H), (10, 15, 28))
    d      = ImageDraw.Draw(card)

    # Parse accent colour hex → RGB
    def hex2rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    acc = hex2rgb(colour)

    # Background gradient
    for y in range(H):
        t  = y / H
        r  = int(10  + 8  * t)
        g  = int(15  + 10 * t)
        b  = int(28  + 18 * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # Accent top bar
    d.rectangle([0, 0, W, 8], fill=acc)
    # Accent bottom bar
    d.rectangle([0, H - 8, W, H], fill=acc)
    # Subtle border
    d.rectangle([0, 0, W-1, H-1], outline=acc, width=2)

    def F(size, bold=False):
        for p in [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
        ]:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    CX = W // 2

    # Brand
    d.text((CX, 22), "TECHDIALECT", font=F(22, True), fill=acc,
           anchor="mm" if hasattr(d, "textbbox") else None)
    bw = d.textbbox((0,0),"TECHDIALECT",font=F(22,True))[2]
    d.text(((W-bw)//2, 18), "TECHDIALECT", font=F(22,True), fill=acc)
    sw = d.textbbox((0,0),"technologia omnibus",font=F(13))[2]
    d.text(((W-sw)//2, 46), "technologia omnibus", font=F(13), fill=(100,120,140))

    # Profile photo or emoji circle
    photo_b64 = db_get_photo(u["id"])
    circle_y = 76
    circle_r = 80

    if photo_b64:
        try:
            img_data = base64.b64decode(photo_b64)
            photo    = Image.open(_io.BytesIO(img_data)).convert("RGB")
            photo    = photo.resize((circle_r*2, circle_r*2), Image.LANCZOS)
            photo    = ImageEnhance.Contrast(photo).enhance(1.05)
            # Circular mask
            mask = Image.new("L", (circle_r*2, circle_r*2), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, circle_r*2-1, circle_r*2-1], fill=255)
            photo_rgba = Image.new("RGBA", (circle_r*2, circle_r*2), (0,0,0,0))
            photo_rgba.paste(photo, mask=mask)
            px = CX - circle_r
            py = circle_y
            card.paste(photo, (px, py), photo_rgba.split()[3])
            # Accent ring
            d.ellipse([px-4, py-4, px+circle_r*2+4, py+circle_r*2+4], outline=acc, width=4)
        except Exception:
            photo_b64 = None  # fall through to emoji

    if not photo_b64:
        # Draw coloured circle with badge emoji text
        cx2, cy2 = CX, circle_y + circle_r
        d.ellipse([cx2-circle_r, cy2-circle_r, cx2+circle_r, cy2+circle_r],
                  fill=(20, 30, 50), outline=acc, width=4)
        # Badge level initial
        init = label[0].upper()
        iw = d.textbbox((0,0),init,font=F(56,True))[2]
        ih = d.textbbox((0,0),init,font=F(56,True))[3]
        d.text((cx2-iw//2, cy2-ih//2-4), init, font=F(56,True), fill=acc)

    y = circle_y + circle_r*2 + 20

    # Divider
    d.rectangle([(W-200)//2, y, (W+200)//2, y+2], fill=acc)
    y += 12

    # Badge level
    lw = d.textbbox((0,0),f"{label} Contributor",font=F(28,True))[2]
    d.text(((W-lw)//2, y), f"{label} Contributor", font=F(28,True), fill=acc)
    y += 38

    # Username
    uw = d.textbbox((0,0),username,font=F(22,True))[2]
    d.text(((W-uw)//2, y), username, font=F(22,True), fill=(255,255,255))
    y += 34

    # Count
    cnt_str = f"{contrib:,} translation{'s' if contrib != 1 else ''} contributed"
    cw2 = d.textbbox((0,0),cnt_str,font=F(16))[2]
    d.text(((W-cw2)//2, y), cnt_str, font=F(16), fill=(140,165,190))
    y += 30

    # Language badges
    if lang_rows:
        d.rectangle([(W-200)//2, y, (W+200)//2, y+2], fill=(30,42,60))
        y += 12
        # Render language pills
        pills = [(r["target_lang"], r["cnt"]) for r in lang_rows]
        pill_h = 28
        total_pill_w = sum(d.textbbox((0,0),f"{n}: {c}",font=F(13,True))[2]+20 for n,c in pills) + (len(pills)-1)*8
        px2 = (W - min(total_pill_w, W-60)) // 2
        for lang_name, lang_cnt in pills:
            text = f"{lang_name}: {lang_cnt}"
            tw   = d.textbbox((0,0),text,font=F(13,True))[2]
            pw2  = tw + 20
            if px2 + pw2 > W - 20:
                px2  = (W - min(total_pill_w, W-60)) // 2
                y   += pill_h + 6
            d.rounded_rectangle([px2, y, px2+pw2, y+pill_h], radius=14,
                                 fill=tuple(int(c*0.15) for c in acc))
            d.rounded_rectangle([px2, y, px2+pw2, y+pill_h], radius=14,
                                 outline=tuple(int(c*0.6) for c in acc), width=1)
            tw2 = d.textbbox((0,0),text,font=F(13,True))[2]
            d.text((px2+10, y+7), text, font=F(13,True), fill=acc)
            px2 += pw2 + 8
        y += pill_h + 14

    # Next badge note
    if next_label_str:
        nw = d.textbbox((0,0),next_label_str,font=F(13))[2]
        d.text(((W-nw)//2, y), next_label_str, font=F(13), fill=(80,100,120))
        y += 24

    # Website
    d.rectangle([(W-280)//2, H-52, (W+280)//2, H-20], fill=tuple(int(c*0.15) for c in acc))
    sw2 = d.textbbox((0,0),"silabs.pythonanywhere.com",font=F(15,True))[2]
    d.text(((W-sw2)//2, H-48), "silabs.pythonanywhere.com", font=F(15,True), fill=acc)

    # ── Encode as PNG bytes ───────────────────────────────────────────────────
    buf = _io.BytesIO()
    card.save(buf, format="PNG", optimize=True)
    buf.seek(0)

    return Response(
        buf.getvalue(),
        mimetype="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="techdialect_badge_{username}.png"',
            "Content-Length": str(len(buf.getvalue())),
        }
    )


# =============================================================================
#  ADMIN ROUTES
# =============================================================================

@app.route("/admin")
@login_required
@admin_required
def admin_panel():
    db = get_db()
    rows = db.execute("SELECT added_by, COUNT(*) as cnt FROM translations GROUP BY added_by").fetchall()
    user_contrib = {r["added_by"]: r["cnt"] for r in rows}
    pending_langs = db.execute(
        "SELECT l.*, u.username as proposer FROM languages l LEFT JOIN users u ON l.added_by=u.id WHERE l.approved=0"
    ).fetchall()
    all_users = get_all_users()
    # Pre-compute badge info for every user so Jinja2 doesn't need to call get_badge()
    user_badges = {}
    for usr in all_users:
        cnt = user_contrib.get(usr["id"], 0)
        slug, emoji, label, colour, dark = get_badge(cnt)
        user_badges[usr["id"]] = {"slug": slug, "emoji": emoji, "label": label, "colour": colour}

    return render_template_string(
        ADMIN_HTML,
        pending_users=get_pending_users(), all_users=all_users,
        pending_langs=pending_langs, all_langs=db_all_languages(),
        lang_counts=db_lang_counts(), user_contrib=user_contrib,
        messages_list=db_get_messages(), unread_count=db_unread_count(),
        pending_translations=db_pending_translations(),
        user_badges=user_badges,
        DEFAULT_ADMIN_USERNAME=DEFAULT_ADMIN_USERNAME,
    )

@app.route("/admin/approve/<int:uid>", methods=["POST"])
@login_required
@admin_required
def admin_approve(uid):
    db = get_db(); u = get_user(uid)
    if u: db.execute("UPDATE users SET approved=1 WHERE id=?", (uid,)); db.commit(); flash(f"✅ {u['username']} approved.","success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/reject/<int:uid>", methods=["POST"])
@login_required
@admin_required
def admin_reject(uid):
    db = get_db(); u = get_user(uid)
    if u and u["role"] != "admin": db.execute("DELETE FROM users WHERE id=?", (uid,)); db.commit(); flash(f"❌ {u['username']} rejected.","warning")
    return redirect(url_for("admin_panel"))

@app.route("/admin/approve_lang/<int:lid>", methods=["POST"])
@login_required
@admin_required
def admin_approve_lang(lid):
    db = get_db(); row = db.execute("SELECT * FROM languages WHERE id=?", (lid,)).fetchone()
    if row: db.execute("UPDATE languages SET approved=1 WHERE id=?", (lid,)); db.commit(); flash(f"✅ Language '{row['name']}' is now live.","success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/reject_lang/<int:lid>", methods=["POST"])
@login_required
@admin_required
def admin_reject_lang(lid):
    db = get_db(); row = db.execute("SELECT * FROM languages WHERE id=?", (lid,)).fetchone()
    if row: db.execute("DELETE FROM languages WHERE id=?", (lid,)); db.commit(); flash(f"Language '{row['name']}' rejected.","warning")
    return redirect(url_for("admin_panel"))

@app.route("/admin/promote/<int:uid>", methods=["POST"])
@login_required
@admin_required
def admin_promote(uid):
    db = get_db(); u = get_user(uid)
    if u:
        db.execute("UPDATE users SET role='admin' WHERE id=?", (uid,))
        db.commit()
        flash(f"✅ {u['username']} has been promoted to Admin.", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/demote/<int:uid>", methods=["POST"])
@login_required
@admin_required
def admin_demote(uid):
    db = get_db(); u = get_user(uid)
    if u:
        if u['username'] == DEFAULT_ADMIN_USERNAME:
            flash("❌ Cannot demote the primary system admin.", "danger")
        else:
            db.execute("UPDATE users SET role='user' WHERE id=?", (uid,))
            db.commit()
            flash(f"⚠️ {u['username']} has been demoted to User.", "warning")
    return redirect(url_for("admin_panel"))

# ── Message admin routes ───────────────────────────────────────────────────────

@app.route("/admin/messages/read/<int:mid>", methods=["POST"])
@login_required
@admin_required
def admin_read_message(mid):
    db_mark_read(mid)
    flash("Message marked as read.","success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/messages/mark_all_read", methods=["POST"])
@login_required
@admin_required
def admin_mark_all_read():
    db_mark_all_read()
    flash("All messages marked as read.","success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/messages/export")
@login_required
@admin_required
def admin_export_messages():
    """Download all messages as CSV."""
    rows = db_get_messages()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["id","from_user","subject","body","sent_at","read_at"])
    for r in rows:
        w.writerow([r["id"], r["username"] or "", r["subject"], r["body"],
                    r["created_at"], r["read_at"] or ""])
    raw = output.getvalue().encode("utf-8-sig")
    return Response(raw, mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=techdialect_messages.csv",
                             "Content-Length": str(len(raw))})

@app.route("/admin/messages/clear_old", methods=["POST"])
@login_required
@admin_required
def admin_clear_old_messages():
    """Delete messages older than 7 days."""
    n = db_delete_old_messages(days=7)
    flash(f"Deleted {n} message(s) older than 7 days.","success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/translations/<int:tid>/approve", methods=["POST"])
@login_required
@admin_required
def admin_approve_translation(tid):
    u = current_user()
    db_update_translation_review(tid, "verified", u["id"])
    flash("Translation approved and marked as verified.", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/translations/<int:tid>/reject", methods=["POST"])
@login_required
@admin_required
def admin_reject_translation(tid):
    u = current_user()
    db_update_translation_review(tid, "rejected", u["id"])
    flash("Translation marked as rejected.", "warning")
    return redirect(url_for("admin_panel"))

# =============================================================================
#  LANGUAGE PROPOSAL ROUTE
# =============================================================================

@app.route("/languages/propose", methods=["GET","POST"])
@login_required
def propose_language():
    if request.method == "POST":
        name      = request.form.get("name","").strip().title()
        nllb_code = request.form.get("nllb_code","").strip() or None
        u = current_user()
        if not name: flash("Language name is required.","danger"); return redirect(url_for("propose_language"))
        try:
            db = get_db()
            db.execute("INSERT INTO languages (name,nllb_code,added_by,approved,created_at) VALUES (?,?,?,0,?)",
                       (name,nllb_code,u["id"],datetime.datetime.utcnow().isoformat()))
            db.commit()
            flash(f"'{name}' submitted for admin review. It will appear once approved.","success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash(f"'{name}' already exists.","warning"); return redirect(url_for("propose_language"))
    return render_template_string(PROPOSE_LANG_HTML)

# =============================================================================
#  CONTACT ROUTE
# =============================================================================

@app.route("/contact", methods=["GET","POST"])
@login_required
def contact():
    u = current_user()
    if request.method == "POST":
        subject = request.form.get("subject","").strip()
        body    = request.form.get("body","").strip()
        if not subject or not body:
            flash("Both subject and message are required.","danger")
            return redirect(url_for("contact"))
        if len(body) > 2000:
            flash("Message too long (max 2000 characters).","danger")
            return redirect(url_for("contact"))
        db_send_message(u["id"], subject, body)
        flash("Your message has been sent to the admin team. We'll follow up if needed.","success")
        return redirect(url_for("dashboard"))
    return render_template_string(CONTACT_HTML, username=u["username"])

# =============================================================================
#  MAIN APP ROUTES
# =============================================================================

@app.route("/", methods=["GET"])
@login_required
def dashboard():
    lang = request.args.get("lang", session.get("selected_lang"))
    lang_names = {l["name"] for l in db_approved_languages()}
    if not lang or lang not in lang_names:
        lang = next(iter(lang_names), "Tiv")
    session["selected_lang"] = lang
    return render_main(lang=lang)

@app.route("/translate", methods=["POST"])
@login_required
def translate_route():
    english = request.form.get("english_text","").strip()
    lang    = request.form.get("target_lang", session.get("selected_lang","Tiv"))
    session["selected_lang"] = lang
    return render_main(result=translate(english,lang), last_query=english, lang=lang)

@app.route("/add", methods=["POST"])
@login_required
def add_route():
    english  = request.form.get("english_text","").strip()
    local    = request.form.get("local_text","").strip()
    lang     = request.form.get("target_lang", session.get("selected_lang","Tiv"))
    category = request.form.get("category","General").strip()
    u = current_user()
    if not english or not local:
        flash("Both English and translation are required.","warning"); return redirect(url_for("dashboard"))
    if db_insert(english,local,lang,category,"manual",u["id"]):
        session["last_category"] = category; session["selected_lang"] = lang
        flash(f'✅ Saved: "{english}" → "{local}"',"success")
    else:
        flash(f'"{english}" already exists in {lang}.',"info")
    return redirect(url_for("dashboard", lang=lang))

@app.route("/save", methods=["POST"])
@login_required
def save_route():
    english  = request.form.get("english_text","").strip()
    local    = request.form.get("local_text","").strip()
    lang     = request.form.get("target_lang", session.get("selected_lang","Tiv"))
    category = request.form.get("category","General").strip()
    u = current_user()
    if db_insert(english,local,lang,category,"ai",u["id"]):
        flash(f'✅ Saved AI translation: "{english}"',"success")
    else:
        flash(f'"{english}" already exists in {lang}.',"info")
    session["selected_lang"] = lang
    return redirect(url_for("dashboard", lang=lang))

@app.route("/upload_csv", methods=["POST"])
@login_required
def upload_csv_route():
    file         = request.files.get("csv_file")
    default_lang = request.form.get("target_lang", session.get("selected_lang","Tiv"))
    u = current_user()
    if not file or not file.filename:
        flash("No file selected.","warning"); return redirect(url_for("dashboard"))
    approved_langs = db_lang_names()
    try:
        content = file.read().decode("utf-8-sig")
        reader  = csv.DictReader(io.StringIO(content))
        added, dupes, bad, seeded = 0, 0, 0, 0
        is_admin = (u and u.get("role") == "admin")
        for row in reader:
            eng  = (row.get("english_text") or "").strip()
            loc  = (row.get("local_text")   or "").strip()
            cat  = (row.get("category")     or "General").strip()
            lang = (row.get("target_lang")  or default_lang).strip()
            if not eng: bad += 1; continue
            if cat not in CATEGORIES: cat = "General"

            if not loc and is_admin:
                for lang_name in approved_langs:
                    if db_insert(eng,"[PENDING]",lang_name,cat,"csv_seed_admin",u["id"],allow_update_pending=False): seeded += 1
                    else: dupes += 1
                continue

            if not loc: bad += 1; continue
            if lang not in approved_langs: lang = default_lang
            if db_insert(eng,loc,lang,cat,"csv",u["id"]): added += 1
            else: dupes += 1
        msg = f"Upload done: {added} translations added, {dupes} duplicates skipped"
        if seeded:
            msg += f", {seeded} admin seed rows created as [PENDING] across all languages"
        msg += f", {bad} incomplete rows skipped." if bad else "."
        flash(msg,"success" if added else "warning")
    except Exception as exc:
        flash(f"CSV error: {exc}","danger")
    session["selected_lang"] = default_lang
    return redirect(url_for("dashboard", lang=default_lang))

@app.route("/export_csv")
@login_required
def export_csv_route():
    lang_filter = request.args.get("lang")
    if lang_filter and lang_filter not in db_lang_names(): lang_filter = None
    rows   = db_translations(lang_filter)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","english_text","local_text","target_lang","category","source","contributor","created_at"])
    for r in rows:
        writer.writerow([r["id"],r["english_text"],r["local_text"],r["target_lang"],
                         r["category"],r["source"],r["contributor"] or "",r["created_at"]])
    raw  = output.getvalue().encode("utf-8-sig")
    fname = f"techdialect_{lang_filter.lower().replace(' ','_')}.csv" if lang_filter else "techdialect_all_languages.csv"
    return Response(raw, mimetype="text/csv",
                    headers={"Content-Disposition":f"attachment; filename={fname}","Content-Length":str(len(raw))})

@app.route("/translate_article", methods=["POST"])
@login_required
def translate_article_route():
    body = request.get_json(silent=True) or {}
    text = body.get("text","").strip()
    lang = body.get("lang", session.get("selected_lang","Tiv")).strip()
    return jsonify(translate_article(text, lang))

# =============================================================================
#  REST API
# =============================================================================

@app.route("/api/translate")
def api_translate():
    text = request.args.get("text","").strip()
    lang = request.args.get("lang","Tiv").strip()
    return jsonify(translate(text, lang))

@app.route("/api/languages")
def api_languages():
    lc = db_lang_counts()
    return jsonify({"languages":[{"name":l["name"],"nllb_code":l["nllb_code"],"count":lc.get(l["name"],0)} for l in db_approved_languages()]})

@app.route("/api/stats")
def api_stats():
    return jsonify({"total_terms":db_count(),"today_count":today_count(),"daily_goal":DAILY_GOAL,
                    "streak_days":get_streak(),"total_days":total_days(),
                    "ai_active":bool(HF_TOKEN and REQUESTS_AVAILABLE),"languages":db_lang_counts()})

@app.route("/api/coverage")
def api_coverage():
    lang = request.args.get("lang","Tiv")
    return jsonify({"lang":lang,"coverage":db_coverage(lang)})

@app.route("/api/translate_article", methods=["POST"])
def api_translate_article():
    body = request.get_json(silent=True) or {}
    return jsonify(translate_article(body.get("text","").strip(), body.get("lang","Tiv").strip()))

@app.route("/api/badge/<username>")
def api_badge(username):
    """GET /api/badge/<username> — badge data as JSON."""
    u = get_user_by_name(username)
    if not u or not u["approved"]: return jsonify({"error":"User not found"}), 404
    contrib = db_user_contrib_count(u["id"])
    slug, emoji, label, colour, dark = get_badge(contrib)
    return jsonify({"username":username,"contributions":contrib,"badge":{"slug":slug,"emoji":emoji,"label":label,"colour":colour}})

@app.route("/docs")
def api_docs():
    """Render a simple API documentation page."""
    return render_template_string("""
    <!DOCTYPE html><html lang="en"><head>
    <meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>Techdialect API Documentation</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{background:#f8fafc;font-family:system-ui,-apple-system,sans-serif;padding:2rem 0;}
    .card{border:none;border-radius:1rem;box-shadow:0 4px 12px rgba(0,0,0,.05);margin-bottom:2rem;}
    code{background:#f1f5f9;color:#e85d04;padding:.2rem .4rem;border-radius:.3rem;}
    pre{background:#1e293b;color:#f8fafc;padding:1rem;border-radius:.5rem;overflow-x:auto;}
    .method{font-weight:800;margin-right:.5rem;color:#0d6efd;}</style></head><body>
    <div class="container" style="max-width:800px;">
      <div class="d-flex align-items-center gap-3 mb-4">
        <a href="/" class="btn btn-outline-secondary btn-sm">← Back</a>
        <h1 class="h3 fw-bold mb-0">Techdialect API <span class="badge bg-primary small" style="font-size:.6rem">v1.0</span></h1>
      </div>
      <p class="text-muted">Integrate Nigerian language translations into your own apps and services.</p>
      
      <div class="card"><div class="card-body">
        <h5 class="fw-bold"><span class="method">GET</span> /api/translate</h5>
        <p class="small text-muted">Translate text using the 3-tier engine.</p>
        <p class="mb-1 small fw-bold">Parameters:</p>
        <ul class="small"><li><code>text</code>: The English text to translate.</li><li><code>lang</code>: Target language (e.g. Tiv, Yoruba).</li></ul>
        <pre>{ "status": "exact", "english": "Hello", "local": "M sugh u", "lang": "Tiv" }</pre>
      </div></div>

      <div class="card"><div class="card-body">
        <h5 class="fw-bold"><span class="method">GET</span> /api/languages</h5>
        <p class="small text-muted">List all approved languages and their dataset counts.</p>
        <pre>{ "languages": [ { "name": "Tiv", "count": 450 }, ... ] }</pre>
      </div></div>

      <div class="card"><div class="card-body">
        <h5 class="fw-bold"><span class="method">GET</span> /api/stats</h5>
        <p class="small text-muted">Get global platform statistics.</p>
        <pre>{ "total_terms": 1250, "streak_days": 14, ... }</pre>
      </div></div>
      
      <div class="text-center text-muted small mt-5">Techdialect — technologia omnibus</div>
    </div></body></html>""")

@app.route("/manifest.json")
def serve_manifest():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "manifest.json")

# =============================================================================
#  ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    init_db()
    print("\n" + "="*65)
    print("  TECHDIALECT TRANSLATION ENGINE  v6.1")
    print("  Multi-user · Badges + Photos · Messaging · User-managed languages")
    print("="*65)
    print(f"  DB     : {DB_PATH}")
    print(f"  AI     : {'✅ HuggingFace API active' if HF_TOKEN else '❌ No HF_TOKEN — DB-only mode'}")
    print(f"  Admin  : {DEFAULT_ADMIN_USERNAME} / Techdialect@2024")
    print(f"  URL    : http://127.0.0.1:5000")
    print(f"  Badge  : http://127.0.0.1:5000/badge/<username>")
    print(f"  Stop   : Ctrl+C")
    print("="*65 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5000, use_reloader=False)
else:
    init_db()
