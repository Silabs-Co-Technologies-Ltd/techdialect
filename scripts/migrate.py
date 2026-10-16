"""Explicit, idempotent schema installation for a backed-up TechDialect database.

Example:
  python scripts/migrate.py --apply
  python scripts/migrate.py --apply --confirm-remote

Production Turso schema changes MUST be executed separately from a Vercel deploy.
Never run this command before creating a restorable backup.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    p = argparse.ArgumentParser(description="Install/upgrade TechDialect database schema")
    p.add_argument("--apply", action="store_true", help="Apply the schema updates")
    p.add_argument("--confirm-remote", action="store_true",
                   help="Acknowledge backup/maintenance for remote database")
    a = p.parse_args()
    from db_runtime import uses_remote_database, validate_database_configuration
    validate_database_configuration()
    if not a.apply:
        p.error("No changes made. Pass --apply after reviewing the backup.")
    if uses_remote_database() and not a.confirm_remote:
        p.error("Remote changes require --confirm-remote and a verified backup.")
    from smart_translation_system import app, init_db, get_db
    with app.app_context():
        init_db()
        db = get_db()
        from data_studio import _init as init_submissions
        from publishing import _schema as init_publications
        from reviewer_roles import init_reviewer_roles
        from lesson_editor import _init as init_editions
        from video_tutorials import _db as init_video
        init_submissions(db)
        init_publications(db)
        init_reviewer_roles(db)
        init_editions(db)
        init_video()
        tables = {"users", "languages", "translations", "language_submissions",
                  "published_terms", "stem_reviewer_roles", "stem_editions",
                  "video_tutorials", "request_quotas"}
        found = {r["name"] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        missing = tables - found
        if missing:
            raise RuntimeError("Schema verification failed; missing tables: " + ", ".join(sorted(missing)))
        print("Schema installed and verified: " + ", ".join(sorted(tables)))
        print("Backend:", "remote persistent Turso" if uses_remote_database() else "local SQLite")


if __name__ == "__main__":
    main()
