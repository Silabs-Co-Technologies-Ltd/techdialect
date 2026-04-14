# =============================================================================
#  TECHDIALECT TRANSLATION ENGINE  v5.0
#  Multi-user · Admin approval · User-managed languages · PythonAnywhere ready
#  Single-file Flask app · SQLite · HuggingFace Inference API · Bootstrap 5
# =============================================================================
#
#  ╔══════════════════════════════════════════════════════════════════════════╗
#  ║                    PYTHONANYWHERE DEPLOYMENT GUIDE                       ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║                                                                          ║
#  ║  STEP 1 — Upload this file                                               ║
#  ║    Dashboard → Files → upload smart_translation_system.py               ║
#  ║    to /home/<yourusername>/                                              ║
#  ║                                                                          ║
#  ║  STEP 2 — Create a Web App                                               ║
#  ║    Web tab → Add a new web app → Manual configuration → Python 3.10     ║
#  ║                                                                          ║
#  ║  STEP 3 — Set the WSGI file                                              ║
#  ║    In the Web tab, click your WSGI file link and replace ALL content     ║
#  ║    with these 4 lines:                                                   ║
#  ║                                                                          ║
#  ║        import sys                                                        ║
#  ║        sys.path.insert(0, '/home/<yourusername>')                        ║
#  ║        from smart_translation_system import app as application           ║
#  ║                                                                          ║
#  ║  STEP 4 — Install dependencies (Bash console on PythonAnywhere)         ║
#  ║        pip install --user flask python-dotenv requests                   ║
#  ║                                                                          ║
#  ║  STEP 5 — Set environment variables (Web tab → Environment variables)   ║
#  ║        SECRET_KEY   = any-long-random-string                             ║
#  ║        HF_TOKEN     = hf_xxxx  (get free at huggingface.co/settings)    ║
#  ║        DAILY_GOAL   = 20  (optional, default 20)                        ║
#  ║                                                                          ║
#  ║  STEP 6 — Reload the web app and open your site URL                     ║
#  ║                                                                          ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║                    LOCAL PYCHARM QUICK-START                             ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║                                                                          ║
#  ║    pip install flask python-dotenv requests                              ║
#  ║    Right-click → Run → open http://127.0.0.1:5000                       ║
#  ║                                                                          ║
#  ║    Optional .env file (same folder):                                     ║
#  ║        SECRET_KEY=changeme                                               ║
#  ║        HF_TOKEN=hf_xxxx                                                  ║
#  ║        DAILY_GOAL=20                                                     ║
#  ║                                                                          ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║                    DEFAULT ADMIN CREDENTIALS                             ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║                                                                          ║
#  ║    Username : Silabstechdialect                                          ║
#  ║    Password : Techdialect@2024                                           ║
#  ║                                                                          ║
#  ║    ⚠  Change the password after first login via the Admin panel.        ║
#  ║                                                                          ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║                    HOW THE AI WORKS (no local model)                    ║
#  ╠══════════════════════════════════════════════════════════════════════════╣
#  ║                                                                          ║
#  ║    Translation: exact DB match → fuzzy match → HuggingFace API          ║
#  ║    Model used: facebook/nllb-200-distilled-600M (free inference API)    ║
#  ║    Without HF_TOKEN: exact + fuzzy DB matching only (still useful)      ║
#  ║                                                                          ║
#  ║    HuggingFace free token: huggingface.co → Settings → Access Tokens    ║
#  ║                                                                          ║
#  ╚══════════════════════════════════════════════════════════════════════════╝
# =============================================================================

import os, csv, io, sqlite3, difflib, datetime, textwrap, json, re, hashlib
from functools import wraps

from flask import (
    Flask, request, render_template_string, redirect, url_for,
    flash, Response, session, jsonify, g
)
from dotenv import load_dotenv

try:
    import requests as http_requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from werkzeug.security import generate_password_hash, check_password_hash
    WERKZEUG_AVAILABLE = True
except ImportError:
    # Fallback for rare environments where werkzeug isn't installed separately
    def generate_password_hash(pw):
        return hashlib.sha256(pw.encode()).hexdigest()
    def check_password_hash(hashed, pw):
        return hashed == hashlib.sha256(pw.encode()).hexdigest()
    WERKZEUG_AVAILABLE = False

load_dotenv()

# =============================================================================
#  CONFIGURATION
# =============================================================================

SECRET_KEY       = os.getenv("SECRET_KEY", "techdialect-engine-dev-key-change-in-prod")
HF_TOKEN         = os.getenv("HF_TOKEN")        # HuggingFace Inference API token
DAILY_GOAL       = int(os.getenv("DAILY_GOAL", "20"))
SIMILARITY_THRESHOLD = 0.55
MAX_INPUT_CHARS  = 450
MAX_CHUNK_CHARS  = 400

# HuggingFace model for AI translation
# SCALABILITY NOTE: Change to any NLLB-compatible model here — nothing else changes.
HF_MODEL_URL     = "https://huggingface.co/meta-llama/Llama-3.2-3B"
SOURCE_LANG      = "eng_Latn"

# Database — uses absolute path so PythonAnywhere finds it from any working dir
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "techdialect.db")

# Sentence splitter for article chunking
SENTENCE_SPLIT   = re.compile(r'(?<=[.!?])\s+')

# Default admin credentials (created on first startup if no admin exists)
DEFAULT_ADMIN_USERNAME = "Silabstechdialect"
DEFAULT_ADMIN_PASSWORD = "Techdialect@2024"

# Broad category list — covers all domains of life, not just STEM
# SCALABILITY NOTE: Move to a categories table if users need to add categories
CATEGORIES = [
    # Everyday Life
    "Greetings & Farewells", "Family & Relationships", "Body & Health",
    "Food & Cooking", "Clothing & Fashion", "Housing & Community",
    "Travel & Direction", "Marketplace & Trade", "Money & Finance",
    "Time & Calendar", "Numbers & Counting", "Colors & Shapes",
    # Nature & Environment
    "Animals & Birds", "Plants & Trees", "Farming & Agriculture",
    "Weather & Seasons", "Land & Geography", "Water & Rivers",
    # Human Experience
    "Emotions & Feelings", "Character & Values", "Religion & Spirituality",
    "Proverbs & Idioms", "Arts & Music", "Sports & Games",
    "Celebrations & Culture", "History & Heritage",
    # Civic & Social
    "Government & Law", "Education & School", "Work & Occupation",
    "War & Conflict", "Media & Communication",
    # Language structure
    "Verbs & Actions", "Adjectives & Descriptions",
    "Conjunctions & Prepositions", "Sentence Starters",
    # STEM
    "Mathematics", "Biology", "Chemistry", "Physics",
    "Computer Science", "Engineering", "Medicine & Anatomy",
    "Environment & Ecology",
    # Catch-all
    "General",
]

# =============================================================================
#  FLASK APP
# =============================================================================

app = Flask(__name__)
app.secret_key = SECRET_KEY

# =============================================================================
#  DATABASE LAYER
#
#  Tables:
#    users        — registered accounts, admin-approved
#    languages    — user-proposed languages, admin-approved
#    translations — the core dataset
#    daily_log    — per-day entry counts for goal tracking
#
#  SCALABILITY NOTE: To migrate to PostgreSQL (e.g. on Heroku / Railway):
#    1. Replace sqlite3.connect() with psycopg2.connect(DATABASE_URL)
#    2. Change ? placeholders to %s
#    3. Change AUTOINCREMENT to SERIAL / BIGSERIAL
#    4. Add GIN index on english_text for full-text search
# =============================================================================

def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")   # better concurrency on PythonAnywhere
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create all tables, indexes, and the default admin account. Idempotent."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # ── Users ──────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'user',
            approved      INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT    NOT NULL
        )
    """)

    # ── Languages (user-managed, admin-approved) ───────────────────────────
    # SCALABILITY NOTE: Add a `region` or `country` column here when the
    # language list grows to cover many countries — useful for filtering.
    c.execute("""
        CREATE TABLE IF NOT EXISTS languages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE,
            nllb_code  TEXT,
            added_by   INTEGER,
            approved   INTEGER NOT NULL DEFAULT 0,
            created_at TEXT    NOT NULL,
            FOREIGN KEY (added_by) REFERENCES users(id)
        )
    """)

    # ── Translations ───────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            english_text TEXT    NOT NULL,
            local_text   TEXT    NOT NULL,
            target_lang  TEXT    NOT NULL,
            category     TEXT    NOT NULL DEFAULT 'General',
            source       TEXT    NOT NULL DEFAULT 'manual',
            added_by     INTEGER,
            created_at   TEXT    NOT NULL,
            UNIQUE (english_text, target_lang),
            FOREIGN KEY (added_by) REFERENCES users(id)
        )
    """)

    # ── Daily log ──────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_log (
            log_date TEXT    PRIMARY KEY,
            count    INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_trans_lang     ON translations (target_lang)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_trans_eng_lang ON translations (english_text, target_lang)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_trans_category ON translations (category)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_lang_approved  ON languages    (approved)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_approved ON users        (approved)")

    conn.commit()

    # ── Seed default admin if none exists ─────────────────────────────────
    existing_admin = conn.execute(
        "SELECT id FROM users WHERE role='admin' LIMIT 1"
    ).fetchone()

    if not existing_admin:
        conn.execute(
            """INSERT OR IGNORE INTO users
               (username, email, password_hash, role, approved, created_at)
               VALUES (?, ?, ?, 'admin', 1, ?)""",
            (
                DEFAULT_ADMIN_USERNAME,
                "admin@techdialect.com",
                generate_password_hash(DEFAULT_ADMIN_PASSWORD),
                datetime.datetime.utcnow().isoformat()
            )
        )
        conn.commit()
        print(f"  Default admin created: {DEFAULT_ADMIN_USERNAME}")

    # ── Seed default starter languages if languages table is empty ─────────
    starter_langs = [
        ("Tiv",             "tiv_Latn"),
        ("Yoruba",          "yor_Latn"),
        ("Hausa",           "hau_Arab"),
        ("Igbo",            "ibo_Latn"),
        ("Nigerian Pidgin", "pcm_Latn"),
    ]
    for name, code in starter_langs:
        c.execute(
            """INSERT OR IGNORE INTO languages
               (name, nllb_code, added_by, approved, created_at)
               VALUES (?, ?, NULL, 1, ?)""",
            (name, code, datetime.datetime.utcnow().isoformat())
        )
    conn.commit()
    conn.close()


