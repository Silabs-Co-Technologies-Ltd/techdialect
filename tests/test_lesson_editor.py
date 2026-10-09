"""Bilingual STEM editorial safety checks."""
import sqlite3
import pytest
from flask import Flask
import lesson_editor

@pytest.fixture
def editorial(monkeypatch):
    db=sqlite3.connect(":memory:")
    db.row_factory=sqlite3.Row
    db.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT, approved INTEGER NOT NULL DEFAULT 1)")
    db.executemany("INSERT INTO users(id,username) VALUES(?,?)",[(1,'author'),(2,'science expert'),(3,'language expert')])
    user={"id":1,"role":"admin","approved":1}
    monkeypatch.setattr(lesson_editor,"_current",lambda:(db,user))
    monkeypatch.setattr(lesson_editor, "available_editor_languages", lambda: ["Tiv", "Yoruba"])
    app=Flask(__name__)
    app.config.update(TESTING=True,SECRET_KEY="editor-test-secret")
    app.register_blueprint(lesson_editor.lesson_editor_bp)
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["data_csrf"]="editor-token"
        yield client,db,user
    db.close()

def test_unreviewed_edition_cannot_publish(editorial):
    client,db,user=editorial
    payload={"csrf_token":"editor-token","lesson_slug":"plant-food","language":"Tiv",
             "explanation":"A reviewed-language draft","example_text":"A local example",
             "question":"Sample question","options":"Correct answer\nWrong A\nWrong B"}
    assert client.post("/studio/lessons/save",data=payload).status_code==302
    row=db.execute("SELECT * FROM stem_editions").fetchone()
    assert row["published_at"] is None
    assert client.post("/studio/lessons/1/publish",data={"csrf_token":"editor-token"}).status_code==409
    assert client.post("/studio/lessons/1/science",data={"csrf_token":"editor-token"}).status_code==403
    user["id"]=2
    assert client.post("/studio/lessons/1/science",data={"csrf_token":"editor-token"}).status_code==403
    from reviewer_roles import init_reviewer_roles
    init_reviewer_roles(db)
    db.execute("INSERT INTO stem_reviewer_roles(user_id,specialty,granted_by,granted_at) VALUES(2,'science',1,'2026-10-09')")
    db.execute("INSERT INTO stem_reviewer_roles(user_id,specialty,granted_by,granted_at) VALUES(3,'language',1,'2026-10-09')")
    db.execute("INSERT INTO stem_reviewer_roles(user_id,specialty,granted_by,granted_at) VALUES(1,'science',1,'2026-10-09')")
    db.execute("INSERT INTO stem_reviewer_roles(user_id,specialty,granted_by,granted_at) VALUES(2,'language',1,'2026-10-09')")
    db.commit()
    # Even an assigned subject reviewer cannot approve their own lesson.
    user["id"]=1
    assert client.post("/studio/lessons/1/science",data={"csrf_token":"editor-token"}).status_code==403
    user["id"]=2
    assert client.post("/studio/lessons/1/science",data={"csrf_token":"editor-token"}).status_code==302
    # One person cannot perform both specialty reviews, even with both grants.
    assert client.post("/studio/lessons/1/language",data={"csrf_token":"editor-token"}).status_code==403
    user["id"]=3
    user["role"]="user"
    assert client.get("/studio/lessons/").status_code==200
    assert client.post("/studio/lessons/1/language",data={"csrf_token":"editor-token"}).status_code==302
    assert client.post("/studio/lessons/1/publish",data={"csrf_token":"editor-token"}).status_code==403
    user["role"]="admin"
    assert client.post("/studio/lessons/1/publish",data={"csrf_token":"editor-token"}).status_code==302
    assert db.execute("SELECT published_at FROM stem_editions WHERE id=1").fetchone()[0] is not None

def test_unauthorized_draft(editorial):
    client,db,user=editorial
    user["role"]="user"
    assert client.get("/studio/lessons/").status_code==403
    assert client.post("/studio/lessons/save",data={}).status_code==403

def test_unapproved_language_is_not_editable(editorial):
    client, db, actor = editorial
    response = client.post("/studio/lessons/save", data={
        "csrf_token":"editor-token", "lesson_slug":"plant-food", "language":"Unknown",
        "explanation":"Test", "example_text":"Example", "question":"Q?",
        "options":"A\\nB\\nC"
    })
    assert response.status_code == 400
