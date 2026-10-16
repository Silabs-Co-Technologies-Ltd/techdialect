"""Explicit publication of language data after human review.

Approval and publication are deliberately distinct. Public responses expose no
contributor account identifiers or private source notes.
"""
import datetime
from flask import Blueprint, abort, jsonify, request, redirect, url_for
from data_studio import _current, _init, _require_csrf

publish_bp = Blueprint("publishing", __name__, url_prefix="/data")

def _schema(db):
    _init(db)
    db.execute("""CREATE TABLE IF NOT EXISTS published_terms (
        submission_id INTEGER PRIMARY KEY,
        publisher_id INTEGER NOT NULL,
        published_at TEXT NOT NULL,
        FOREIGN KEY (submission_id) REFERENCES language_submissions(id),
        FOREIGN KEY (publisher_id) REFERENCES users(id)
    )""")
    db.commit()

@publish_bp.post("/publish/<int:submission_id>")
def publish_term(submission_id):
    db, user = _current()
    if user["role"] != "admin":
        abort(403)
    _require_csrf()
    _schema(db)
    term = db.execute(
        "SELECT status FROM language_submissions WHERE id=?", (submission_id,)
    ).fetchone()
    if not term or term["status"] != "approved":
        abort(409, description="Term must be approved before publication")
    db.execute(
        "INSERT OR IGNORE INTO published_terms (submission_id,publisher_id,published_at) VALUES (?,?,?)",
        (submission_id, user["id"], datetime.datetime.now(datetime.timezone.utc).isoformat())
    )
    db.commit()
    return redirect(url_for("data.index"))

@publish_bp.get("/terms")
def public_terms():
    # Public endpoint provides only approved AND explicitly published records.
    from smart_translation_system import get_db
    db = get_db()
    _schema(db)
    language = request.args.get("language", "").strip()
    sql = """SELECT s.id, s.english_text, s.local_text, s.language, s.dialect, s.context
             FROM published_terms p JOIN language_submissions s ON s.id=p.submission_id
             WHERE s.status='approved'"""
    params = []
    if language:
        if len(language) > 100:
            abort(400)
        sql += " AND s.language=?"
        params.append(language)
    sql += " ORDER BY p.published_at DESC LIMIT 100"
    rows = db.execute(sql, params).fetchall()
    return jsonify({"terms":[dict(r) for r in rows], "count":len(rows)})
