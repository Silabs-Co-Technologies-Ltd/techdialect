"""Permission assignments must be explicit and restricted to administrators."""
import sqlite3
import pytest
from flask import Flask
import reviewer_roles

@pytest.fixture
def reviewer_client(monkeypatch):
    db=sqlite3.connect(":memory:")
    db.row_factory=sqlite3.Row
    db.execute("""CREATE TABLE users
        (id INTEGER PRIMARY KEY, username TEXT, approved INTEGER NOT NULL)""")
    db.executemany("INSERT INTO users VALUES (?,?,?)",[
        (1,"admin",1), (2,"teacher",1), (3,"pending",0)
    ])
    actor={"id":1,"approved":1,"role":"admin"}
    monkeypatch.setattr(reviewer_roles,"_current",lambda:(db,actor))
    app=Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    app.register_blueprint(reviewer_roles.reviewers_bp)
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["data_csrf"]="test-token"
        yield client,db,actor
    db.close()

def test_assignment_and_revocation(reviewer_client):
    client,db,actor=reviewer_client
    token="test-token"
    assert client.get("/studio/reviewers/").status_code==200
    data={"csrf_token":token,"user_id":"2","specialty":"science","decision":"grant"}
    assert client.post("/studio/reviewers/update",data=data).status_code==302
    assert reviewer_roles.has_specialty(db,{"id":2,"approved":1},"science")
    assert not reviewer_roles.has_specialty(db,{"id":2,"approved":1},"language")
    assert client.post("/studio/reviewers/update",data={**data,"decision":"revoke"}).status_code==302
    assert not reviewer_roles.has_specialty(db,{"id":2,"approved":1},"science")

def test_permission_checks(reviewer_client):
    client,db,actor=reviewer_client
    token="test-token"
    invalid={"csrf_token":token,"user_id":"3","specialty":"science","decision":"grant"}
    assert client.post("/studio/reviewers/update",data=invalid).status_code==404
    assert client.post("/studio/reviewers/update",data={**invalid,"user_id":"2","specialty":"administrator"}).status_code==400
    assert client.post("/studio/reviewers/update",data={**invalid,"user_id":"2","csrf_token":"bad"}).status_code==400
    actor["role"]="user"
    assert client.get("/studio/reviewers/").status_code==403
    assert client.post("/studio/reviewers/update",data={**invalid,"user_id":"2"}).status_code==403
