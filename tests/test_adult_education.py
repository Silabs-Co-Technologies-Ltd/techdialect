"""Adult technology education, language review and legacy schema migration tests."""
import json
import sqlite3

import pytest
from flask import Flask

import lesson_editor
import reviewer_roles
import stem_learning
from adult_catalog import ADULT_LESSONS
from curriculum_catalog import PATHWAYS, validate_pathways


@pytest.fixture
def adult_client(monkeypatch):
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE users(
        id INTEGER PRIMARY KEY, username TEXT, approved INTEGER, role TEXT)""")
    db.executemany("INSERT INTO users VALUES(?,?,?,?)", [
        (1, "author", 1, "admin"),
        (2, "technical reviewer", 1, "user"),
        (3, "language reviewer", 1, "user"),
    ])
    # Simulates the earlier persisted edition table without the two new fields.
    db.execute("""CREATE TABLE stem_editions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_slug TEXT NOT NULL,language TEXT NOT NULL,
        dialect TEXT NOT NULL DEFAULT '',explanation TEXT NOT NULL,
        example_text TEXT NOT NULL,question TEXT NOT NULL,
        options_json TEXT NOT NULL,created_by INTEGER NOT NULL,
        science_reviewed_by INTEGER,language_reviewed_by INTEGER,
        published_by INTEGER,published_at TEXT,created_at TEXT NOT NULL,
        UNIQUE(lesson_slug,language,dialect))""")
    db.commit()
    actor = {"id": 1, "role": "admin", "approved": 1}
    monkeypatch.setattr(lesson_editor, "_current", lambda: (db, actor))
    monkeypatch.setattr(lesson_editor, "available_editor_languages", lambda: ["Tiv"])
    monkeypatch.setattr(stem_learning, "available_languages", lambda: ["Tiv"])
    monkeypatch.setattr(stem_learning, "reviewed_term", lambda concept, language: None)
    monkeypatch.setattr(stem_learning, "lesson_tutorials", lambda slug: [])
    monkeypatch.setattr(
        stem_learning, "published_lesson_edition",
        lambda slug, language: lesson_editor.published_edition(db, slug, language),
    )
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="adult-education-test-secret")
    app.register_blueprint(stem_learning.stem_bp)
    app.register_blueprint(lesson_editor.lesson_editor_bp)
    app.register_blueprint(reviewer_roles.reviewers_bp)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["data_csrf"] = "test-adults"
        yield client, db, actor
    db.close()


def _edition(**overrides):
    values = {
        "csrf_token": "test-adults",
        "lesson_slug": "smartphone-basics",
        "language": "Tiv",
        "dialect": "",
        "explanation": "Locally reviewed explanation",
        "example_text": "Community example",
        "question": "Reviewed local quiz?",
        "options": "Right\nWrong 1\nWrong 2",
        "steps_text": "Reviewed first step\nReviewed second step",
        "task_text": "Reviewed practical activity",
    }
    values.update(overrides)
    return values


def test_adult_catalog_and_learning_routes(adult_client):
    client, db, actor = adult_client
    assert len(ADULT_LESSONS) == 12
    assert len(stem_learning.LESSONS) == 32
    assert validate_pathways(stem_learning.LESSON_BY_SLUG)
    assert len([p for p in PATHWAYS if p["level"] == "Adult Education"]) == 3
    assert all(item["steps"] and item["task"] for item in ADULT_LESSONS)
    home = client.get("/learn/adults")
    assert home.status_code == 200
    assert b"Technology skills for everyday life" in home.data
    assert b"Smartphones and Digital Confidence" in home.data
    assert b"Adult Video Tutorials" in home.data
    assert client.get("/learn/adults?language=Invalid").status_code == 400
    tiv = client.get("/learn/adults?language=Tiv")
    assert tiv.status_code == 200
    assert b"language=Tiv" in tiv.data
    path = client.get("/learn/path/adult-digital-basics?language=Tiv")
    assert path.status_code == 200
    assert b"smartphone-basics?language=Tiv" in path.data
    lesson = client.get("/learn/smartphone-basics?language=Tiv")
    assert lesson.status_code == 200
    assert b"Practice step by step" in lesson.data
    assert b"Locally reviewed explanation" not in lesson.data
    assert b"fully reviewed Tiv version is not yet available" in lesson.data
    sw = client.get("/learn/sw.js").data
    assert b"/learn/adults" in sw and b"/learn/smartphone-basics" in sw


def test_localized_practical_work_requires_complete_draft_and_two_reviewers(adult_client):
    client, db, actor = adult_client
    assert client.post("/studio/lessons/save", data=_edition(
        steps_text="", task_text="")).status_code == 400
    assert client.post("/studio/lessons/save", data=_edition()).status_code == 302
    columns = {row["name"] for row in db.execute("PRAGMA table_info(stem_editions)")}
    assert {"steps_json","task_text"} <= columns
    row = db.execute("SELECT * FROM stem_editions").fetchone()
    assert row["published_at"] is None
    assert json.loads(row["steps_json"]) == [
        "Reviewed first step", "Reviewed second step"]
    assert client.get("/studio/lessons/").status_code == 200
    assert b"Reviewed practical activity" in client.get("/studio/lessons/").data
    assert b"Locally reviewed explanation" not in client.get(
        "/learn/smartphone-basics?language=Tiv").data
    reviewer_roles.init_reviewer_roles(db)
    db.execute("""INSERT INTO stem_reviewer_roles
        (user_id,specialty,granted_by,granted_at) VALUES
        (2,'science',1,'2026-10-16'),(3,'language',1,'2026-10-16')""")
    db.commit()
    token = {"csrf_token":"test-adults"}
    assert client.post("/studio/lessons/1/publish", data=token).status_code == 409
    actor.update(id=2, role="user")
    assert client.post("/studio/lessons/1/science", data=token).status_code == 302
    assert client.post("/studio/lessons/1/language", data=token).status_code == 403
    actor.update(id=3, role="user")
    assert client.post("/studio/lessons/1/language", data=token).status_code == 302
    actor.update(id=1, role="admin")
    assert client.post("/studio/lessons/1/publish", data=token).status_code == 302
    published=client.get("/learn/smartphone-basics?language=Tiv")
    assert published.status_code == 200
    assert b"Locally reviewed explanation" in published.data
    assert b"Reviewed first step" in published.data
    assert b"Reviewed second step" in published.data
    assert b"Reviewed practical activity" in published.data
    assert client.post("/studio/lessons/save", data=_edition(
        explanation="Overwrite published lesson")).status_code == 409


def test_adult_lesson_untranslated_does_not_invent_translation(adult_client):
    client, db, actor = adult_client
    response=client.get("/learn/ai-assistants?language=Tiv")
    assert response.status_code == 200
    assert b"A fully reviewed" not in response.data  # See explicit lower-case fallback.
    assert b"fully reviewed Tiv version is not yet available" in response.data
    assert b"never paste passwords" in response.data.lower()
    assert b"Human-reviewed Tiv lesson edition" not in response.data
