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
    app = Flask(__name__)
    app.register_blueprint(stem_learning.stem_bp)
    client = app.test_client()
    assert b'Reviewed example' in client.get('/learn/plant-food?language=Tiv').data
    assert client.get('/learn/plant-food?language=NotSupported').status_code == 400
