"""Editorial bilingual STEM lesson editions with two independent human reviews."""
import datetime
import hmac
from flask import Blueprint, abort, jsonify, request, redirect, url_for, render_template_string, session
from data_studio import _current, _require_csrf, _csrf
from stem_learning import LESSON_BY_SLUG
from reviewer_roles import has_specialty, init_reviewer_roles

lesson_editor_bp = Blueprint("lesson_editor", __name__, url_prefix="/studio/lessons")

def _init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS stem_editions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_slug TEXT NOT NULL,
        language TEXT NOT NULL,
        dialect TEXT NOT NULL DEFAULT '',
        explanation TEXT NOT NULL,
        example_text TEXT NOT NULL,
        question TEXT NOT NULL,
        options_json TEXT NOT NULL,
        created_by INTEGER NOT NULL,
        science_reviewed_by INTEGER,
        language_reviewed_by INTEGER,
        published_by INTEGER,
        published_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (created_by) REFERENCES users(id),
        UNIQUE(lesson_slug, language, dialect)
    )""")
    db.commit()

def published_edition(db, slug, language):
    _init(db)
    return db.execute("""SELECT * FROM stem_editions
        WHERE lesson_slug=? AND language=? AND published_at IS NOT NULL
        AND science_reviewed_by IS NOT NULL AND language_reviewed_by IS NOT NULL
        ORDER BY CASE WHEN dialect='' THEN 0 ELSE 1 END, id DESC LIMIT 1""",
        (slug, language)).fetchone()

EDITOR = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>STEM Editorial Studio</title><style>body{font:16px system-ui;background:#f5f9fb;color:#123;margin:0}
main{max-width:850px;margin:2rem auto;padding:1rem}section{background:white;border:1px solid #cbdbe4;padding:1.5rem;margin:1rem 0;border-radius:14px}
label{display:block;margin:.8rem 0 .2rem;font-weight:600}input,textarea,select{box-sizing:border-box;width:100%;padding:.7rem;font:inherit}
button{padding:.7rem 1rem;background:#005b7b;color:white;border:0;border-radius:8px;margin:.4rem}button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid orange}
small{color:#456}</style><main><a href="/learn/">← Learning</a><h1>STEM Editorial Studio</h1>
<p>Language and science reviews must be completed by different assigned specialists before publication.</p>
{% if is_admin %}<p><a href="{{ url_for('reviewers.index') }}">Manage reviewers</a></p>{% endif %}
{% if is_admin %}<section><h2>Create or replace an unpublished lesson edition</h2>
<form method="post" action="{{ url_for('lesson_editor.save') }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}">
<label for="slug">STEM lesson</label><select id="slug" name="lesson_slug">{% for x in lessons %}<option value="{{ x.slug }}">{{ x.title }}</option>{% endfor %}</select>
<label for="lang">Language</label><input id="lang" name="language" maxlength="100" required>
<label for="dialect">Dialect (optional)</label><input id="dialect" name="dialect" maxlength="100">
<label for="explain">Reviewed explanation</label><textarea id="explain" name="explanation" maxlength="3000" required></textarea>
<label for="example">Local example</label><textarea id="example" name="example_text" maxlength="1000" required></textarea>
<label for="question">Quiz question</label><textarea id="question" name="question" maxlength="500" required></textarea>
<label for="options">Three answer choices, one per line (first one must be correct)</label><textarea id="options" name="options" maxlength="1000" required></textarea>
<button>Save draft for review</button></form></section>{% endif %}
{% for x in editions %}<section><h2>{{ x.lesson_slug }} · {{ x.language }}</h2>
<p>{{ x.explanation }}</p>
<small>Science: {{ 'reviewed' if x.science_reviewed_by else 'pending' }} · Language: {{ 'reviewed' if x.language_reviewed_by else 'pending' }} · {{ 'published' if x.published_at else 'unpublished' }}</small>
{% if not x.published_at %}
{% if can_science and x.created_by != actor_id and x.language_reviewed_by != actor_id and not x.science_reviewed_by %}
<form method="post" action="{{ url_for('lesson_editor.action', edition_id=x.id,kind='science') }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}"><button type="submit">Approve science</button></form>{% endif %}
{% if can_language and x.created_by != actor_id and x.science_reviewed_by != actor_id and not x.language_reviewed_by %}
<form method="post" action="{{ url_for('lesson_editor.action', edition_id=x.id,kind='language') }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}"><button type="submit">Approve language</button></form>{% endif %}
{% if is_admin and x.science_reviewed_by and x.language_reviewed_by %}
<form method="post" action="{{ url_for('lesson_editor.action', edition_id=x.id,kind='publish') }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}"><button type="submit">Publish</button></form>{% endif %}
{% endif %}</section>{% endfor %}
</main></html>"""

