"""Curated YouTube STEM tutorials.

Video files live on YouTube; TechDialect stores only metadata and validated IDs.
The embed loads only after an explicit learner action, important for child privacy.
"""
import datetime
import re
from urllib.parse import urlsplit, parse_qs

from flask import Blueprint, abort, flash, redirect, render_template_string, request, url_for, Response

from data_studio import _csrf, _require_csrf
from stem_learning import LESSON_BY_SLUG

videos_bp = Blueprint("videos", __name__, url_prefix="/videos")
video_admin_bp = Blueprint("video_admin", __name__, url_prefix="/admin/videos")

YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}
STATUSES = {"draft", "published", "hidden"}
MAX_PUBLIC = 100


def youtube_id(value):
    """Accept real HTTPS YouTube video URLs, never arbitrary embed URLs or HTML."""
    try:
        parsed = urlsplit((value or "").strip())
        if (parsed.scheme != "https" or parsed.netloc.lower() not in YOUTUBE_HOSTS
                or parsed.username or parsed.password or parsed.port is not None):
            return None
        host = parsed.netloc.lower()
        parts = parsed.path.strip("/").split("/")
        if host.endswith("youtu.be"):
            candidate = parts[0] if len(parts) == 1 else None
        elif parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v", [])
            candidate = values[0] if len(values) == 1 else None
        elif len(parts) == 2 and parts[0] in ("embed", "shorts", "live"):
            candidate = parts[1]
        else:
            candidate = None
        return candidate if candidate and YOUTUBE_ID.fullmatch(candidate) else None
    except (ValueError, TypeError):
        return None


def _services():
    from smart_translation_system import get_db, current_user, db_lang_names
    return get_db, current_user, db_lang_names


def _db():
    get_db, _, _ = _services()
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS video_tutorials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        language TEXT NOT NULL DEFAULT 'English',
        lesson_slug TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'draft'
            CHECK(status IN ('draft','published','hidden')),
        created_by INTEGER NOT NULL,
        updated_by INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        published_at TEXT,
        FOREIGN KEY(created_by) REFERENCES users(id),
        FOREIGN KEY(updated_by) REFERENCES users(id)
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_video_public ON video_tutorials(status,lesson_slug,created_at)")
    db.commit()
    return db


def published_for_lesson(slug, limit=6):
    """Public-only lesson recommendations; never include drafts or hidden videos."""
    return _db().execute("""SELECT id,video_id,title,description,language,lesson_slug
        FROM video_tutorials WHERE status='published' AND lesson_slug=?
        ORDER BY published_at DESC,id DESC LIMIT ?""", (slug, limit)).fetchall()


def _admin():
    _, get_user, _ = _services()
    actor = get_user()
    if not actor or not actor["approved"] or actor["role"] != "admin":
        abort(403)
    return actor


def _languages():
    _, _, names = _services()
    return sorted({"English"} | set(names()))


def _fields():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    link = request.form.get("youtube_url", "").strip()
    language = request.form.get("language", "").strip()
    slug = request.form.get("lesson_slug", "").strip()
    video = youtube_id(link)
    if (not video or not title or not language or len(title) > 140 or
            len(description) > 1600 or language not in _languages() or
            (slug and slug not in LESSON_BY_SLUG)):
        abort(400, description="Invalid tutorial. Use a YouTube video link, approved language and optional lesson.")
    return video, title, description, language, slug


