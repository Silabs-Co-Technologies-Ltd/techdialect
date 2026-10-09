"""Smoke tests for standalone STEM module, no database or AI credentials needed."""
from flask import Flask
import stem_learning
from stem_learning import stem_bp, LESSONS

def test_unique_lessons():
    assert len(LESSONS) >= 5
    assert len({x["slug"] for x in LESSONS}) == len(LESSONS)
    assert all(len(x["options"]) >= 2 and 0 <= x["answer"] < len(x["options"]) for x in LESSONS)

def test_routes(monkeypatch):
    monkeypatch.setattr(stem_learning, 'available_languages', lambda: ['Tiv'])
    monkeypatch.setattr(stem_learning, 'reviewed_term', lambda concept, lang: None)
    monkeypatch.setattr(stem_learning, 'published_lesson_edition', lambda slug, lang: None)
    app = Flask(__name__)
    app.register_blueprint(stem_bp)
    client = app.test_client()
    assert client.get("/learn/").status_code == 200
    assert b"TechDialect STEM" in client.get("/learn/").data
    assert client.get("/learn/plant-food").status_code == 200
    assert b"Photosynthesis" in client.get("/learn/plant-food").data
    assert client.get("/learn/unknown").status_code == 404

def test_language_selection_and_invalid_language(monkeypatch):
    monkeypatch.setattr(stem_learning, 'available_languages', lambda: ['Tiv'])
    monkeypatch.setattr(stem_learning, 'reviewed_term', lambda concept, lang: {'local_text':'Reviewed example','dialect':''} if lang=='Tiv' else None)
    monkeypatch.setattr(stem_learning, 'published_lesson_edition', lambda slug, lang: None)
    app = Flask(__name__)
    app.register_blueprint(stem_learning.stem_bp)
    client = app.test_client()
    assert b'Reviewed example' in client.get('/learn/plant-food?language=Tiv').data
    assert client.get('/learn/plant-food?language=NotSupported').status_code == 400

def test_offline_worker_is_limited_to_public_stem():
    app = Flask(__name__)
    app.register_blueprint(stem_learning.stem_bp)
    client = app.test_client()
    response=client.get("/learn/sw.js")
    assert response.status_code == 200
    assert response.mimetype == "application/javascript"
    assert response.headers["Service-Worker-Allowed"] == "/learn/"
    script=response.data
    assert b"techdialect-stem-v1" in script
    assert b"/learn/plant-food" in script
    assert b"req.method" in script
    assert b"url.pathname.startsWith" in script

def test_published_local_lesson_has_independent_quiz(monkeypatch):
    monkeypatch.setattr(stem_learning, "available_languages", lambda: ["Tiv"])
    monkeypatch.setattr(stem_learning, "reviewed_term", lambda concept, lang: None)
    fake = {
        "explanation":"Reviewed lesson content",
        "example_text":"Community illustration",
        "question":"Localized practice question",
        "options_json":'["Correct choice", "Other choice", "Another choice"]'
    }
    monkeypatch.setattr(stem_learning, "published_lesson_edition", lambda slug, lang: fake)
    app=Flask(__name__)
    app.register_blueprint(stem_learning.stem_bp)
    page=app.test_client().get("/learn/plant-food?language=Tiv")
    assert page.status_code==200
    assert b"Localized practice question" in page.data
    assert b"Local-language practice" in page.data
    assert page.data.count(b'data-quiz') >= 2
    assert b"Correct choice" in page.data


def test_device_only_learning_progress_markup(monkeypatch):
    monkeypatch.setattr(stem_learning, 'available_languages', lambda: ['Tiv'])
    monkeypatch.setattr(stem_learning, 'reviewed_term', lambda concept, lang: None)
    monkeypatch.setattr(stem_learning, 'published_lesson_edition', lambda slug, lang: None)
    app=Flask(__name__)
    app.register_blueprint(stem_learning.stem_bp)
    client=app.test_client()
    listing=client.get('/learn/').data
    page=client.get('/learn/plant-food').data
    assert b'learning-progress' in listing
    assert b'clear-progress' in listing
    assert b'data-lesson="plant-food"' in listing
    assert b'data-lesson-detail="plant-food"' in page
    assert b"localStorage.setItem" in page
    assert b"data-language=\"English\"" in page

def test_pathway_catalog_and_routes():
    from curriculum_catalog import PATHWAYS, validate_pathways
    assert validate_pathways(stem_learning.LESSON_BY_SLUG)
    assert len(PATHWAYS) == 3
    assert sum(len(p["lesson_slugs"]) for p in PATHWAYS) == len(LESSONS)
    app = Flask(__name__)
    app.register_blueprint(stem_learning.stem_bp)
    client = app.test_client()
    home = client.get('/learn/')
    assert home.status_code == 200
    assert b'Primary 4 STEM Foundations' in home.data
    for path in PATHWAYS:
        response = client.get('/learn/path/' + path["slug"])
        assert response.status_code == 200
        for lesson_slug in path["lesson_slugs"]:
            assert ('/learn/' + lesson_slug).encode() in response.data
    assert client.get('/learn/path/unknown').status_code == 404