# =============================================================================
#  DB HELPERS
# =============================================================================

def db_get_approved_languages():
    """Return all admin-approved languages, ordered alphabetically."""
    rows = get_db().execute(
        "SELECT * FROM languages WHERE approved=1 ORDER BY name"
    ).fetchall()
    return rows


def db_get_all_languages():
    """Return all languages (approved + pending) — for admin view."""
    return get_db().execute(
        "SELECT l.*, u.username as proposer FROM languages l "
        "LEFT JOIN users u ON l.added_by = u.id ORDER BY l.approved DESC, l.name"
    ).fetchall()


def db_lang_names():
    """Return a set of approved language names for validation."""
    return {r["name"] for r in db_get_approved_languages()}


def db_get_all_translations(lang=None, category=None, limit=None, added_by=None):
    wheres, params = [], []
    if lang:      wheres.append("target_lang=?"); params.append(lang)
    if category:  wheres.append("category=?");    params.append(category)
    if added_by:  wheres.append("added_by=?");    params.append(added_by)
    where_sql = ("WHERE " + " AND ".join(wheres)) if wheres else ""
    limit_sql = f"LIMIT {int(limit)}" if limit else ""
    return get_db().execute(
        f"SELECT t.*, u.username as contributor FROM translations t "
        f"LEFT JOIN users u ON t.added_by = u.id "
        f"{where_sql} ORDER BY t.created_at DESC {limit_sql}",
        params
    ).fetchall()


def db_exact_match(english, lang):
    return get_db().execute(
        "SELECT * FROM translations WHERE LOWER(english_text)=LOWER(?) AND target_lang=?",
        (english.strip(), lang)
    ).fetchone()


def db_insert_translation(english, local, lang, category, source="manual", added_by=None):
    """Insert translation. Returns True on success, False on duplicate."""
    try:
        db = get_db()
        db.execute(
            """INSERT INTO translations
               (english_text, local_text, target_lang, category, source, added_by, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (english.strip(), local.strip(), lang,
             category or "General", source, added_by,
             datetime.datetime.utcnow().isoformat())
        )
        db.commit()
        # Update daily log
        today = datetime.date.today().isoformat()
        db.execute(
            "INSERT INTO daily_log (log_date,count) VALUES (?,1) "
            "ON CONFLICT(log_date) DO UPDATE SET count=count+1",
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
    where_sql = ("WHERE " + " AND ".join(wheres)) if wheres else ""
    return get_db().execute(
        f"SELECT COUNT(*) FROM translations {where_sql}", params
    ).fetchone()[0]


def db_lang_counts():
    """Return dict of {lang_name: count} for all approved languages."""
    rows = get_db().execute(
        "SELECT target_lang, COUNT(*) as cnt FROM translations GROUP BY target_lang"
    ).fetchall()
    counts = {r["target_lang"]: r["cnt"] for r in rows}
    return counts


def db_coverage(lang):
    """Category coverage for a language — sorted empty-first."""
    rows = get_db().execute(
        "SELECT category, COUNT(*) as cnt FROM translations "
        "WHERE target_lang=? GROUP BY category", (lang,)
    ).fetchall()
    count_map = {r["category"]: r["cnt"] for r in rows}
    result = [{"category": c, "count": count_map.get(c, 0)} for c in CATEGORIES]
    result.sort(key=lambda x: x["count"])
    return result


# ── Daily stats ───────────────────────────────────────────────────────────────

def get_today_count():
    today = datetime.date.today().isoformat()
    row   = get_db().execute(
        "SELECT count FROM daily_log WHERE log_date=?", (today,)
    ).fetchone()
    return row["count"] if row else 0


def get_streak():
    rows  = get_db().execute(
        "SELECT log_date FROM daily_log WHERE count>0 ORDER BY log_date DESC"
    ).fetchall()
    if not rows:
        return 0
    dates = [datetime.date.fromisoformat(r["log_date"]) for r in rows]
    today = datetime.date.today()
    if dates[0] < today - datetime.timedelta(days=1):
        return 0
    streak, check = 0, today
    for d in dates:
        if d >= check - datetime.timedelta(days=1):
            streak += 1
            check   = d - datetime.timedelta(days=1)
        else:
            break
    return streak


def get_total_days():
    return get_db().execute(
        "SELECT COUNT(*) FROM daily_log WHERE count>0"
    ).fetchone()[0]


# =============================================================================
#  USER / AUTH HELPERS
# =============================================================================

def get_user_by_id(uid):
    return get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def get_user_by_username(username):
    return get_db().execute(
        "SELECT * FROM users WHERE username=?", (username,)
    ).fetchone()


def get_pending_users():
    return get_db().execute(
        "SELECT * FROM users WHERE approved=0 AND role='user' ORDER BY created_at DESC"
    ).fetchall()


def get_all_users():
    return get_db().execute(
        "SELECT * FROM users ORDER BY approved DESC, created_at DESC"
    ).fetchall()


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_user_by_id(uid)


def login_required(f):
    """Decorator: redirect to login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        u = current_user()
        if not u or not u["approved"]:
            session.clear()
            flash("Your account is pending admin approval.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator: only admin can access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        u = current_user()
        if not u or u["role"] != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# =============================================================================
#  TRANSLATION ENGINE  (3-tier: exact DB → fuzzy → HuggingFace API)
#
#  SCALABILITY NOTE: Extract this section to translation_service.py when
#  splitting into microservices. Routes only call translate(text, lang).
#  To swap AI backends, replace call_hf_api() — everything else stays.
# =============================================================================

def find_fuzzy(english, lang):
    """
    difflib similarity match against all stored phrases for a language.
    SCALABILITY NOTE: Replace with TF-IDF or FAISS index when > 50k rows.
    """
    rows = db_get_all_translations(lang)
    if not rows:
        return None, 0.0
    best_row, best_score = None, 0.0
    q = english.strip().lower()
    for row in rows:
        score = difflib.SequenceMatcher(None, q, row["english_text"].lower()).ratio()
        if score > best_score:
            best_score = score
            best_row   = row
    return (best_row, best_score) if best_score >= SIMILARITY_THRESHOLD else (None, best_score)


def _get_nllb_code(lang_name):
    """Look up the NLLB language code for a language from the DB."""
    row = get_db().execute(
        "SELECT nllb_code FROM languages WHERE name=? AND approved=1", (lang_name,)
    ).fetchone()
    return row["nllb_code"] if row and row["nllb_code"] else None


def call_hf_api(english, lang):
    """
    Translate via HuggingFace Inference API (free, needs HF_TOKEN env var).
    No local model — works on any hosting including PythonAnywhere free tier.

    SCALABILITY NOTE: To add rate limiting, wrap this with a Redis-backed
    token-bucket limiter. To cache API responses, store results in translations
    table with source='ai_cache'.
    """
    if not HF_TOKEN or not REQUESTS_AVAILABLE:
        return None

    nllb_code = _get_nllb_code(lang)
    if not nllb_code:
        return None

    safe_text = textwrap.shorten(english.strip(), width=MAX_INPUT_CHARS, placeholder="…")

    # Build a few-shot prompt with saved translations for this language
    examples = get_db().execute(
        "SELECT english_text, local_text FROM translations "
        "WHERE target_lang=? ORDER BY RANDOM() LIMIT 5",
        (lang,)
    ).fetchall()

    example_block = ""
    for ex in examples:
        example_block += f"English: {ex['english_text']}\n{lang}: {ex['local_text']}\n\n"

    prompt = (
        f"Translate the following English text to {lang}.\n"
        f"Keep the tone natural.\n\n"
        f"{example_block}"
        f"English: {safe_text}\n{lang}:"
    )

    try:
        resp = http_requests.post(
            HF_MODEL_URL,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 150,
                    "temperature":    0.3,
                    "do_sample":      False,
                }
            },
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            raw = data[0].get("generated_text", "").strip()
            # Strip prompt echo if model repeats the input
            if ":" in raw:
                raw = raw.split(":")[-1].strip()
            return raw or None
        if isinstance(data, dict):
            return data.get("generated_text", "").strip() or None
    except Exception as exc:
        print(f"  HF API error: {exc}")
    return None


def translate(english, lang):
    """
    Master 3-tier translation function.
    Returns a consistent dict consumed by both the UI and the REST API.
    """
    english = english.strip()
    if not english:
        return {"status": "error", "message": "Please enter some text."}
    if lang not in db_lang_names():
        return {"status": "error", "message": f"Unknown language: {lang}"}

    # Tier 1 — exact DB match
    row = db_exact_match(english, lang)
    if row:
        return {
            "status": "exact", "source": "Database (exact match)",
            "english": row["english_text"], "local": row["local_text"],
            "lang": lang, "category": row["category"], "saved": True
        }

    # Tier 2 — fuzzy DB match
    fuzzy_row, score = find_fuzzy(english, lang)
    if fuzzy_row:
        return {
            "status": "fuzzy",
            "source": f"Database (fuzzy — {score:.0%} similar)",
            "english": fuzzy_row["english_text"], "local": fuzzy_row["local_text"],
            "lang": lang, "category": fuzzy_row["category"],
            "score": score, "saved": True, "original_query": english
        }

    # Tier 3 — HuggingFace AI
    ai_text = call_hf_api(english, lang)
    if ai_text:
        return {
            "status": "ai", "source": f"AI (HuggingFace → {lang})",
            "english": english, "local": ai_text,
            "lang": lang, "category": "General", "saved": False
        }

    # Tier 4 — not found
    hint = "" if HF_TOKEN else " (set HF_TOKEN env var to enable AI)"
    return {
        "status": "not_found", "source": "Not found",
        "english": english, "local": "", "lang": lang, "saved": False,
        "message": f"No {lang} translation found{hint}. Add it manually below."
    }


# =============================================================================
#  ARTICLE TRANSLATION (paragraph chunking)
# =============================================================================

def split_into_chunks(text):
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) <= MAX_CHUNK_CHARS:
            chunks.append(para)
            continue
        sentences = SENTENCE_SPLIT.split(para)
        current   = ""
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(current) + len(sent) + 1 <= MAX_CHUNK_CHARS:
                current = (current + " " + sent).strip()
            else:
                if current:
                    chunks.append(current)
                if len(sent) > MAX_CHUNK_CHARS:
                    sent = textwrap.shorten(sent, width=MAX_CHUNK_CHARS, placeholder="…")
                current = sent
        if current:
            chunks.append(current)
    return [c for c in chunks if c.strip()]


