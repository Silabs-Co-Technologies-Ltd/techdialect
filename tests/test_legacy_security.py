"""Legacy form protection and request quota tests using isolated Flask apps."""
import sqlite3

from flask import Flask, request

from legacy_security import install_legacy_security, LIMITS


def app_and_connection():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test-only-secret")
    db = sqlite3.connect(":memory:")
    install_legacy_security(app, lambda: db)

    @app.get("/login")
    def login_form():
        return '<html><head><title>Login</title></head><body><form method="POST"><input name="username"></form></body></html>'

    @app.post("/login")
    def login_post():
        return "OK"

    @app.post("/translate_article")
    def logged_in_article():
        return "OK"

    @app.get("/api/translate")
    def public_api():
        return "OK"

    @app.post("/api/translate_article")
    def public_json_api():
        return "OK"

    return app, db


def test_legacy_form_receives_token_and_rejects_forgery():
    app, db = app_and_connection()
    try:
        client = app.test_client()
        result = client.get("/login")
        assert result.status_code == 200
        assert b'name="csrf_token"' in result.data
        assert b'name="csrf-token"' in result.data
        assert result.headers["Cache-Control"] == "private, no-store"
        assert client.post("/login", data={"username": "a"}).status_code == 400
        with client.session_transaction() as session:
            token = session["_legacy_csrf"]
        assert client.post("/login", data={"csrf_token": token}).status_code == 200
        assert client.post("/login", data={"csrf_token": "invalid"}).status_code == 400
        assert client.post("/translate_article", json={"text": "Example"}).status_code == 400
        assert client.post("/translate_article", json={"text": "Example"},
                           headers={"X-CSRF-Token": token}).status_code == 200
    finally:
        db.close()


def test_limits_and_rate_limit_headers():
    app, db = app_and_connection()
    try:
        client = app.test_client()
        limit = LIMITS["GET", "/api/translate"]
        for _ in range(limit):
            assert client.get("/api/translate").status_code == 200
        exceeded = client.get("/api/translate")
        assert exceeded.status_code == 429
        assert exceeded.json["error"].startswith("Rate limit exceeded")
        assert int(exceeded.headers["Retry-After"]) > 0
        assert client.post("/api/translate_article", json={"text": "Example"}).status_code == 200
        assert db.execute("SELECT COUNT(*) FROM request_quotas").fetchone()[0] > 0
    finally:
        db.close()
