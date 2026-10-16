"""Storage is fail-closed on Vercel and preserves SQLite row compatibility."""
import sqlite3
import sys
import subprocess
import os
import types

import pytest
import db_runtime


def test_local_sqlite_and_row_support(tmp_path, monkeypatch):
    monkeypatch.setattr(db_runtime, "IS_VERCEL", False)
    monkeypatch.setattr(db_runtime, "REMOTE_URL", "")
    monkeypatch.setattr(db_runtime, "REMOTE_TOKEN", "")
    conn=db_runtime.connect(str(tmp_path / "local.db"))
    conn.execute("CREATE TABLE demo(id INTEGER PRIMARY KEY, title TEXT)")
    conn.execute("INSERT INTO demo(title) VALUES(?)", ("Example",))
    conn.commit()
    row=conn.execute("SELECT id,title FROM demo").fetchone()
    assert row["title"]=="Example"
    assert row[0]==1
    conn.close()


def test_vercel_without_remote_database_fails_closed(monkeypatch):
    monkeypatch.setattr(db_runtime, "IS_VERCEL", True)
    monkeypatch.setattr(db_runtime, "REMOTE_URL", "")
    monkeypatch.setattr(db_runtime, "REMOTE_TOKEN", "")
    with pytest.raises(RuntimeError, match="require persistent"):
        db_runtime.validate_database_configuration()


def test_partial_remote_settings_rejected(monkeypatch):
    monkeypatch.setattr(db_runtime, "IS_VERCEL", False)
    monkeypatch.setattr(db_runtime, "REMOTE_URL", "libsql://sample.example.turso.io")
    monkeypatch.setattr(db_runtime, "REMOTE_TOKEN", "")
    with pytest.raises(RuntimeError, match="Both TURSO"):
        db_runtime.validate_database_configuration()


def test_remote_adapter_with_fake_dbapi_driver(tmp_path, monkeypatch):
    """Contract test using sqlite3 as a stand-in; not a live Turso verification."""
    monkeypatch.setattr(db_runtime, "IS_VERCEL", True)
    monkeypatch.setattr(db_runtime, "REMOTE_URL", "libsql://fake.turso.io")
    monkeypatch.setattr(db_runtime, "REMOTE_TOKEN", "fake-test-token")
    driver=types.SimpleNamespace(
        connect=lambda url, auth_token: sqlite3.connect(":memory:")
    )
    monkeypatch.setitem(sys.modules,"turso_serverless",driver)
    conn=db_runtime.connect(str(tmp_path/"must-not-be-used.db"))
    conn.execute("CREATE TABLE demo(id INTEGER PRIMARY KEY, title TEXT)")
    assert conn.execute("INSERT INTO demo(title) VALUES(?)",("Sample",)).rowcount==1
    result=conn.execute("SELECT id,title FROM demo")
    row=result.fetchone()
    assert row[0]==1
    assert row["title"]=="Sample"
    assert row.keys()==["id","title"]
    assert dict(row)=={"id":1,"title":"Sample"}
    assert conn.execute("SELECT id,title FROM demo").fetchall()[0]["title"]=="Sample"
    conn.close()
    assert not (tmp_path/"must-not-be-used.db").exists()


def test_application_import_on_vercel_without_storage_fails(tmp_path):
    env=os.environ.copy()
    env["VERCEL"]="1"
    env["SECRET_KEY"]="a1B2c3D4e5F6g7H8i9J0KLMnopQRstUVWxyz"
    for name in ("TURSO_DATABASE_URL","TURSO_AUTH_TOKEN"):
        env.pop(name,None)
    env["DATABASE_PATH"]=str(tmp_path/"must-not-be-created.db")
    p=subprocess.run([sys.executable,"-c","import app"],env=env,
                     capture_output=True,text=True,timeout=15)
    assert p.returncode!=0
    assert "Vercel deployments require persistent" in p.stderr
    assert not (tmp_path/"must-not-be-created.db").exists()



def test_migration_and_preflight_on_fresh_local_database(tmp_path):
    env=os.environ.copy()
    env["SECRET_KEY"]="integration-local-only-not-for-production"
    env["DATABASE_PATH"]=str(tmp_path/"installation.db")
    for key in ("VERCEL","VERCEL_ENV","TURSO_DATABASE_URL","TURSO_AUTH_TOKEN"):
        env.pop(key,None)
    migrate=subprocess.run(
        [sys.executable,"scripts/migrate.py","--apply"],
        env=env,text=True,capture_output=True,timeout=35
    )
    assert migrate.returncode==0, migrate.stderr[-4000:]
    assert "Schema installed and verified" in migrate.stdout
    preflight=subprocess.run(
        [sys.executable,"scripts/release_preflight.py"],
        env=env,text=True,capture_output=True,timeout=35
    )
    assert preflight.returncode==0, preflight.stderr[-4000:]
    assert "PASS" in preflight.stdout


def test_vercel_import_with_remote_config_does_not_initialize_sqlite(tmp_path):
    env=os.environ.copy()
    env["VERCEL"]="1"
    env["SECRET_KEY"]="strong-remote-staging-example-secret-"+"x"*32
    env["TURSO_DATABASE_URL"]="libsql://fake.turso.io"
    env["TURSO_AUTH_TOKEN"]="test-only-not-real"
    env["DATABASE_PATH"]=str(tmp_path/"should-not-exist.db")
    program = """
import sqlite3,sys,types
sys.modules['turso_serverless']=types.SimpleNamespace(
    connect=lambda url,auth_token: sqlite3.connect(':memory:'))
from app import app
with app.test_client() as client:
    result=client.get('/')
    assert result.status_code == 200, result.data[:400]
    assert b'TechDialect' in result.data
"""
    run=subprocess.run([sys.executable,"-c",program],env=env,
        text=True,capture_output=True,timeout=25)
    assert run.returncode==0,run.stderr[-4000:]
    assert not (tmp_path/"should-not-exist.db").exists()


def test_production_rejects_short_secret_without_db_access(tmp_path):
    env=os.environ.copy()
    env["VERCEL"]="1"
    env["SECRET_KEY"]="weak-secret"
    env["TURSO_DATABASE_URL"]="libsql://fake.turso.io"
    env["TURSO_AUTH_TOKEN"]="private-placeholder"
    env["DATABASE_PATH"]=str(tmp_path/"do-not-create.db")
    p=subprocess.run([sys.executable,"-c","import app"],env=env,
        text=True,capture_output=True,timeout=15)
    assert p.returncode!=0
    assert "strong, random SECRET_KEY" in p.stderr
    assert not (tmp_path/"do-not-create.db").exists()
