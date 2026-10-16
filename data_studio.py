"""TechDialect Data Studio: reviewed linguistic submissions, no automatic publication."""
import datetime
import hmac
import secrets

from flask import Blueprint, abort, flash, redirect, render_template_string, request, session, url_for

data_bp = Blueprint("data", __name__, url_prefix="/data")

def _services():
    # Delay importing the legacy app until its blueprint registration is complete.
    from smart_translation_system import get_db, current_user, db_lang_names
    return get_db, current_user, db_lang_names

def _init(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS language_submissions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      english_text TEXT NOT NULL,
      local_text TEXT NOT NULL,
      language TEXT NOT NULL,
      dialect TEXT NOT NULL DEFAULT '',
      context TEXT NOT NULL,
      source_note TEXT NOT NULL,
      contributor_id INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected')),
      reviewer_id INTEGER,
      reviewed_at TEXT,
      created_at TEXT NOT NULL,
      FOREIGN KEY (contributor_id) REFERENCES users(id),
      FOREIGN KEY (reviewer_id) REFERENCES users(id)
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_submissions_status ON language_submissions(status)")
    conn.commit()

def _csrf():
    if "data_csrf" not in session:
        session["data_csrf"] = secrets.token_urlsafe(32)
    return session["data_csrf"]

def _require_csrf():
    supplied = request.form.get("csrf_token", "")
    if not hmac.compare_digest(str(supplied), str(session.get("data_csrf", ""))) or not supplied:
        abort(400, description="Invalid form token")

def _current():
    get_db, current_user, _ = _services()
    user = current_user()
    if not user or not user["approved"]:
        abort(403)
    return get_db(), user

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Data Studio | TechDialect</title>
<style>body{font-family:system-ui,sans-serif;background:#f6fafc;color:#1b2e39;margin:0}
main{max-width:840px;margin:24px auto;padding:16px}article{background:white;border:1px solid #d7e6e9;border-radius:14px;padding:22px;margin:12px 0}
input,textarea,select,button{font:inherit;padding:12px;border-radius:8px;border:1px solid #afc4d0;width:100%;box-sizing:border-box}
label{display:block;margin:15px 0 5px;font-weight:600}button{background:#006a7c;color:white;border:0;cursor:pointer;margin-top:12px}
button:focus-visible,a:focus-visible{outline:3px solid #df9a33;outline-offset:3px}
small{color:#4f6873}.pill{font-size:.8rem;background:#edf4f6;border-radius:6px;padding:4px 8px}
.actions{display:flex;gap:10px}.actions form{flex:1}
</style></head><body><main>
<a href="/learn/">← STEM lessons</a><h1>Language Data Studio</h1>
<p>Contribute Nigerian-language translations. All submissions enter a review queue and are not automatically published as verified data.</p>
{% with messages = get_flashed_messages(with_categories=true) %}
{% for category,message in messages %}<article role="status">{{ message }}</article>{% endfor %}{% endwith %}
{% if is_admin %}
<h2>Pending review ({{ rows|length }})</h2>
{% for item in rows %}
<article><span class="pill">{{ item.language }}{% if item.dialect %} · {{ item.dialect }}{% endif %}</span>
<h3>{{ item.english_text }} → {{ item.local_text }}</h3>
<p>{{ item.context }}</p><small>Source: {{ item.source_note }} · Contributor #{{ item.contributor_id }}</small>
<div class="actions">
<form method="post" action="{{ url_for('data.review',submission_id=item.id) }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}"><input type="hidden" name="decision" value="approved">
<button type="submit">Approve</button></form>
<form method="post" action="{{ url_for('data.review',submission_id=item.id) }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}"><input type="hidden" name="decision" value="rejected">
<button type="submit">Reject</button></form></div></article>
{% else %}<article>No pending submissions.</article>{% endfor %}
<h2>Approved, awaiting publication</h2>
{% for item in approved %}
<article><span class="pill">{{ item.language }}</span>
<p><strong>{{ item.english_text }}</strong> → {{ item.local_text }}</p>
<form method="post" action="{{ url_for('publishing.publish_term',submission_id=item.id) }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}">
<button type="submit">Publish reviewed term</button></form></article>
{% else %}<article>No approved terms awaiting publication.</article>{% endfor %}
{% else %}
<article><h2>Submit a translation</h2>
<form method="post" action="{{ url_for('data.submit') }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}">
<label for="english">English STEM term</label><input id="english" name="english_text" maxlength="250" required>
<label for="local">Translation in your language</label><input id="local" name="local_text" maxlength="500" required>
<label for="language">Language</label><select id="language" name="language" required>
{% for lang in languages %}<option value="{{ lang }}">{{ lang }}</option>{% endfor %}</select>
<label for="dialect">Dialect / regional variety (optional)</label><input id="dialect" name="dialect" maxlength="100">
<label for="context">How is this term used?</label><textarea id="context" name="context" maxlength="1000" required></textarea>
<label for="source">Source or community attribution</label><input id="source" name="source_note" maxlength="300" required>
<p><small>Submit only material you have the right to share. Do not include private information about other people.</small></p>
<button type="submit">Submit for review</button>
</form></article>{% endif %}
</main></body></html>"""

@data_bp.get("/")
def index():
    db, user = _current()
    from publishing import _schema
    _schema(db)
    _, _, lang_names = _services()
    is_admin = user["role"] == "admin"
    rows = db.execute(
        "SELECT * FROM language_submissions WHERE status='pending' ORDER BY created_at ASC LIMIT 100"
    ).fetchall() if is_admin else []
    approved = db.execute(
        """SELECT s.* FROM language_submissions s
           LEFT JOIN published_terms p ON p.submission_id=s.id
           WHERE s.status='approved' AND p.submission_id IS NULL
           ORDER BY s.reviewed_at ASC LIMIT 100"""
    ).fetchall() if is_admin else []
    return render_template_string(PAGE, csrf=_csrf(), languages=sorted(lang_names()),
                                  rows=rows, approved=approved, is_admin=is_admin)

@data_bp.post("/submit")
def submit():
    db, user = _current()
    _require_csrf()
    _init(db)
    _, _, lang_names = _services()
    english = request.form.get("english_text", "").strip()
    local = request.form.get("local_text", "").strip()
    lang = request.form.get("language", "").strip()
    dialect = request.form.get("dialect", "").strip()
    context = request.form.get("context", "").strip()
    source = request.form.get("source_note", "").strip()
    if not all((english, local, context, source)) or lang not in lang_names() or any([
        len(english)>250,len(local)>500,len(dialect)>100,len(context)>1000,len(source)>300
    ]):
        abort(400, "Invalid submission")
    db.execute("""INSERT INTO language_submissions
        (english_text,local_text,language,dialect,context,source_note,contributor_id,created_at)
        VALUES (?,?,?,?,?,?,?,?)""",
        (english,local,lang,dialect,context,source,user["id"],datetime.datetime.now(datetime.timezone.utc).isoformat()))
    db.commit()
    flash("Submitted for language review. It is not published yet.", "success")
    return redirect(url_for("data.index"))

@data_bp.post("/review/<int:submission_id>")
def review(submission_id):
    db, user = _current()
    if user["role"] != "admin":
        abort(403)
    _require_csrf()
    _init(db)
    decision = request.form.get("decision")
    if decision not in ("approved", "rejected"):
        abort(400)
    cursor = db.execute("""UPDATE language_submissions
        SET status=?, reviewer_id=?, reviewed_at=?
        WHERE id=? AND status='pending'""",
        (decision, user["id"], datetime.datetime.now(datetime.timezone.utc).isoformat(),submission_id))
    db.commit()
    if cursor.rowcount != 1:
        abort(404)
    flash("Review decision saved. Approved submissions require explicit publishing later.", "success")
    return redirect(url_for("data.index"))
