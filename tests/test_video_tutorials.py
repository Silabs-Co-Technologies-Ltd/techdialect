"""Public YouTube browsing, privacy, URL safety and administrator actions."""
import sqlite3
import pytest
from flask import Flask

import stem_learning
import video_tutorials

VIDEO_ID = "AbCdEf01234"
VALID_VIDEO = "https://www.youtube.com/watch?v=" + VIDEO_ID


@pytest.mark.parametrize("link", [
    VALID_VIDEO,
    "https://youtu.be/" + VIDEO_ID,
    "https://www.youtube.com/shorts/" + VIDEO_ID,
    "https://youtube.com/live/" + VIDEO_ID,
    "https://m.youtube.com/embed/" + VIDEO_ID,
])
def test_accepted_youtube_formats(link):
    assert video_tutorials.youtube_id(link) == VIDEO_ID


@pytest.mark.parametrize("link", [
    "<iframe src='https://www.youtube.com/embed/AbCdEf01234'></iframe>",
    "http://www.youtube.com/watch?v=AbCdEf01234",
    "https://www.youtube.com.evil.example/watch?v=AbCdEf01234",
    "https://youtube.com@malicious.example/watch?v=AbCdEf01234",
    "https://www.youtube.com:444/watch?v=AbCdEf01234",
    "https://www.youtube.com/watch?v=AbCdEf01234&v=12345678901",
    "https://youtube.com/watch?v=bad",
    "https://youtu.be/AbCdEf01234/extra",
    "javascript:alert(1)",
    "https://www.youtube.com/playlist?list=AbCdEf01234",
])
def test_invalid_youtube_urls_rejected(link):
    assert video_tutorials.youtube_id(link) is None


@pytest.fixture
def app_client(monkeypatch):
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE users(
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        approved INTEGER NOT NULL)""")
    db.execute("INSERT INTO users VALUES (1,'admin','admin',1)")
    db.commit()
    actor = {"id":1,"approved":1,"role":"admin"}
    monkeypatch.setattr(video_tutorials, "_services",
                        lambda: (lambda: db, lambda: actor, lambda: {"Tiv", "Yoruba"}))
    monkeypatch.setattr(stem_learning, "available_languages", lambda: ["Tiv"])
    monkeypatch.setattr(stem_learning, "reviewed_term", lambda concept, language: None)
    monkeypatch.setattr(stem_learning, "published_lesson_edition", lambda slug, language: None)
    monkeypatch.setattr(stem_learning, "lesson_tutorials", video_tutorials.published_for_lesson)
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="video-test-secret")
    app.register_blueprint(stem_learning.stem_bp)
    app.register_blueprint(video_tutorials.videos_bp)
    app.register_blueprint(video_tutorials.video_admin_bp)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["data_csrf"] = "video-test-token"
        yield client, db, actor
    db.close()


def _form(**kwargs):
    fields = {
        "csrf_token": "video-test-token",
        "title": "Learning about photosynthesis",
        "youtube_url": VALID_VIDEO,
        "description": "An introduction for children.",
        "language": "English",
        "lesson_slug": "plant-food",
    }
    fields.update(kwargs)
    return fields


def test_only_admin_can_manage_and_all_changes_need_csrf(app_client):
    client, db, actor = app_client
    actor["role"] = "user"
    assert client.get("/admin/videos/").status_code == 403
    assert client.post("/admin/videos/create", data=_form()).status_code == 403
    actor["role"] = "admin"
    assert client.post("/admin/videos/create", data=_form(csrf_token="wrong")).status_code == 400
    assert client.post("/admin/videos/create", data=_form()).status_code == 302
    video = db.execute("SELECT * FROM video_tutorials").fetchone()
    assert video["status"] == "draft"
    assert client.post("/admin/videos/1/visibility", data={"status":"published"}).status_code == 400
    assert client.post("/admin/videos/1/visibility", data={"status":"unapproved", "csrf_token":"video-test-token"}).status_code == 400


def test_published_only_and_lesson_video_display(app_client):
    client, db, actor = app_client
    assert client.get("/videos/").status_code == 200
    assert client.post("/admin/videos/create", data=_form()).status_code == 302
    listing = client.get("/videos/").data
    assert b"Learning about photosynthesis" not in listing
    assert b"Learning about photosynthesis" in client.get("/admin/videos/").data
    assert client.get("/learn/plant-food").data.count(b"Learning about photosynthesis") == 0
    assert client.post("/admin/videos/1/visibility",
                       data={"csrf_token":"video-test-token","status":"published"}).status_code == 302
    listing = client.get("/videos/").data
    assert b"Learning about photosynthesis" in listing
    assert b'data-youtube-id="' + VIDEO_ID.encode() + b'"' in listing
    assert b"<iframe" not in listing
    assert b"www.youtube-nocookie.com/embed" not in listing
    assert b"Play tutorial on YouTube" in listing
    assert b"Learning about photosynthesis" in client.get("/learn/plant-food").data
    assert b"Learning about photosynthesis" not in client.get("/learn/fractions").data
    assert b"Learning about photosynthesis" not in client.get("/videos/?level=Primary+5").data
    assert b"Learning about photosynthesis" in client.get("/videos/?level=Primary+4").data
    assert b"Learning about photosynthesis" not in client.get("/videos/?language=Tiv").data
    assert b"Learning about photosynthesis" in client.get("/videos/?language=English").data
    assert client.get("/videos/?level=Unlisted").status_code == 400
    player = client.get("/videos/embed.js")
    assert player.status_code == 200
    assert b"youtube-nocookie.com/embed/" in player.data
    assert b'iframe' in player.data
    assert client.post("/admin/videos/1/visibility",
                       data={"csrf_token":"video-test-token","status":"hidden"}).status_code == 302
    assert b"Learning about photosynthesis" not in client.get("/videos/").data


def test_edit_resets_publication_and_rejects_duplicate_or_bad_urls(app_client):
    client, db, actor = app_client
    assert client.post("/admin/videos/create",data=_form()).status_code == 302
    assert client.post("/admin/videos/create",data=_form()).status_code == 409
    assert client.post("/admin/videos/create",
                       data=_form(youtube_url="https://example.net/vid")).status_code == 400
    assert client.post("/admin/videos/create",
                       data=_form(lesson_slug="unknown")).status_code == 400
    assert client.post("/admin/videos/1/visibility",
                       data={"csrf_token":"video-test-token","status":"published"}).status_code == 302
    assert client.post("/admin/videos/1/edit",
                       data=_form(title="Updated tutorial", language="Tiv")).status_code == 302
    assert db.execute("SELECT status FROM video_tutorials WHERE id=1").fetchone()[0] == "draft"
    assert b"Updated tutorial" not in client.get("/videos/").data
    assert client.post("/admin/videos/99/visibility",
                       data={"csrf_token":"video-test-token","status":"published"}).status_code == 404
    assert client.post("/admin/videos/99/edit", data=_form()).status_code == 404


def test_unsafe_title_is_escaped(app_client):
    client, db, actor = app_client
    payload = _form(title="<script>alert(1)</script>")
    assert client.post("/admin/videos/create",data=payload).status_code == 302
    assert client.post("/admin/videos/1/visibility",
                       data={"csrf_token":"video-test-token","status":"published"}).status_code == 302
    page = client.get("/videos/").data
    assert b"&lt;script&gt;" in page
    assert b"<script>alert(1)</script>" not in page