@lesson_editor_bp.get("/")
def index():
    db, user = _current()
    _init(db)
    is_admin = user["role"] == "admin"
    can_science = has_specialty(db, user, "science")
    can_language = has_specialty(db, user, "language")
    if not (is_admin or can_science or can_language):
        abort(403)
    rows=db.execute("SELECT * FROM stem_editions ORDER BY created_at DESC LIMIT 100").fetchall()
    return render_template_string(EDITOR, csrf=_csrf(), lessons=LESSON_BY_SLUG.values(),
                                  editions=rows, is_admin=is_admin, actor_id=user["id"],
                                  can_science=can_science, can_language=can_language)

@lesson_editor_bp.post("/save")
def save():
    import json
    db, user = _current()
    if user["role"] != "admin":
        abort(403)
    _require_csrf()
    _init(db)
    slug=request.form.get("lesson_slug","")
    language=request.form.get("language","").strip()
    dialect=request.form.get("dialect","").strip()
    explanation=request.form.get("explanation","").strip()
    example=request.form.get("example_text","").strip()
    question=request.form.get("question","").strip()
    choices=[s.strip() for s in request.form.get("options","").splitlines() if s.strip()]
    if slug not in LESSON_BY_SLUG or not language or not explanation or not example or not question or len(choices)!=3 or any([len(language)>100,len(dialect)>100,len(explanation)>3000,len(example)>1000,len(question)>500,any(len(x)>250 for x in choices)]):
        abort(400)
    # Published editions must not be silently overwritten. Drafts reset all reviews on changes.
    existing=db.execute("SELECT id,published_at FROM stem_editions WHERE lesson_slug=? AND language=? AND dialect=?",(slug,language,dialect)).fetchone()
    if existing and existing["published_at"]:
        abort(409,description="Published editions are immutable; create a new version in a future revision.")
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if existing:
        db.execute("""UPDATE stem_editions SET explanation=?,example_text=?,question=?,options_json=?,created_by=?,created_at=?,science_reviewed_by=NULL,language_reviewed_by=NULL
            WHERE id=?""",(explanation,example,question,json.dumps(choices),user["id"],now,existing["id"]))
    else:
        db.execute("""INSERT INTO stem_editions(lesson_slug,language,dialect,explanation,example_text,question,options_json,created_by,created_at)
        VALUES(?,?,?,?,?,?,?,?,?)""",(slug,language,dialect,explanation,example,question,json.dumps(choices),user["id"],now))
    db.commit()
    return redirect(url_for("lesson_editor.index"))

@lesson_editor_bp.post("/<int:edition_id>/<kind>")
def action(edition_id,kind):
    db,user=_current()
    _require_csrf()
    _init(db)
    row=db.execute("SELECT * FROM stem_editions WHERE id=?",(edition_id,)).fetchone()
    if not row or row["published_at"]:
        abort(404)
    if kind in ("science","language"):
        if not has_specialty(db, user, kind):
            abort(403, description="Specialist reviewer assignment required.")
        other="language_reviewed_by" if kind=="science" else "science_reviewed_by"
        if row["created_by"]==user["id"] or row[other]==user["id"]:
            abort(403,description="Author and reviewers must be different people.")
        col="science_reviewed_by" if kind=="science" else "language_reviewed_by"
        if row[col]:
            abort(409, description="This lesson has already been reviewed for that specialty.")
        db.execute(f"UPDATE stem_editions SET {col}=? WHERE id=?",(user["id"],edition_id))
    elif kind=="publish":
        if user["role"] != "admin":
            abort(403)
        if not row["science_reviewed_by"] or not row["language_reviewed_by"]:
            abort(409,description="Two independent reviews are required.")
        db.execute("UPDATE stem_editions SET published_by=?,published_at=? WHERE id=?",
                   (user["id"],datetime.datetime.now(datetime.timezone.utc).isoformat(),edition_id))
    else:
        abort(404)
    db.commit()
    return redirect(url_for("lesson_editor.index"))
