"""Full application import smoke test with a fresh isolated database."""
import os
import subprocess
import sys

def test_application_boots_cleanly(tmp_path):
    env = os.environ.copy()
    env["SECRET_KEY"] = "integration-test-only-not-a-production-secret"
    env["DATABASE_PATH"] = str(tmp_path / "runtime" / "techdialect.db")
    for name in ("BOOTSTRAP_ADMIN_USERNAME","BOOTSTRAP_ADMIN_PASSWORD","BOOTSTRAP_ADMIN_EMAIL"):
        env.pop(name, None)
    script = """
from smart_translation_system import app
with app.test_client() as client:
    assert client.get('/learn/').status_code == 200
    assert client.get('/learn/plant-food').status_code == 200
    assert client.get('/learn/sw.js').status_code == 200
    r=client.get('/data/terms')
    assert r.status_code == 200, (r.status_code,r.data[:400])
    assert r.json['count'] == 0
    assert client.get('/studio/lessons/').status_code == 403
    assert client.get('/studio/reviewers/').status_code == 403
    assert client.get('/logout').status_code == 405
    login_page = client.get('/login')
    assert login_page.status_code == 200
    assert b'name="csrf_token"' in login_page.data
    assert client.post('/login', data={'username': 'attacker', 'password': 'invalid'}).status_code == 400
    with client.session_transaction() as sess:
        csrf = sess['_legacy_csrf']
    assert client.post('/login', data={'csrf_token': csrf, 'username': 'attacker', 'password': 'invalid'}).status_code == 302
    assert client.post('/logout', data={}).status_code == 400
    assert client.post('/logout', data={'csrf_token': csrf}).status_code == 302
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=os.getcwd(),
        env=env, capture_output=True, text=True, timeout=35
    )
    assert result.returncode == 0, result.stderr[-4000:]
    assert (tmp_path / "runtime" / "techdialect.db").exists()
