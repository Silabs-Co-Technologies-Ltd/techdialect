"""Admin-managed specialist reviewers for bilingual STEM content.

A reviewer is an approved user explicitly assigned science or language expertise.
Being an administrator does not confer reviewer permissions automatically.
"""
import datetime

from flask import Blueprint, abort, redirect, render_template_string, request, url_for
from data_studio import _current, _csrf, _require_csrf

reviewers_bp = Blueprint("reviewers", __name__, url_prefix="/studio/reviewers")
SPECIALTIES = frozenset(("science", "language"))

def init_reviewer_roles(db):
    db.execute("""CREATE TABLE IF NOT EXISTS stem_reviewer_roles (
        user_id INTEGER NOT NULL,
        specialty TEXT NOT NULL CHECK (specialty IN ('science','language')),
        granted_by INTEGER NOT NULL,
        granted_at TEXT NOT NULL,
        PRIMARY KEY (user_id, specialty),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (granted_by) REFERENCES users(id)
    )""")
    db.commit()

def has_specialty(db, user, specialty):
    if specialty not in SPECIALTIES or not user or not user["approved"]:
        return False
    init_reviewer_roles(db)
    return db.execute(
        "SELECT 1 FROM stem_reviewer_roles WHERE user_id=? AND specialty=?",
        (user["id"], specialty)
    ).fetchone() is not None

HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>STEM Reviewer Assignments | TechDialect</title>
<style>body{font:16px system-ui;background:#f6fafc;color:#19323c;margin:0}
main{max-width:850px;margin:2rem auto;padding:16px}
section{background:white;border:1px solid #d8e5e9;border-radius:12px;padding:18px;margin:12px 0}
label{display:block;margin:10px 0}select,button{font:inherit;padding:10px;max-width:100%}
button{background:#075d72;color:white;border:0;border-radius:8px}
a:focus-visible,button:focus-visible,select:focus-visible{outline:3px solid orange;outline-offset:2px}
small{color:#4b6870}</style></head><body><main>
<a href="/studio/lessons/">← Lesson editor</a><h1>Assign specialist reviewers</h1>
<p>Only approved accounts can review scientific accuracy or language quality.
A lesson's author cannot review it, and one reviewer cannot perform both reviews.</p>
<section><form method="post" action="{{ url_for('reviewers.update') }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}">
<label for="person">Approved contributor</label>
<select id="person" name="user_id" required>
{% for u in users %}<option value="{{ u.id }}">{{ u.username }}</option>{% endfor %}
</select>
<label for="specialty">Review specialty</label>
<select id="specialty" name="specialty">
<option value="science">Science accuracy</option>
<option value="language">Language quality</option></select>
<label for="decision">Change</label>
<select id="decision" name="decision"><option value="grant">Grant permission</option>
<option value="revoke">Revoke permission</option></select>
<button type="submit">Update permission</button></form></section>
<h2>Current assignments</h2>
{% for role in assignments %}<section>
<strong>{{ role.username }}</strong> · {{ role.specialty|capitalize }} reviewer
<small>Assigned {{ role.granted_at }}</small></section>
{% else %}<p>No specialist reviewers assigned yet.</p>{% endfor %}
</main></body></html>"""

@reviewers_bp.get("/")
def index():
    db, actor = _current()
    if actor["role"] != "admin":
        abort(403)
    init_reviewer_roles(db)
    users = db.execute("SELECT id, username FROM users WHERE approved=1 ORDER BY username").fetchall()
    assignments = db.execute("""SELECT r.*, u.username FROM stem_reviewer_roles r
        JOIN users u ON u.id=r.user_id ORDER BY u.username, r.specialty""").fetchall()
    return render_template_string(HTML, csrf=_csrf(), users=users, assignments=assignments)

@reviewers_bp.post("/update")
def update():
    db, actor = _current()
    if actor["role"] != "admin":
        abort(403)
    _require_csrf()
    init_reviewer_roles(db)
    try:
        user_id = int(request.form.get("user_id", ""))
    except ValueError:
        abort(400)
    specialty = request.form.get("specialty", "")
    decision = request.form.get("decision", "")
    if user_id <= 0 or specialty not in SPECIALTIES or decision not in ("grant", "revoke"):
        abort(400)
    user = db.execute("SELECT id FROM users WHERE id=? AND approved=1", (user_id,)).fetchone()
    if not user:
        abort(404, "Account must be approved before assigning review privileges")
    if decision == "grant":
        db.execute("""INSERT OR IGNORE INTO stem_reviewer_roles
            (user_id,specialty,granted_by,granted_at) VALUES (?,?,?,?)""",
            (user_id,specialty,actor["id"],datetime.datetime.now(datetime.timezone.utc).isoformat()))
    else:
        db.execute("DELETE FROM stem_reviewer_roles WHERE user_id=? AND specialty=?", (user_id,specialty))
    db.commit()
    return redirect(url_for("reviewers.index"))
