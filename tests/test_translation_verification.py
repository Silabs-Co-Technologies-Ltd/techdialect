"""New contributions must never leak into verified translation lookups."""
import os
import subprocess
import sys


def test_verification_is_required_for_lookups(tmp_path):
    env = dict(os.environ)
    env["SECRET_KEY"] = "test-only-translation-verification-key"
    env["DATABASE_PATH"] = str(tmp_path / "state" / "db.sqlite")
    for name in ("BOOTSTRAP_ADMIN_USERNAME", "BOOTSTRAP_ADMIN_PASSWORD", "BOOTSTRAP_ADMIN_EMAIL"):
        env.pop(name, None)
    program = """
from unittest.mock import patch
from smart_translation_system import app, db_insert, db_exact, db_fuzzy_candidates, db_update_translation, db_update_translation_review, get_db

with app.app_context():
    assert db_insert('Evaporation', 'Candidate in Tiv', 'Tiv', 'Basic Science', source='manual', added_by=42)
    database = get_db()
    row = database.execute("SELECT * FROM translations WHERE english_norm='evaporation'").fetchone()
    assert row['quality_status'] == 'pending_review'
    assert db_exact('evaporation', 'Tiv') is None
    assert not db_fuzzy_candidates('evaporation', 'Tiv')
    db_update_translation_review(row['id'], 'verified', reviewer_id=3)
    assert db_exact('evaporation', 'Tiv')['local_text'] == 'Candidate in Tiv'
    assert len(db_fuzzy_candidates('evaporation', 'Tiv')) == 1
    with patch('smart_translation_system.current_user', return_value={'id':3,'role':'admin'}):
        assert db_update_translation(row['id'], 'Corrected Tiv term', 'Basic Science', editor_id=3) == 'Tiv'
    edited = database.execute("SELECT * FROM translations WHERE id=?", (row['id'],)).fetchone()
    assert edited['quality_status'] == 'pending_review'
    assert edited['added_by'] == 42
    assert edited['verified_by'] is None
    assert edited['verified_at'] is None
    assert db_exact('evaporation', 'Tiv') is None
    assert not db_fuzzy_candidates('evaporation', 'Tiv')
    db_update_translation_review(row['id'], 'rejected', reviewer_id=3)
    assert db_exact('evaporation', 'Tiv') is None
    # AI-sourced suggestions also enter the review queue.
    assert db_insert('Fraction', 'Candidate text', 'Tiv', 'Mathematics', source='ai', added_by=42)
    assert database.execute("SELECT quality_status FROM translations WHERE english_norm='fraction'").fetchone()[0] == 'pending_review'
"""
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=35
    )
    assert completed.returncode == 0, completed.stderr[-4500:]