PUBLIC_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>Video Tutorials | TechDialect</title>
<style>
:root{font-family:system-ui,sans-serif;color:#183545;background:#f5f9fb}
*{box-sizing:border-box}body{margin:0}main{max-width:1100px;margin:0 auto;padding:24px}
h1{font-size:clamp(1.7rem,4vw,2.5rem)}a{color:#006182}
nav{display:flex;flex-wrap:wrap;gap:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(300px,100%),1fr));gap:18px}
.card{border:1px solid #d7e5e9;border-radius:16px;background:white;padding:20px;min-width:0}
.card p{line-height:1.6;overflow-wrap:anywhere}
.meta{color:#476775;font-size:.88rem}
.video-placeholder{border:0;border-radius:12px;background:#17394c;color:#fff;
display:flex;align-items:center;justify-content:center;flex-direction:column;
gap:8px;min-height:190px;padding:20px;width:100%;font:inherit;cursor:pointer}
.video-placeholder span{display:block;font-size:2rem}
.video-player iframe{aspect-ratio:16/9;width:100%;border:0;border-radius:12px}
fieldset{border:0;padding:0;display:flex;flex-wrap:wrap;gap:12px}
label{display:flex;flex-direction:column;gap:6px;font-weight:600}
select,button{font:inherit}select{padding:10px;border:1px solid #9fbac5;border-radius:8px}
button.search{padding:10px 16px;align-self:end;background:#006584;color:white;border:0;border-radius:9px}
form{background:#fff;border:1px solid #d7e5e9;border-radius:14px;padding:18px;margin:20px 0}
a:focus-visible,button:focus-visible,select:focus-visible{outline:3px solid #e5a54b;outline-offset:3px}
.note{font-size:.9rem;color:#476775}
</style></head><body><main>
<nav><a href="{{ url_for('stem.index') }}">STEM Lessons</a><a href="{{ url_for('stem.progress_report') }}">My Progress</a>
<a href="{{ url_for('videos.index') }}">Video Tutorials</a></nav>
<h1>STEM Video Tutorials</h1>
<p>Watch TechDialect tutorials hosted on YouTube, alongside the lessons they explain.</p>
<form method="get" aria-label="Filter tutorials">
<fieldset><label for="level">Class
<select name="level" id="level"><option value="">All classes</option>
{% for level in levels %}<option value="{{ level }}" {% if level==selected_level %}selected{% endif %}>{{ level }}</option>{% endfor %}
</select></label>
<label for="language">Language
<select name="language" id="language"><option value="">All languages</option>
{% for language in languages %}<option value="{{ language }}" {% if language==selected_language %}selected{% endif %}>{{ language }}</option>{% endfor %}
</select></label>
<button class="search">Filter tutorials</button></fieldset>
</form>
<p class="meta" role="status">{{ videos|length }} tutorial{{ '' if videos|length==1 else 's' }} shown</p>
<section class="grid" aria-label="Published tutorials">
{% for item in videos %}
<article class="card"><h2>{{ item.title }}</h2>
<p class="meta">{{ item.language }}{% if item.lesson_slug %} ·
{% set lesson = lessons[item.lesson_slug] %}{{ lesson.level }} · {{ lesson.subject }}{% endif %}</p>
{% if item.description %}<p>{{ item.description }}</p>{% endif %}
{% if item.lesson_slug %}<p><a href="{{ url_for('stem.lesson_detail',slug=item.lesson_slug) }}">Open related lesson</a></p>{% endif %}
<div class="video-player" data-video-player>
<button type="button" class="video-placeholder" data-youtube-id="{{ item.video_id }}"
aria-label="Load YouTube video: {{ item.title }}"><span aria-hidden="true">▶</span>
Play tutorial on YouTube</button></div>
<p class="note">YouTube is loaded only when you select Play. It may receive browser information. Internet is required for playback.</p>
<p><a href="https://www.youtube.com/watch?v={{ item.video_id }}" rel="noopener noreferrer"
target="_blank">Open this tutorial on YouTube</a></p></article>
{% else %}
<article class="card"><h2>No matching tutorials yet</h2>
<p>Published videos will appear here after they are added by a TechDialect administrator.</p></article>
{% endfor %}
</section>
<script src="{{ url_for('videos.embed_script') }}" defer></script>
</main></body></html>"""


ADMIN_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Manage STEM Videos | TechDialect</title>
<style>
body{font:16px system-ui,sans-serif;color:#183545;background:#f5f9fb;margin:0}
main{max-width:980px;margin:auto;padding:24px}h1{font-size:clamp(1.5rem,4vw,2.2rem)}
article{background:white;border:1px solid #d7e4e9;border-radius:14px;padding:20px;margin:16px 0}
label{display:block;font-weight:600;margin:14px 0 5px}
input,select,textarea{font:inherit;padding:10px;border:1px solid #abc2cc;border-radius:9px;box-sizing:border-box;width:100%}
button{font:inherit;padding:10px 14px;background:#065c76;color:white;border:0;border-radius:9px;cursor:pointer}
button.secondary{background:#355a6a}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
a{color:#006182}a:focus-visible,input:focus-visible,select:focus-visible,button:focus-visible,textarea:focus-visible{outline:3px solid #e9ac43;outline-offset:3px}
.note{color:#4c6976;font-size:.9rem}
</style></head><body><main>
<p><a href="{{ url_for('videos.index') }}">← Public video library</a></p>
<h1>Manage YouTube Tutorials</h1><p>Paste your YouTube video URL, choose a language and optionally connect it to a STEM lesson.
New videos stay as drafts until explicitly published.</p>
{% with messages=get_flashed_messages() %}{% for message in messages %}
<p role="status">{{ message }}</p>{% endfor %}{% endwith %}
<article><h2>Add a tutorial</h2>
<form method="post" action="{{ url_for('video_admin.create') }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}">
<label for="new-title">Tutorial title</label><input id="new-title" name="title" maxlength="140" required>
<label for="new-url">YouTube video URL</label><input id="new-url" name="youtube_url" type="url"
placeholder="https://www.youtube.com/watch?v=..." required>
<label for="new-description">Description</label><textarea id="new-description" name="description" maxlength="1600" rows="3"></textarea>
<label for="new-language">Language</label><select id="new-language" name="language" required>
{% for lang in languages %}<option value="{{ lang }}">{{ lang }}</option>{% endfor %}</select>
<label for="new-lesson">Related STEM lesson (optional)</label><select id="new-lesson" name="lesson_slug">
<option value="">General tutorial</option>
{% for lesson in lessons.values() %}<option value="{{ lesson.slug }}">{{ lesson.level }} · {{ lesson.title }}</option>{% endfor %}
</select><p><button type="submit">Save tutorial draft</button></p>
</form></article>
<h2>Saved tutorials</h2>
{% for item in videos %}
<article><h3>{{ item.title }}</h3>
<p class="note">Status: <strong>{{ item.status }}</strong> · ID: {{ item.video_id }} · {{ item.language }}</p>
<form method="post" action="{{ url_for('video_admin.edit',tutorial_id=item.id) }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}">
<label for="title-{{ item.id }}">Title</label><input id="title-{{ item.id }}" name="title" maxlength="140"
value="{{ item.title }}" required>
<label for="url-{{ item.id }}">YouTube URL</label><input id="url-{{ item.id }}" type="url" name="youtube_url"
value="https://www.youtube.com/watch?v={{ item.video_id }}" required>
<label for="desc-{{ item.id }}">Description</label><textarea id="desc-{{ item.id }}"
name="description" maxlength="1600" rows="2">{{ item.description }}</textarea>
<label for="lang-{{ item.id }}">Language</label><select id="lang-{{ item.id }}" name="language">
{% for lang in languages %}<option value="{{ lang }}" {% if item.language==lang %}selected{% endif %}>{{ lang }}</option>{% endfor %}
</select>
<label for="lesson-{{ item.id }}">Related lesson</label><select id="lesson-{{ item.id }}" name="lesson_slug">
<option value="">General tutorial</option>
{% for lesson in lessons.values() %}<option value="{{ lesson.slug }}" {% if item.lesson_slug==lesson.slug %}selected{% endif %}>{{ lesson.level }} · {{ lesson.title }}</option>{% endfor %}</select>
<p><button type="submit">Save changes (return to draft)</button></p>
</form>
<div class="row">
{% if item.status!='published' %}
<form method="post" action="{{ url_for('video_admin.visibility',tutorial_id=item.id) }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}">
<input type="hidden" name="status" value="published"><button type="submit">Publish</button>
</form>{% endif %}
{% if item.status=='published' %}
<form method="post" action="{{ url_for('video_admin.visibility',tutorial_id=item.id) }}">
<input type="hidden" name="csrf_token" value="{{ csrf }}">
<input type="hidden" name="status" value="hidden"><button type="submit" class="secondary">Unpublish</button>
</form>{% endif %}
</div></article>
{% else %}<p>No videos saved yet.</p>{% endfor %}
</main></body></html>"""


@videos_bp.get("/")
def index():
    db = _db()
    level = request.args.get("level", "").strip()
    language = request.args.get("language", "").strip()
    levels = sorted({x["level"] for x in LESSON_BY_SLUG.values()})
    if (level and level not in levels) or (language and language not in _languages()):
        abort(400)
    sql = """SELECT id,video_id,title,description,language,lesson_slug
             FROM video_tutorials WHERE status='published'"""
    values = []
    if language:
        sql += " AND language=?"
        values.append(language)
    if level:
        eligible = [x["slug"] for x in LESSON_BY_SLUG.values() if x["level"] == level]
        sql += " AND lesson_slug IN (" + ",".join("?" for _ in eligible) + ")"
        values.extend(eligible)
    sql += " ORDER BY published_at DESC,id DESC LIMIT ?"
    values.append(MAX_PUBLIC)
    rows = db.execute(sql, values).fetchall()
    return render_template_string(PUBLIC_HTML, videos=rows, lessons=LESSON_BY_SLUG,
                                  selected_level=level, selected_language=language,
                                  levels=levels, languages=_languages())


@video_admin_bp.get("/")
def dashboard():
    _admin()
    rows = _db().execute("SELECT * FROM video_tutorials ORDER BY created_at DESC,id DESC LIMIT 200").fetchall()
    return render_template_string(ADMIN_HTML, videos=rows, lessons=LESSON_BY_SLUG,
                                  csrf=_csrf(), languages=_languages())


@video_admin_bp.post("/create")
def create():
    actor = _admin()
    _require_csrf()
    video, title, description, language, slug = _fields()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db = _db()
    if db.execute("SELECT id FROM video_tutorials WHERE video_id=?", (video,)).fetchone():
        abort(409, description="This YouTube video is already in your library")
    db.execute("""INSERT INTO video_tutorials
      (video_id,title,description,language,lesson_slug,status,created_by,updated_by,created_at,updated_at)
      VALUES (?,?,?,?,?,'draft',?,?,?,?)""",
      (video,title,description,language,slug,actor["id"],actor["id"],now,now))
    db.commit()
    flash("Video saved as draft. Publish it when ready.")
    return redirect(url_for("video_admin.dashboard"))


@video_admin_bp.post("/<int:tutorial_id>/edit")
def edit(tutorial_id):
    actor = _admin()
    _require_csrf()
    video, title, description, language, slug = _fields()
    db = _db()
    existing = db.execute("SELECT id FROM video_tutorials WHERE id=?", (tutorial_id,)).fetchone()
    if not existing:
        abort(404)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    duplicate = db.execute("SELECT id FROM video_tutorials WHERE video_id=? AND id!=?",
                           (video,tutorial_id)).fetchone()
    if duplicate:
        abort(409, description="This YouTube video is already assigned to another tutorial")
    updated = db.execute("""UPDATE video_tutorials SET video_id=?,title=?,description=?,language=?,
        lesson_slug=?,status='draft',published_at=NULL,updated_by=?,updated_at=? WHERE id=?""",
        (video,title,description,language,slug,actor["id"],now,tutorial_id))
    db.commit()
    if updated.rowcount != 1:
        abort(404)
    flash("Tutorial updated. It is a draft until published again.")
    return redirect(url_for("video_admin.dashboard"))


@video_admin_bp.post("/<int:tutorial_id>/visibility")
def visibility(tutorial_id):
    actor = _admin()
    _require_csrf()
    status = request.form.get("status")
    if status not in ("published", "hidden"):
        abort(400)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db = _db()
    cursor = db.execute("""UPDATE video_tutorials SET status=?,published_at=?,
        updated_by=?,updated_at=? WHERE id=?""",
        (status, now if status=="published" else None, actor["id"],now,tutorial_id))
    db.commit()
    if cursor.rowcount != 1:
        abort(404)
    flash("Tutorial is now " + status + ".")
    return redirect(url_for("video_admin.dashboard"))


PLAYER_JS = r"""(function () {
  "use strict";
  document.addEventListener("click", function (event) {
    const button = event.target.closest("button[data-youtube-id]");
    if (!button) return;
    const id = button.dataset.youtubeId || "";
    if (!/^[A-Za-z0-9_-]{11}$/.test(id)) return;
    const parent = button.closest("[data-video-player]");
    if (!parent || parent.dataset.loaded === "yes") return;
    const frame = document.createElement("iframe");
    frame.src = "https://www.youtube-nocookie.com/embed/" + id;
    frame.title = button.getAttribute("aria-label") || "YouTube tutorial";
    frame.loading = "lazy";
    frame.referrerPolicy = "strict-origin-when-cross-origin";
    frame.allow = "encrypted-media; picture-in-picture";
    frame.allowFullscreen = true;
    parent.dataset.loaded = "yes";
    parent.replaceChildren(frame);
  });
})();"""


@videos_bp.get("/embed.js")
def embed_script():
    r = Response(PLAYER_JS, mimetype="application/javascript")
    r.headers["Cache-Control"] = "public, max-age=3600"
    return r
