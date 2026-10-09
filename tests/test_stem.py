"""Smoke tests for standalone STEM module, no database or AI credentials needed."""
from flask import Flask
from stem_learning import stem_bp, LESSONS

def test_unique_lessons():
    assert len(LESSONS) >= 5
    assert len({x["slug"] for x in LESSONS}) == len(LESSONS)
    assert all(len(x["options"]) >= 2 and 0 <= x["answer"] < len(x["options"]) for x in LESSONS)

def test_routes():
    app = Flask(__name__)
    app.register_blueprint(stem_bp)
    client = app.test_client()
    assert client.get("/learn/").status_code == 200
    assert b"TechDialect STEM" in client.get("/learn/").data
    assert client.get("/learn/plant-food").status_code == 200
    assert b"Photosynthesis" in client.get("/learn/plant-food").data
    assert client.get("/learn/unknown").status_code == 404
