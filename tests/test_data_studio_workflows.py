"""Data Studio behavior and authorization tests, using disposable in-memory records."""
import sqlite3
import pytest
from flask import Flask
import data_studio

@pytest.fixture
def studio(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
    conn.execute("INSERT INTO users (id,username) VALUES (1,'contributor'),(2,'reviewer')")
    active = {"id": 1, "approved": 1, "role": "user"}
    monkeypatch.setattr(data_studio, "_services", lambda: (lambda: conn, lambda: active, lambda: {"Tiv", "Yoruba"}))
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="testing-only-session-key")
    app.register_blueprint(data_studio.data_bp)
    yield app.test_client(), conn, active
    conn.close()

def test_submission_requires_valid_csrf(studio):
    client, db, user = studio
    assert client.get("/data/").status_code == 200
    result = client.post("/data/submit", data={"english_text":"water", "local_text":"translation", "language":"Tiv", "context":"science","source_note":"speaker"})
    assert result.status_code == 400

def test_review_permission_and_staging(studio):
    client, db, user = studio
    client.get("/data/")
    with client.session_transaction() as sess:
        token = sess["data_csrf"]
    fields = {"csrf_token":token,"english_text":"water","local_text":"sample entry","language":"Tiv","dialect":"", "context":"chemistry vocabulary","source_note":"community reviewer"}
    assert client.post("/data/submit", data=fields).status_code == 302
    row=db.execute("SELECT * FROM language_submissions").fetchone()
    assert row["status"] == "pending"
    assert client.post(f"/data/review/{row['id']}",data={"csrf_token":token,"decision":"approved"}).status_code == 403
    user["role"]="admin"
    assert client.post(f"/data/review/{row['id']}",data={"csrf_token":token,"decision":"approved"}).status_code == 302
    approved=db.execute("SELECT * FROM language_submissions").fetchone()
    assert approved["status"] == "approved"
    assert approved["reviewer_id"] == 1

def test_invalid_language_rejected(studio):
    client,db,user=studio
    client.get("/data/")
    with client.session_transaction() as sess:
        token=sess["data_csrf"]
    result=client.post("/data/submit",data={"csrf_token":token,"english_text":"Force","local_text":"placeholder","language":"Imaginary","context":"Physics","source_note":"native speaker"})
    assert result.status_code == 400
    assert db.execute("SELECT COUNT(*) FROM language_submissions").fetchone()[0] == 0