def translate_article(text, lang):
    text = text.strip()
    if not text:
        return {"status": "error", "message": "No text provided."}
    if lang not in db_lang_names():
        return {"status": "error", "message": f"Unknown language: {lang}"}
    if not HF_TOKEN:
        return {
            "status":  "no_ai",
            "message": "HF_TOKEN environment variable not set. Article translation requires AI."
        }

    chunks  = split_into_chunks(text)
    results = []
    parts   = []

    for i, chunk in enumerate(chunks):
        db_row = db_exact_match(chunk, lang)
        if db_row:
            local = db_row["local_text"]
            src   = "db"
        else:
            local = call_hf_api(chunk, lang) or ""
            src   = "ai"
        results.append({"index": i, "english": chunk, "local": local, "source": src})
        if local:
            parts.append(local)

    return {
        "status":           "ok",
        "lang":             lang,
        "chunks":           results,
        "total_chunks":     len(results),
        "full_translation": "\n\n".join(parts),
    }


# =============================================================================
#  HTML TEMPLATES
#  SCALABILITY NOTE: When splitting into a proper frontend (React/Vue),
#  replace render_template_string() calls with render_template() pointing
#  to a templates/ folder. Every {{ variable }} stays identical.
# =============================================================================

# ── AUTH TEMPLATE ─────────────────────────────────────────────────────────────
AUTH_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Techdialect — {{ page_title }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <style>
    body { background:linear-gradient(135deg,#1a1a2e,#16213e); min-height:100vh;
           display:flex; align-items:center; justify-content:center;
           font-family:'Segoe UI',system-ui,sans-serif; }
    .auth-card { background:#fff; border-radius:1.2rem; padding:2.5rem 2rem;
                 box-shadow:0 8px 40px rgba(0,0,0,.35); width:100%; max-width:420px; }
    .brand { font-size:1.5rem; font-weight:900; color:#1a1a2e; letter-spacing:-.5px; }
    .brand span { color:#e85d04; }
    .sub { font-size:.78rem; color:#6c757d; margin-bottom:1.5rem; }
    .btn-primary { background:linear-gradient(135deg,#e85d04,#f48c06); border:none; font-weight:700; }
    .btn-primary:hover { background:linear-gradient(135deg,#c94d00,#e07a00); }
    .form-label { font-weight:600; font-size:.88rem; }
  </style>
</head>
<body>
<div class="auth-card">
  <div class="text-center mb-4">
    <div class="brand"><i class="bi bi-translate me-2"></i>Tech<span>dialect</span></div>
    <div class="sub">Nigerian Language Dataset Engine</div>
  </div>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }} py-2 small">{{ msg }}</div>
    {% endfor %}
  {% endwith %}
  {{ form_html | safe }}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ── MAIN APP TEMPLATE ─────────────────────────────────────────────────────────
MAIN_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Techdialect · {{ selected_lang }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <style>
    :root { --td:#e85d04; --primary:#0d6efd; --success:#198754; --bg:#f5f7ff; --radius:.9rem; }
    body  { background:var(--bg); font-family:'Segoe UI',system-ui,sans-serif; font-size:.95rem; }

    /* Navbar */
    .navbar { background:linear-gradient(135deg,#1a1a2e,#16213e) !important; }
    .brand-main { font-weight:800; font-size:1.15rem; color:#fff; letter-spacing:-.3px; }
    .brand-main span { color:#e85d04; }
    .brand-sub  { font-size:.68rem; color:#adb5bd; }

    /* Chips */
    .chip { background:#fff; border:1px solid #dee2e6; border-radius:2rem;
            padding:.26rem .8rem; font-size:.78rem; font-weight:600;
            display:inline-flex; align-items:center; gap:.3rem; }
    .chip.streak  { border-color:#f48c06; color:#e85d04; }
    .chip.goal    { border-color:#0d6efd; color:#0d6efd; }
    .chip.total   { border-color:#198754; color:#198754; }

    /* Goal bar */
    .goal-bar-wrap { background:#e9ecef; border-radius:2rem; height:9px; overflow:hidden; }
    .goal-bar { height:100%; border-radius:2rem;
                background:linear-gradient(90deg,#0d6efd,#20c997); transition:width .4s; }
    .goal-bar.done { background:linear-gradient(90deg,#198754,#20c997); }

    /* Cards */
    .card { border:none; border-radius:var(--radius); box-shadow:0 2px 14px rgba(0,0,0,.07); }
    .card-header { border-radius:var(--radius) var(--radius) 0 0 !important;
                   font-weight:600; font-size:.9rem; }

    /* Language pills */
    .lang-pill { padding:.26rem .8rem; border-radius:2rem; font-size:.78rem; font-weight:600;
                 text-decoration:none; border:2px solid transparent; transition:all .16s;
                 display:inline-flex; align-items:center; gap:.3rem; }
    .lang-pill.active   { background:var(--td); color:#fff; border-color:var(--td); }
    .lang-pill.inactive { background:#fff; color:#495057; border-color:#dee2e6; }
    .lang-pill.inactive:hover { border-color:var(--td); color:var(--td); }

    /* Quick entry */
    .quick-entry { background:linear-gradient(135deg,#1a1a2e,#16213e);
                   border-radius:var(--radius); padding:1.3rem; }
    .quick-entry .form-control,
    .quick-entry .form-select { background:#2a2a4a; border:1px solid #3a3a5c;
                                 color:#fff; border-radius:.5rem; }
    .quick-entry .form-control::placeholder { color:#adb5bd; }
    .quick-entry .form-control:focus,
    .quick-entry .form-select:focus { background:#2a2a4a; border-color:#e85d04; color:#fff;
                                       box-shadow:0 0 0 3px rgba(232,93,4,.2); }
    .quick-entry .form-select option { background:#2a2a4a; color:#fff; }
    .quick-entry label { color:#adb5bd; font-size:.76rem; font-weight:600;
                          text-transform:uppercase; letter-spacing:.05em; }
    .save-btn { background:linear-gradient(135deg,var(--td),#f48c06);
                border:none; color:#fff; font-weight:700; padding:.55rem 1.4rem;
                border-radius:.5rem; transition:transform .15s, box-shadow .15s; }
    .save-btn:hover { transform:translateY(-1px); box-shadow:0 4px 12px rgba(232,93,4,.4); color:#fff; }
    .ai-hint { background:#2a2a4a; border:1px solid #3a3a5c; border-radius:.5rem;
               padding:.4rem .7rem; font-size:.82rem; margin-top:.28rem;
               min-height:32px; display:flex; align-items:center; gap:.5rem; }
    .ai-hint-text { color:#fff; font-weight:600; cursor:pointer; }
    .ai-hint-text:hover { color:#f48c06; }

    /* Result */
    .result-box { border-radius:.75rem; padding:1rem 1.3rem; margin-top:.7rem;
                  border-left:4px solid var(--primary);
                  background:linear-gradient(135deg,#e8f4fd,#f0fff4); }
    .result-box.ai      { border-color:#6f42c1; background:linear-gradient(135deg,#f3e8ff,#fdf0ff); }
    .result-box.fuzzy   { border-color:#0d6efd; }
    .result-box.notfound{ border-color:#dc3545; background:#fff5f5; }
    .result-local { font-size:1.45rem; font-weight:800; color:#1a1a2e; line-height:1.3; }

    /* Article */
    .article-section { background:#fff; border-radius:var(--radius);
                       box-shadow:0 2px 14px rgba(0,0,0,.07); margin-bottom:2rem; }
    .article-header  { background:linear-gradient(135deg,#6f42c1,#0d6efd);
                       color:#fff; padding:.9rem 1.3rem;
                       border-radius:var(--radius) var(--radius) 0 0;
                       font-weight:700; font-size:.95rem;
                       display:flex; align-items:center; gap:.5rem; }
    .article-pane    { min-height:220px; resize:vertical; font-size:.9rem; line-height:1.7;
                       border:2px solid #dee2e6; border-radius:.6rem; padding:.8rem;
                       width:100%; font-family:'Segoe UI',system-ui,sans-serif; }
    .article-pane:focus { border-color:#6f42c1; outline:none;
                          box-shadow:0 0 0 3px rgba(111,66,193,.18); }
    .chunk-row { border-bottom:1px solid #f0f0f0; padding:.8rem 0; }
    .chunk-row:last-child { border-bottom:none; }
    .chunk-en  { color:#495057; font-size:.87rem; line-height:1.6; }
    .chunk-tiv { color:#1a1a2e; font-weight:600; font-size:.93rem; line-height:1.6; }
    .badge-ai  { background:#6f42c1; color:#fff; font-size:.67rem;
                 padding:.1rem .42rem; border-radius:.3rem; }
    .badge-db  { background:#198754; color:#fff; font-size:.67rem;
                 padding:.1rem .42rem; border-radius:.3rem; }
    .progress-art { height:7px; border-radius:2rem; background:#e9ecef;
                    overflow:hidden; margin:.6rem 0; }
    .progress-art-bar { height:100%; border-radius:2rem; width:0%;
                        background:linear-gradient(90deg,#6f42c1,#0d6efd); transition:width .3s; }
    .art-btn { background:linear-gradient(135deg,#6f42c1,#0d6efd); border:none; color:#fff;
               font-weight:700; padding:.55rem 1.5rem; border-radius:.5rem; }
    .art-btn:hover { opacity:.9; color:#fff; }
    .art-btn:disabled { opacity:.55; cursor:not-allowed; }

    /* Coverage */
    .cov-table th { font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; }
    .cov-table td { font-size:.8rem; vertical-align:middle !important; }

    /* Table */
    .tbl th { font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; }
    .tbl td { vertical-align:middle !important; font-size:.83rem; }

    /* Export btn */
    .export-btn { background:linear-gradient(135deg,#198754,#20c997); border:none; color:#fff;
                  font-weight:700; padding:.5rem 1.3rem; border-radius:2rem;
                  text-decoration:none; display:inline-block; font-size:.87rem; }
    .export-btn:hover { opacity:.9; color:#fff; }

    .big-num { font-size:2.2rem; font-weight:900; line-height:1; }
    .nav-tabs .nav-link { font-size:.83rem; font-weight:600; color:#6c757d; }
    .nav-tabs .nav-link.active { color:#1a1a2e; }

    @media(max-width:576px){ .result-local{font-size:1.1rem;} .big-num{font-size:1.6rem;} }
  </style>
</head>
<body>

<!-- NAVBAR -->
<nav class="navbar navbar-dark shadow-sm py-2">
  <div class="container-lg">
    <div class="d-flex align-items-center gap-3 flex-wrap">
      <div>
        <div class="brand-main"><i class="bi bi-translate me-2"></i>Tech<span>dialect</span></div>
        <div class="brand-sub">NIGERIAN LANGUAGE DATASET ENGINE</div>
      </div>
    </div>
    <div class="d-flex align-items-center gap-2 flex-wrap mt-1 mt-sm-0">
      {% if streak > 0 %}<span class="chip streak"><i class="bi bi-fire"></i>{{ streak }}d</span>{% endif %}
      <span class="chip goal"><i class="bi bi-bullseye"></i>{{ today_count }}/{{ daily_goal }}</span>
      <span class="chip total"><i class="bi bi-database-fill"></i>{{ total_count }}</span>
      {% if ai_active %}
        <span class="chip"><i class="bi bi-cpu text-success"></i>AI on</span>
      {% else %}
        <span class="chip"><i class="bi bi-cpu text-danger"></i>DB only</span>
      {% endif %}
      {% if user.role == 'admin' %}
        <a href="{{ url_for('admin_panel') }}" class="chip text-decoration-none text-warning">
          <i class="bi bi-shield-lock"></i>Admin
        </a>
      {% endif %}
      <a href="{{ url_for('propose_language') }}" class="chip text-decoration-none text-primary">
        <i class="bi bi-plus-circle"></i>Add Language
      </a>
      <a href="{{ url_for('logout') }}" class="chip text-decoration-none text-danger">
        <i class="bi bi-box-arrow-right"></i>{{ user.username }}
      </a>
    </div>
  </div>
</nav>

<!-- FLASH -->
<div class="container-lg mt-2">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }} alert-dismissible fade show py-2 small">
        {{ msg }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    {% endfor %}
  {% endwith %}
</div>

<!-- DAILY PROGRESS BAR -->
<div class="container-lg mt-2 mb-3">
  <div class="d-flex align-items-center gap-3">
    <div class="flex-grow-1">
      <div class="d-flex justify-content-between mb-1">
        <small class="fw-semibold text-muted">
          Today <span class="text-primary fw-bold">{{ today_count }}</span> / {{ daily_goal }} terms
        </small>
        <small class="text-muted">{{ total_days }} days active · {{ total_count }} total</small>
      </div>
      <div class="goal-bar-wrap">
        {% set pct = [today_count * 100 // daily_goal, 100] | min %}
        <div class="goal-bar {{ 'done' if today_count >= daily_goal else '' }}"
             style="width:{{ pct }}%"></div>
      </div>
    </div>
    {% if today_count >= daily_goal %}
      <span class="badge bg-success">Goal hit!</span>
    {% endif %}
  </div>
</div>

<!-- LANGUAGE SELECTOR -->
<div class="container-lg mb-3">
  <div class="d-flex align-items-center gap-2 flex-wrap">
    <small class="text-muted fw-semibold me-1"><i class="bi bi-globe2 me-1"></i>Language:</small>
    {% for lang in languages %}
      <a href="/?lang={{ lang.name | urlencode }}"
         class="lang-pill {{ 'active' if lang.name == selected_lang else 'inactive' }}">
        {{ lang.name }}
        <span style="opacity:.7;font-weight:400">({{ lang_counts.get(lang.name, 0) }})</span>
      </a>
    {% endfor %}
  </div>
</div>

<!-- MAIN CONTENT -->
<div class="container-lg pb-4">
  <div class="row g-4">

    <!-- LEFT COLUMN -->
    <div class="col-lg-7">

      <!-- QUICK ENTRY -->
      <div class="quick-entry mb-4">
        <div class="d-flex align-items-center justify-content-between mb-3">
          <h6 class="text-white mb-0 fw-bold">
            <i class="bi bi-lightning-charge-fill text-warning me-2"></i>Quick Entry
            <small class="text-muted fw-normal ms-2">add {{ selected_lang }} terms fast</small>
          </h6>
          <small class="text-muted"><kbd class="bg-dark text-white">Ctrl+Enter</kbd> to save</small>
        </div>
        <form method="POST" action="/add" id="quickForm">
          <input type="hidden" name="target_lang" value="{{ selected_lang }}">
          <div class="row g-2">
            <div class="col-md-4">
              <label>English Term</label>
              <input type="text" name="english_text" id="engInput"
                     class="form-control" placeholder="e.g. photosynthesis"
                     autocomplete="off" required>
            </div>
            <div class="col-md-4">
              <label>{{ selected_lang }} Translation</label>
              <input type="text" name="local_text" id="localInput"
                     class="form-control" placeholder="Translation…"
                     autocomplete="off" required>
              <div class="ai-hint d-none" id="aiHintBox">
                <i class="bi bi-cpu text-info"></i>
                <span class="text-muted me-1" style="font-size:.74rem">AI:</span>
                <span class="ai-hint-text" id="aiHintText" onclick="useHint()"></span>
                <span class="text-muted ms-auto" style="font-size:.7rem">click to use</span>
              </div>
            </div>
            <div class="col-md-3">
              <label>Category</label>
              <select name="category" id="catSelect" class="form-select">
                {% for cat in categories %}
                  <option value="{{ cat }}" {{ 'selected' if cat == last_category else '' }}>{{ cat }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-1 d-flex align-items-end">
              <button type="submit" class="save-btn w-100" title="Save">
                <i class="bi bi-plus-lg"></i>
              </button>
            </div>
          </div>
        </form>
      </div>

      <!-- LOOKUP -->
      <div class="card mb-4">
        <div class="card-header bg-primary text-white">
          <i class="bi bi-search me-2"></i>Look Up / Translate — English → {{ selected_lang }}
        </div>
        <div class="card-body">
          <form method="POST" action="/translate">
            <input type="hidden" name="target_lang" value="{{ selected_lang }}">
            <div class="input-group">
              <input type="text" name="english_text" class="form-control"
                     placeholder="Type English to search or translate…"
                     value="{{ last_query }}" maxlength="{{ max_chars }}" required>
              <button type="submit" class="btn btn-primary">
                <i class="bi bi-arrow-right-circle me-1"></i>Translate
              </button>
            </div>
          </form>
          {% if result %}
            {% set r = result %}
            <div class="result-box {{ r.status if r.status in ['ai','fuzzy','not_found'] else '' }}">
              <div class="mb-2">
                {% if   r.status == 'exact'     %}<span class="badge bg-success">{{ r.source }}</span>
                {% elif r.status == 'fuzzy'     %}<span class="badge bg-primary">{{ r.source }}</span>
                {% elif r.status == 'ai'        %}<span class="badge text-white" style="background:#6f42c1">{{ r.source }}</span>
                {% else                         %}<span class="badge bg-danger">{{ r.source }}</span>
                {% endif %}
              </div>
              {% if r.status in ['error','not_found'] %}
                <p class="text-danger mb-0 small">{{ r.get('message','') }}</p>
              {% else %}
                {% if r.status == 'fuzzy' and r.get('original_query') %}
                  <small class="text-muted d-block mb-1">You searched: "<em>{{ r.original_query }}</em>" → closest:</small>
                {% endif %}
                <div class="text-muted small mb-1"><strong>English:</strong> {{ r.english }}</div>
                <div class="result-local mb-1">{{ r.local }}</div>
                <small class="text-muted"><i class="bi bi-tag me-1"></i>{{ r.category or 'General' }}</small>
                {% if not r.saved %}
                  <hr class="my-2"/>
                  <p class="small text-muted mb-2"><i class="bi bi-info-circle me-1"></i>AI result — not saved. Save to improve future lookups.</p>
                  <form method="POST" action="/save" class="row g-2 align-items-end">
                    <input type="hidden" name="english_text" value="{{ r.english }}">
                    <input type="hidden" name="local_text"   value="{{ r.local }}">
                    <input type="hidden" name="target_lang"  value="{{ r.lang }}">
                    <div class="col-sm-5">
                      <select name="category" class="form-select form-select-sm">
                        {% for cat in categories %}<option>{{ cat }}</option>{% endfor %}
                      </select>
                    </div>
                    <div class="col-sm-4">
                      <button type="submit" class="btn btn-success btn-sm w-100">
                        <i class="bi bi-cloud-upload me-1"></i>Save
                      </button>
                    </div>
                  </form>
                {% endif %}
              {% endif %}
            </div>
          {% endif %}
        </div>
      </div>

      <!-- RECENT ENTRIES -->
      <div class="card">
        <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
          <span><i class="bi bi-clock-history me-2"></i>Recent {{ selected_lang }} Entries</span>
          <span class="badge bg-secondary">{{ lang_counts.get(selected_lang, 0) }} total</span>
        </div>
        <div class="card-body p-0">
          {% if recent_entries %}
            <div class="table-responsive" style="max-height:340px;overflow-y:auto;">
              <table class="table table-sm table-hover tbl mb-0">
                <thead class="table-light sticky-top">
                  <tr><th>English</th><th>{{ selected_lang }}</th><th>Category</th><th>By</th></tr>
                </thead>
                <tbody>
                  {% for t in recent_entries %}
                  <tr>
                    <td>{{ t.english_text }}</td>
                    <td class="fw-semibold text-primary">{{ t.local_text }}</td>
                    <td><span class="badge bg-light text-dark border" style="font-size:.68rem">{{ t.category }}</span></td>
                    <td class="text-muted" style="font-size:.78rem">{{ t.contributor or '—' }}</td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          {% else %}
            <div class="text-center py-4 text-muted">
              <i class="bi bi-database-slash fs-2 d-block mb-2"></i>
              No {{ selected_lang }} entries yet — use Quick Entry above!
            </div>
          {% endif %}
        </div>
      </div>

    </div><!-- /left -->

    <!-- RIGHT COLUMN -->
    <div class="col-lg-5">

      <!-- TODAY STATS -->
      <div class="card mb-4">
        <div class="card-header" style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;">
          <i class="bi bi-calendar3 me-2"></i>Today · {{ today_date }}
        </div>
        <div class="card-body">
          <div class="row text-center g-2">
            <div class="col-4">
              <div class="big-num text-primary">{{ today_count }}</div>
              <small class="text-muted">Added today</small>
            </div>
            <div class="col-4">
              <div class="big-num text-success">{{ daily_goal }}</div>
              <small class="text-muted">Daily goal</small>
            </div>
            <div class="col-4">
              <div class="big-num" style="color:var(--td)">{{ streak }}</div>
              <small class="text-muted">Day streak</small>
            </div>
          </div>
          <div class="goal-bar-wrap mt-3">
            {% set pct = [today_count * 100 // daily_goal, 100] | min %}
            <div class="goal-bar {{ 'done' if today_count >= daily_goal else '' }}"
                 style="width:{{ pct }}%"></div>
          </div>
          <div class="text-center mt-2">
            <small class="text-muted">
              {% set rem = daily_goal - today_count %}
              {% if rem > 0 %}
                <span class="text-primary fw-semibold">{{ rem }} more</span> to hit today's goal
              {% else %}
                <span class="text-success fw-semibold">🎉 Goal complete!</span>
              {% endif %}
            </small>
          </div>
        </div>
      </div>

      <!-- TABS -->
      <div class="card">
        <div class="card-header p-0 border-0 bg-transparent">
          <ul class="nav nav-tabs px-3 pt-2">
            <li class="nav-item">
              <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tabCov">
                <i class="bi bi-grid-3x3-gap me-1"></i>Coverage
              </button>
            </li>
            <li class="nav-item">
              <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabUp">
                <i class="bi bi-upload me-1"></i>Upload
              </button>
            </li>
            <li class="nav-item">
              <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabEx">
                <i class="bi bi-download me-1"></i>Export
              </button>
            </li>
          </ul>
        </div>
        <div class="card-body tab-content pt-3">

          <!-- COVERAGE -->
          <div class="tab-pane fade show active" id="tabCov">
            <p class="text-muted small mb-2">
              <strong>{{ selected_lang }}</strong> terms per category — sorted empty-first.
            </p>
            {% if coverage_rows %}
              <div class="table-responsive" style="max-height:400px;overflow-y:auto;">
                <table class="table table-sm mb-0 cov-table">
                  <thead class="table-light sticky-top">
                    <tr><th style="min-width:130px">Category</th><th class="text-center">Terms</th><th>Bar</th></tr>
                  </thead>
                  <tbody>
                    {% for row in coverage_rows %}
                    <tr>
                      <td class="small fw-semibold">{{ row.category }}</td>
                      <td class="text-center">
                        {% if row.count > 0 %}
                          <span class="badge {{ 'bg-success' if row.count >= 20 else 'bg-warning text-dark' }}">{{ row.count }}</span>
                        {% else %}
                          <span class="text-muted small">—</span>
                        {% endif %}
                      </td>
                      <td>
                        <div class="goal-bar-wrap" style="height:6px;">
                          {% set pct = [row.count * 100 // 20, 100] | min %}
                          <div class="goal-bar {{ 'done' if row.count >= 20 else '' }}"
                               style="width:{{ pct }}%"></div>
                        </div>
                      </td>
                    </tr>
                    {% endfor %}
                  </tbody>
                </table>
              </div>
            {% else %}
              <div class="text-center py-3 text-muted">
                <i class="bi bi-bar-chart-line fs-2 d-block mb-2"></i>No entries yet.
              </div>
            {% endif %}
          </div>

          <!-- UPLOAD -->
          <div class="tab-pane fade" id="tabUp">
            <p class="text-muted small mb-3">
              Required columns: <code>english_text</code>, <code>local_text</code>.<br>
              Optional: <code>category</code>, <code>target_lang</code>
              (defaults to <strong>{{ selected_lang }}</strong>).
            </p>
            <form method="POST" action="/upload_csv" enctype="multipart/form-data">
              <input type="hidden" name="target_lang" value="{{ selected_lang }}">
              <div class="mb-3">
                <input type="file" name="csv_file" class="form-control" accept=".csv" required>
              </div>
              <button type="submit" class="btn btn-warning text-dark fw-semibold w-100">
                <i class="bi bi-upload me-2"></i>Upload CSV
              </button>
            </form>
          </div>

          <!-- EXPORT -->
          <div class="tab-pane fade" id="tabEx">
            <p class="text-muted small mb-3">Download your dataset as CSV.</p>
            <div class="d-grid gap-2">
              <a href="/export_csv?lang={{ selected_lang | urlencode }}" class="export-btn text-center">
                <i class="bi bi-download me-2"></i>Export {{ selected_lang }}
                ({{ lang_counts.get(selected_lang, 0) }} terms)
              </a>
              <a href="/export_csv" class="btn btn-outline-success fw-semibold">
                <i class="bi bi-download me-1"></i>Export ALL ({{ total_count }} terms)
              </a>
            </div>
            <hr class="my-3"/>
            <p class="text-muted small mb-1"><strong>REST API:</strong></p>
            <code style="font-size:.76rem">/api/translate?text=hello&lang={{ selected_lang | urlencode }}</code><br>
            <code style="font-size:.76rem">/api/languages</code> &nbsp;
            <code style="font-size:.76rem">/api/stats</code>
          </div>

        </div>
      </div>

    </div><!-- /right -->
  </div>
</div>

<!-- ARTICLE TRANSLATION -->
<div class="container-lg pb-4">
  <div class="article-section">
    <div class="article-header">
      <i class="bi bi-file-text"></i>
      Article / Long Text Translation
      <span style="font-weight:400;font-size:.78rem;opacity:.85;margin-left:.4rem">
        — paste any paragraph, article or essay
      </span>
      {% if not ai_active %}
        <span class="badge bg-warning text-dark ms-auto" style="font-size:.7rem">
          <i class="bi bi-exclamation-triangle me-1"></i>Needs HF_TOKEN
        </span>
      {% endif %}
    </div>
    <div class="p-3 p-md-4">
      <div class="row g-3 mb-3">
        <div class="col-lg-6">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <label class="fw-semibold small text-muted"><i class="bi bi-pencil-square me-1"></i>English Text</label>
            <span class="text-muted small" id="charCount">0 chars</span>
          </div>
          <textarea id="articleInput" class="article-pane" rows="10"
                    placeholder="Paste your article or paragraph here…"></textarea>
        </div>
        <div class="col-lg-6">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <label class="fw-semibold small text-muted"><i class="bi bi-translate me-1"></i>Translation</label>
            <div class="d-flex gap-2">
              <button class="btn btn-outline-secondary btn-sm d-none" id="copyBtn" onclick="copyTranslation()">
                <i class="bi bi-clipboard me-1"></i>Copy
              </button>
              <button class="btn btn-outline-success btn-sm d-none" id="dlBtn" onclick="downloadTranslation()">
                <i class="bi bi-download me-1"></i>Save
              </button>
            </div>
          </div>
          <textarea id="articleOutput" class="article-pane" rows="10"
                    placeholder="Translation appears here…" readonly></textarea>
        </div>
      </div>
      <div class="d-flex align-items-center gap-3 flex-wrap mb-3">
        <div class="d-flex align-items-center gap-2">
          <label class="fw-semibold small text-muted mb-0">Language:</label>
          <select id="articleLang" class="form-select form-select-sm" style="width:auto">
            {% for lang in languages %}
              <option value="{{ lang.name }}" {{ 'selected' if lang.name == selected_lang else '' }}>
                {{ lang.name }}
              </option>
            {% endfor %}
          </select>
        </div>
        <button class="art-btn" id="artBtn" onclick="translateArticle()"
                {{ 'disabled' if not ai_active else '' }}>
          <i class="bi bi-arrow-right-circle me-2"></i>Translate Article
        </button>
        <button class="btn btn-outline-secondary btn-sm d-none" id="clearBtn" onclick="clearArticle()">
          <i class="bi bi-x-circle me-1"></i>Clear
        </button>
        <span class="text-muted small ms-auto d-none" id="artStatus"></span>
      </div>
      <div class="progress-art d-none" id="artProgress">
        <div class="progress-art-bar" id="artProgressBar"></div>
      </div>
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

<!-- FOOTER -->
<footer class="text-center text-muted small py-3 border-top bg-white">
  Techdialect Engine v5.0 &nbsp;·&nbsp;
  Logged in as <strong>{{ user.username }}</strong> &nbsp;·&nbsp;
  <a href="/export_csv" class="text-success text-decoration-none fw-semibold">
    <i class="bi bi-download"></i> Export All
  </a>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
// Auto-focus quick entry
window.addEventListener('DOMContentLoaded', function() {
  var eng = document.getElementById('engInput');
  if (eng) eng.focus();
});

// Ctrl+Enter to submit quick form
document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    var f = document.getElementById('quickForm');
    if (f) f.submit();
  }
});

// AI hint while typing
var hintTimer = null;
var engInput  = document.getElementById('engInput');
var localInput= document.getElementById('localInput');
var hintBox   = document.getElementById('aiHintBox');
var hintText  = document.getElementById('aiHintText');
var selLang   = "{{ selected_lang }}";
var aiActive  = {{ 'true' if ai_active else 'false' }};

function useHint() {
  if (hintText && localInput) { localInput.value = hintText.textContent; localInput.focus(); }
}

if (engInput && aiActive) {
  engInput.addEventListener('input', function() {
    clearTimeout(hintTimer);
    var v = engInput.value.trim();
    if (v.length < 3) { if (hintBox) hintBox.classList.add('d-none'); return; }
    hintTimer = setTimeout(function() {
      if (localInput && localInput.value.trim()) return;
      fetch('/api/translate?text=' + encodeURIComponent(v) + '&lang=' + encodeURIComponent(selLang))
        .then(function(r){ return r.json(); })
        .then(function(d){
          if (d.local && d.status !== 'not_found' && d.status !== 'error') {
            hintText.textContent = d.local;
            hintBox.classList.remove('d-none');
          } else { hintBox.classList.add('d-none'); }
        }).catch(function(){ hintBox.classList.add('d-none'); });
    }, 900);
  });
}

// ── Article translation ───────────────────────────────────────────────────
var artLang   = document.getElementById('articleLang');
var artInput  = document.getElementById('articleInput');
var artOutput = document.getElementById('articleOutput');
var artStatus = document.getElementById('artStatus');
var artProg   = document.getElementById('artProgress');
var artProgBar= document.getElementById('artProgressBar');
var artBtn    = document.getElementById('artBtn');
var artWrap   = document.getElementById('artResultWrap');
var chunkRes  = document.getElementById('chunkResults');
var chunkBadge= document.getElementById('chunkBadge');
var copyBtn   = document.getElementById('copyBtn');
var dlBtn     = document.getElementById('dlBtn');
var clearBtn  = document.getElementById('clearBtn');
var charCount = document.getElementById('charCount');

if (artInput) {
  artInput.addEventListener('input', function() {
    if (charCount) charCount.textContent = artInput.value.length.toLocaleString() + ' chars';
  });
}

function setStatus(msg, col) {
  if (!artStatus) return;
  artStatus.textContent = msg;
  artStatus.className = 'text-' + (col||'muted') + ' small ms-auto';
  artStatus.classList.remove('d-none');
}
function setProg(pct) {
  if (!artProg) return;
  artProg.classList.remove('d-none');
  artProgBar.style.width = Math.min(pct,100) + '%';
}

function translateArticle() {
  var text = artInput ? artInput.value.trim() : '';
  var lang = artLang ? artLang.value : selLang;
  if (!text) { setStatus('Paste some text first.','danger'); return; }

  if (artBtn)    { artBtn.disabled=true; artBtn.innerHTML='<i class="bi bi-hourglass-split me-2"></i>Translating…'; }
  if (artOutput)  artOutput.value='';
  if (chunkRes)   chunkRes.innerHTML='';
  if (artWrap)    artWrap.style.display='none';
  if (copyBtn)    copyBtn.classList.add('d-none');
  if (dlBtn)      dlBtn.classList.add('d-none');
  if (clearBtn)   clearBtn.classList.remove('d-none');
  setProg(8);
  setStatus('Sending to AI…','primary');

  fetch('/translate_article', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({text:text, lang:lang})
  })
  .then(function(r){ return r.json(); })
  .then(function(d){
    if (d.status==='error'||d.status==='no_ai') {
      setProg(0); artProg.classList.add('d-none');
      setStatus(d.message||'Failed.','danger');
      if (artBtn) { artBtn.disabled=false; artBtn.innerHTML='<i class="bi bi-arrow-right-circle me-2"></i>Translate Article'; }
      return;
    }
    if (artOutput) artOutput.value = d.full_translation||'';
    setProg(100);
    setStatus('Done — '+d.total_chunks+' chunk'+(d.total_chunks!==1?'s':'')+' translated.','success');
    if (copyBtn) copyBtn.classList.remove('d-none');
    if (dlBtn)   dlBtn.classList.remove('d-none');
    if (chunkRes && d.chunks && d.chunks.length) {
      if (chunkBadge) chunkBadge.textContent = d.chunks.length+' paragraphs';
      var html='';
      d.chunks.forEach(function(c){
        var b = c.source==='db'
          ? '<span class="badge-db">DB</span>'
          : '<span class="badge-ai">AI</span>';
        html+='<div class="chunk-row"><div class="row g-2">'
          +'<div class="col-md-6 chunk-en">'+esc(c.english)+'</div>'
          +'<div class="col-md-6 chunk-tiv">'+b+' '+esc(c.local||'—')+'</div>'
          +'</div></div>';
      });
      chunkRes.innerHTML=html;
      artWrap.style.display='block';
    }
    if (artBtn) { artBtn.disabled=false; artBtn.innerHTML='<i class="bi bi-arrow-right-circle me-2"></i>Translate Article'; }
  })
  .catch(function(e){ setStatus('Error: '+e,'danger'); if(artBtn){artBtn.disabled=false;} });
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function copyTranslation() {
  if(!artOutput) return;
  navigator.clipboard.writeText(artOutput.value).then(function(){
    var o=copyBtn.innerHTML; copyBtn.innerHTML='<i class="bi bi-check me-1"></i>Copied!';
    setTimeout(function(){ copyBtn.innerHTML=o; },1800);
  });
}
function downloadTranslation() {
  var t=artOutput?artOutput.value:'', lang=artLang?artLang.value:'translation';
  var a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([t],{type:'text/plain;charset=utf-8'}));
  a.download='techdialect_'+lang.toLowerCase().replace(/\s+/g,'_')+'_translation.txt';
  a.click();
}
function clearArticle() {
  if(artInput)  artInput.value='';
  if(artOutput) artOutput.value='';
  if(chunkRes)  chunkRes.innerHTML='';
  if(artWrap)   artWrap.style.display='none';
  if(artProg)  { artProg.classList.add('d-none'); artProgBar.style.width='0%'; }
  if(artStatus) artStatus.classList.add('d-none');
  if(copyBtn)   copyBtn.classList.add('d-none');
  if(dlBtn)     dlBtn.classList.add('d-none');
  if(clearBtn)  clearBtn.classList.add('d-none');
  if(charCount) charCount.textContent='0 chars';
  if(artInput)  artInput.focus();
}
</script>
</body>
</html>
"""

# ── ADMIN TEMPLATE ─────────────────────────────────────────────────────────────
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Techdialect Admin</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <style>
    body { background:#f5f7ff; font-family:'Segoe UI',system-ui,sans-serif; }
    .navbar { background:linear-gradient(135deg,#1a1a2e,#16213e) !important; }
    .brand  { font-weight:800; color:#fff; font-size:1.1rem; }
    .brand span { color:#e85d04; }
    .card   { border:none; border-radius:.9rem; box-shadow:0 2px 14px rgba(0,0,0,.07); }
    .card-header { border-radius:.9rem .9rem 0 0 !important; font-weight:600; }
    th { font-size:.76rem; text-transform:uppercase; letter-spacing:.04em; }
    td { vertical-align:middle !important; font-size:.85rem; }
  </style>
</head>
<body>
<nav class="navbar navbar-dark shadow-sm py-2 mb-4">
  <div class="container">
    <span class="brand"><i class="bi bi-shield-lock me-2"></i>Tech<span>dialect</span> Admin</span>
    <div>
      <a href="{{ url_for('dashboard') }}" class="btn btn-outline-light btn-sm me-2">
        <i class="bi bi-arrow-left me-1"></i>Dashboard
      </a>
      <a href="{{ url_for('logout') }}" class="btn btn-outline-danger btn-sm">Logout</a>
    </div>
  </div>
</nav>
<div class="container pb-5">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }} alert-dismissible fade show py-2 small">
        {{ msg }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    {% endfor %}
  {% endwith %}

  <div class="row g-4">

    <!-- Pending Users -->
    <div class="col-lg-6">
      <div class="card">
        <div class="card-header bg-warning text-dark">
          <i class="bi bi-person-exclamation me-2"></i>Pending Approvals
          <span class="badge bg-dark ms-2">{{ pending_users | length }}</span>
        </div>
        <div class="card-body p-0">
          {% if pending_users %}
            <table class="table table-sm table-hover mb-0">
              <thead class="table-light"><tr><th>Username</th><th>Email</th><th>Registered</th><th></th></tr></thead>
              <tbody>
                {% for u in pending_users %}
                <tr>
                  <td class="fw-semibold">{{ u.username }}</td>
                  <td class="text-muted">{{ u.email }}</td>
                  <td class="text-muted small">{{ u.created_at[:10] }}</td>
                  <td>
                    <form method="POST" action="/admin/approve/{{ u.id }}" class="d-inline">
                      <button class="btn btn-success btn-sm">Approve</button>
                    </form>
                    <form method="POST" action="/admin/reject/{{ u.id }}" class="d-inline ms-1">
                      <button class="btn btn-danger btn-sm">Reject</button>
                    </form>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          {% else %}
            <div class="text-center py-4 text-muted small">
              <i class="bi bi-check-circle fs-2 d-block mb-2 text-success"></i>
              No pending approvals.
            </div>
          {% endif %}
        </div>
      </div>
    </div>

    <!-- Pending Languages -->
    <div class="col-lg-6">
      <div class="card">
        <div class="card-header bg-info text-white">
          <i class="bi bi-globe2 me-2"></i>Language Proposals
          <span class="badge bg-white text-dark ms-2">{{ pending_langs | length }} pending</span>
        </div>
        <div class="card-body p-0">
          {% if pending_langs %}
            <table class="table table-sm table-hover mb-0">
              <thead class="table-light"><tr><th>Language</th><th>NLLB Code</th><th>Proposed by</th><th></th></tr></thead>
              <tbody>
                {% for l in pending_langs %}
                <tr>
                  <td class="fw-semibold">{{ l.name }}</td>
                  <td><code>{{ l.nllb_code or '—' }}</code></td>
                  <td class="text-muted small">{{ l.proposer or 'system' }}</td>
                  <td>
                    <form method="POST" action="/admin/approve_lang/{{ l.id }}" class="d-inline">
                      <button class="btn btn-success btn-sm">Approve</button>
                    </form>
                    <form method="POST" action="/admin/reject_lang/{{ l.id }}" class="d-inline ms-1">
                      <button class="btn btn-danger btn-sm">Reject</button>
                    </form>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          {% else %}
            <div class="text-center py-4 text-muted small">
              <i class="bi bi-check-circle fs-2 d-block mb-2 text-success"></i>
              No pending language proposals.
            </div>
          {% endif %}
        </div>
      </div>
    </div>

    <!-- All Users -->
    <div class="col-12">
      <div class="card">
        <div class="card-header bg-dark text-white">
          <i class="bi bi-people me-2"></i>All Users
        </div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-sm table-hover mb-0">
              <thead class="table-light">
                <tr><th>#</th><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th>Joined</th><th>Contributions</th></tr>
              </thead>
              <tbody>
                {% for u in all_users %}
                <tr>
                  <td class="text-muted">{{ u.id }}</td>
                  <td class="fw-semibold">{{ u.username }}</td>
                  <td class="text-muted">{{ u.email }}</td>
                  <td>
                    <span class="badge {{ 'bg-danger' if u.role == 'admin' else 'bg-secondary' }}">{{ u.role }}</span>
                  </td>
                  <td>
                    <span class="badge {{ 'bg-success' if u.approved else 'bg-warning text-dark' }}">
                      {{ 'Active' if u.approved else 'Pending' }}
                    </span>
                  </td>
                  <td class="text-muted small">{{ u.created_at[:10] }}</td>
                  <td class="text-muted">{{ user_contrib.get(u.id, 0) }}</td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- All Languages -->
    <div class="col-12">
      <div class="card">
        <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
          <span><i class="bi bi-translate me-2"></i>All Languages</span>
          <a href="{{ url_for('propose_language') }}" class="btn btn-light btn-sm">
            <i class="bi bi-plus me-1"></i>Add Language
          </a>
        </div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-sm table-hover mb-0">
              <thead class="table-light">
                <tr><th>#</th><th>Name</th><th>NLLB Code</th><th>Status</th><th>Proposed by</th><th>Terms</th></tr>
              </thead>
              <tbody>
                {% for l in all_langs %}
                <tr>
                  <td class="text-muted">{{ l.id }}</td>
                  <td class="fw-semibold">{{ l.name }}</td>
                  <td><code>{{ l.nllb_code or '—' }}</code></td>
                  <td>
                    <span class="badge {{ 'bg-success' if l.approved else 'bg-warning text-dark' }}">
                      {{ 'Live' if l.approved else 'Pending' }}
                    </span>
                  </td>
                  <td class="text-muted small">{{ l.proposer or 'system' }}</td>
                  <td class="text-muted">{{ lang_counts.get(l.name, 0) }}</td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ── PROPOSE LANGUAGE TEMPLATE ──────────────────────────────────────────────────
PROPOSE_LANG_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Techdialect — Propose Language</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <style>
    body { background:#f5f7ff; font-family:'Segoe UI',system-ui,sans-serif;
           display:flex; align-items:center; justify-content:center; min-height:100vh; }
    .card { border:none; border-radius:1rem; box-shadow:0 4px 24px rgba(0,0,0,.1);
             padding:2rem; max-width:480px; width:100%; }
    .brand { font-weight:800; color:#1a1a2e; }
    .brand span { color:#e85d04; }
  </style>
</head>
<body>
<div class="card">
  <div class="mb-4 text-center">
    <div class="brand fs-4"><i class="bi bi-translate me-2"></i>Tech<span>dialect</span></div>
    <p class="text-muted small mt-1">Propose a new language for the dataset engine</p>
  </div>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }} py-2 small">{{ msg }}</div>
    {% endfor %}
  {% endwith %}
  <form method="POST">
    <div class="mb-3">
      <label class="form-label fw-semibold">Language Name <span class="text-danger">*</span></label>
      <input type="text" name="name" class="form-control"
             placeholder="e.g. Fulfulde, Kanuri, Efik, Ibibio" required>
    </div>
    <div class="mb-3">
      <label class="form-label fw-semibold">NLLB-200 Language Code
        <small class="text-muted fw-normal">(optional but recommended for AI)</small>
      </label>
      <input type="text" name="nllb_code" class="form-control" placeholder="e.g. fuv_Latn, kau_Arab">
      <div class="form-text">
        Find your code at
        <a href="https://github.com/facebookresearch/flores/blob/main/flores200/README.md"
           target="_blank">FLORES-200 language list</a>.
        Format: <code>iso_Script</code> e.g. <code>yor_Latn</code>
      </div>
    </div>
    <div class="alert alert-info py-2 small">
      <i class="bi bi-info-circle me-1"></i>
      Your proposal will be reviewed by an admin before going live.
      Approved languages appear in the language selector for all users.
    </div>
    <div class="d-flex gap-2">
      <button type="submit" class="btn btn-primary fw-semibold flex-grow-1">
        <i class="bi bi-send me-2"></i>Submit Proposal
      </button>
      <a href="{{ url_for('dashboard') }}" class="btn btn-outline-secondary">Cancel</a>
    </div>
  </form>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


# =============================================================================
#  RENDER HELPER
# =============================================================================

def render_main(result=None, last_query="", last_category="General", lang=None):
    if lang is None:
        lang = session.get("selected_lang", "Tiv")

    languages = db_get_approved_languages()
    lang_names = [l["name"] for l in languages]
    if lang not in lang_names:
        lang = lang_names[0] if lang_names else ""

    u = current_user()
    return render_template_string(
        MAIN_HTML,
        result        = result,
        last_query    = last_query,
        last_category = session.get("last_category", last_category),
        selected_lang = lang,
        languages     = languages,
        lang_counts   = db_lang_counts(),
        categories    = CATEGORIES,
        today_count   = get_today_count(),
        daily_goal    = DAILY_GOAL,
        streak        = get_streak(),
        total_count   = db_count(),
        total_days    = get_total_days(),
        today_date    = datetime.date.today().strftime("%d %b %Y"),
        recent_entries= db_get_all_translations(lang, limit=50),
        coverage_rows = db_coverage(lang),
        ai_active     = bool(HF_TOKEN and REQUESTS_AVAILABLE),
        max_chars     = MAX_INPUT_CHARS,
        user          = u,
    )


# =============================================================================
#  AUTH ROUTES
# =============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        u = get_user_by_username(username)
        if not u or not check_password_hash(u["password_hash"], password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))
        if not u["approved"]:
            flash("Your account is awaiting admin approval.", "warning")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"]  = u["id"]
        session["username"] = u["username"]
        session["role"]     = u["role"]
        flash(f"Welcome back, {u['username']}!", "success")
        return redirect(url_for("dashboard"))

    form_html = """
    <form method="POST">
      <h5 class="fw-bold mb-4">Sign In</h5>
      <div class="mb-3">
        <label class="form-label">Username</label>
        <input type="text" name="username" class="form-control" required autofocus>
      </div>
      <div class="mb-3">
        <label class="form-label">Password</label>
        <input type="password" name="password" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-100 mb-3">Sign In</button>
      <div class="text-center">
        <small class="text-muted">No account? <a href="/register">Register here</a></small>
      </div>
    </form>
    """
    return render_template_string(AUTH_HTML, page_title="Login", form_html=form_html)


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("register"))

        try:
            db = get_db()
            db.execute(
                """INSERT INTO users (username, email, password_hash, role, approved, created_at)
                   VALUES (?, ?, ?, 'user', 0, ?)""",
                (username, email, generate_password_hash(password),
                 datetime.datetime.utcnow().isoformat())
            )
            db.commit()
            flash(
                "Account created! An admin will review and approve it shortly. "
                "You'll be able to log in once approved.",
                "success"
            )
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "danger")
            return redirect(url_for("register"))

    form_html = """
    <form method="POST">
      <h5 class="fw-bold mb-4">Create Account</h5>
      <div class="mb-3">
        <label class="form-label">Username</label>
        <input type="text" name="username" class="form-control" required autofocus>
      </div>
      <div class="mb-3">
        <label class="form-label">Email</label>
        <input type="email" name="email" class="form-control" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Password</label>
        <input type="password" name="password" class="form-control" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Confirm Password</label>
        <input type="password" name="confirm" class="form-control" required>
      </div>
      <div class="alert alert-info py-2 small mb-3">
        <i class="bi bi-info-circle me-1"></i>
        After registering, an admin must approve your account before you can log in.
      </div>
      <button type="submit" class="btn btn-primary w-100 mb-3">Register</button>
      <div class="text-center">
        <small class="text-muted">Have an account? <a href="/login">Sign in</a></small>
      </div>
    </form>
    """
    return render_template_string(AUTH_HTML, page_title="Register", form_html=form_html)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# =============================================================================
#  ADMIN ROUTES
# =============================================================================

@app.route("/admin")
@login_required
@admin_required
def admin_panel():
    db = get_db()
    # Per-user contribution counts
    rows = db.execute(
        "SELECT added_by, COUNT(*) as cnt FROM translations GROUP BY added_by"
    ).fetchall()
    user_contrib = {r["added_by"]: r["cnt"] for r in rows}

    pending_langs = db.execute(
        "SELECT l.*, u.username as proposer FROM languages l "
        "LEFT JOIN users u ON l.added_by = u.id WHERE l.approved=0"
    ).fetchall()

    return render_template_string(
        ADMIN_HTML,
        pending_users = get_pending_users(),
        all_users     = get_all_users(),
        pending_langs = pending_langs,
        all_langs     = db_get_all_languages(),
        lang_counts   = db_lang_counts(),
        user_contrib  = user_contrib,
    )


@app.route("/admin/approve/<int:uid>", methods=["POST"])
@login_required
@admin_required
def admin_approve(uid):
    db = get_db()
    u  = get_user_by_id(uid)
    if u:
        db.execute("UPDATE users SET approved=1 WHERE id=?", (uid,))
        db.commit()
        flash(f"✅ {u['username']} approved.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/reject/<int:uid>", methods=["POST"])
@login_required
@admin_required
def admin_reject(uid):
    db = get_db()
    u  = get_user_by_id(uid)
    if u and u["role"] != "admin":
        db.execute("DELETE FROM users WHERE id=?", (uid,))
        db.commit()
        flash(f"❌ {u['username']} rejected and removed.", "warning")
    return redirect(url_for("admin_panel"))


@app.route("/admin/approve_lang/<int:lid>", methods=["POST"])
@login_required
@admin_required
def admin_approve_lang(lid):
    db  = get_db()
    row = db.execute("SELECT * FROM languages WHERE id=?", (lid,)).fetchone()
    if row:
        db.execute("UPDATE languages SET approved=1 WHERE id=?", (lid,))
        db.commit()
        flash(f"✅ Language '{row['name']}' is now live.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/reject_lang/<int:lid>", methods=["POST"])
@login_required
@admin_required
def admin_reject_lang(lid):
    db  = get_db()
    row = db.execute("SELECT * FROM languages WHERE id=?", (lid,)).fetchone()
    if row:
        db.execute("DELETE FROM languages WHERE id=?", (lid,))
        db.commit()
        flash(f"Language '{row['name']}' proposal rejected.", "warning")
    return redirect(url_for("admin_panel"))


# =============================================================================
#  LANGUAGE PROPOSAL ROUTE
# =============================================================================

@app.route("/languages/propose", methods=["GET", "POST"])
@login_required
def propose_language():
    if request.method == "POST":
        name      = request.form.get("name", "").strip().title()
        nllb_code = request.form.get("nllb_code", "").strip() or None
        u = current_user()

        if not name:
            flash("Language name is required.", "danger")
            return redirect(url_for("propose_language"))

        try:
            db = get_db()
            db.execute(
                """INSERT INTO languages (name, nllb_code, added_by, approved, created_at)
                   VALUES (?, ?, ?, 0, ?)""",
                (name, nllb_code, u["id"], datetime.datetime.utcnow().isoformat())
            )
            db.commit()
            flash(
                f"'{name}' submitted for admin review. "
                "It will appear in the language list once approved.",
                "success"
            )
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash(f"'{name}' already exists in the system.", "warning")
            return redirect(url_for("propose_language"))

    return render_template_string(PROPOSE_LANG_HTML)


# =============================================================================
#  MAIN APP ROUTES
# =============================================================================

@app.route("/", methods=["GET"])
@login_required
def dashboard():
    lang = request.args.get("lang", session.get("selected_lang"))
    lang_names = {l["name"] for l in db_get_approved_languages()}
    if not lang or lang not in lang_names:
        lang = next(iter(lang_names), "Tiv")
    session["selected_lang"] = lang
    return render_main(lang=lang)


@app.route("/translate", methods=["POST"])
@login_required
def translate_route():
    english = request.form.get("english_text", "").strip()
    lang    = request.form.get("target_lang", session.get("selected_lang", "Tiv"))
    session["selected_lang"] = lang
    return render_main(result=translate(english, lang), last_query=english, lang=lang)


@app.route("/add", methods=["POST"])
@login_required
def add_route():
    english  = request.form.get("english_text", "").strip()
    local    = request.form.get("local_text",   "").strip()
    lang     = request.form.get("target_lang",  session.get("selected_lang", "Tiv"))
    category = request.form.get("category",     "General").strip()
    u = current_user()

    if not english or not local:
        flash("Both English and translation are required.", "warning")
        return redirect(url_for("dashboard"))

    if db_insert_translation(english, local, lang, category, "manual", u["id"]):
        session["last_category"] = category
        session["selected_lang"] = lang
        flash(f'✅ Saved: "{english}" → "{local}"', "success")
    else:
        flash(f'"{english}" already exists in {lang}.', "info")

    return redirect(url_for("dashboard", lang=lang, focus=1))


@app.route("/save", methods=["POST"])
@login_required
def save_route():
    english  = request.form.get("english_text", "").strip()
    local    = request.form.get("local_text",   "").strip()
    lang     = request.form.get("target_lang",  session.get("selected_lang", "Tiv"))
    category = request.form.get("category",     "General").strip()
    u = current_user()

    if db_insert_translation(english, local, lang, category, "ai", u["id"]):
        flash(f'✅ Saved AI translation: "{english}"', "success")
    else:
        flash(f'"{english}" already exists in {lang}.', "info")

    session["selected_lang"] = lang
    return redirect(url_for("dashboard", lang=lang))


@app.route("/upload_csv", methods=["POST"])
@login_required
def upload_csv_route():
    file         = request.files.get("csv_file")
    default_lang = request.form.get("target_lang", session.get("selected_lang", "Tiv"))
    u = current_user()

    if not file or not file.filename:
        flash("No file selected.", "warning")
        return redirect(url_for("dashboard"))

    approved_langs = db_lang_names()

    try:
        content = file.read().decode("utf-8-sig")
        reader  = csv.DictReader(io.StringIO(content))
        added, dupes, bad = 0, 0, 0
        for row in reader:
            eng  = (row.get("english_text") or "").strip()
            loc  = (row.get("local_text")   or "").strip()
            lang = (row.get("target_lang")  or default_lang).strip()
            cat  = (row.get("category")     or "General").strip()
            if not eng or not loc:
                bad += 1; continue
            if lang not in approved_langs:
                lang = default_lang
            if cat not in CATEGORIES:
                cat = "General"
            if db_insert_translation(eng, loc, lang, cat, "csv", u["id"]):
                added += 1
            else:
                dupes += 1
        msg  = f"Upload done: {added} added, {dupes} duplicates skipped"
        msg += f", {bad} incomplete rows skipped." if bad else "."
        flash(msg, "success" if added else "warning")
    except Exception as exc:
        flash(f"CSV error: {exc}", "danger")

    session["selected_lang"] = default_lang
    return redirect(url_for("dashboard", lang=default_lang))


@app.route("/export_csv")
@login_required
def export_csv_route():
    lang_filter = request.args.get("lang")
    if lang_filter and lang_filter not in db_lang_names():
        lang_filter = None

    rows   = db_get_all_translations(lang_filter)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "english_text", "local_text", "target_lang",
                     "category", "source", "contributor", "created_at"])
    for r in rows:
        writer.writerow([r["id"], r["english_text"], r["local_text"],
                         r["target_lang"], r["category"], r["source"],
                         r["contributor"] or "", r["created_at"]])

    raw  = output.getvalue().encode("utf-8-sig")
    fname = (
        f"techdialect_{lang_filter.lower().replace(' ','_')}.csv"
        if lang_filter else "techdialect_all_languages.csv"
    )
    return Response(raw, mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={fname}",
                             "Content-Length": str(len(raw))})


@app.route("/translate_article", methods=["POST"])
@login_required
def translate_article_route():
    body = request.get_json(silent=True) or {}
    text = body.get("text", "").strip()
    lang = body.get("lang", session.get("selected_lang", "Tiv")).strip()
    return jsonify(translate_article(text, lang))


# =============================================================================
#  REST API  (for Techdialect frontend consumption)
#  SCALABILITY NOTE: Add JWT Bearer token auth when going public.
# =============================================================================

@app.route("/api/translate")
def api_translate():
    text = request.args.get("text", "").strip()
    lang = request.args.get("lang", "Tiv").strip()
    return jsonify(translate(text, lang))


@app.route("/api/languages")
def api_languages():
    return jsonify({
        "languages": [
            {"name": l["name"], "nllb_code": l["nllb_code"],
             "count": db_lang_counts().get(l["name"], 0)}
            for l in db_get_approved_languages()
        ]
    })


@app.route("/api/stats")
def api_stats():
    return jsonify({
        "total_terms":  db_count(),
        "today_count":  get_today_count(),
        "daily_goal":   DAILY_GOAL,
        "streak_days":  get_streak(),
        "total_days":   get_total_days(),
        "ai_active":    bool(HF_TOKEN and REQUESTS_AVAILABLE),
        "languages":    db_lang_counts(),
    })


@app.route("/api/coverage")
def api_coverage():
    lang = request.args.get("lang", "Tiv")
    return jsonify({"lang": lang, "coverage": db_coverage(lang)})


@app.route("/api/translate_article", methods=["POST"])
def api_translate_article():
    body = request.get_json(silent=True) or {}
    text = body.get("text", "").strip()
    lang = body.get("lang", "Tiv").strip()
    return jsonify(translate_article(text, lang))


# =============================================================================
#  ENTRY POINT
# =============================================================================

# This block only runs when you do "python smart_translation_system.py" locally.
# On PythonAnywhere (WSGI), the file is imported and app.run() is never called.
if __name__ == "__main__":
    init_db()
    print("\n" + "=" * 65)
    print("  TECHDIALECT TRANSLATION ENGINE  v5.0")
    print("  Multi-user · Admin approval · User-managed languages")
    print("=" * 65)
    print(f"  DB       : {DB_PATH}")
    print(f"  AI       : {'✅ HuggingFace API active' if HF_TOKEN else '❌ No HF_TOKEN — DB-only mode'}")
    print(f"  Admin    : {DEFAULT_ADMIN_USERNAME} / Techdialect@2024")
    print(f"  URL      : http://127.0.0.1:5000")
    print(f"  Stop     : Ctrl+C")
    print("=" * 65 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5000, use_reloader=False)
else:
    # Running under WSGI (PythonAnywhere) — initialise DB silently
    init_db()
