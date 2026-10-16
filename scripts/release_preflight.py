"""Non-mutating application release checks.

Use this after migrations have been applied to the intended staging database:
  python scripts/release_preflight.py

Exit code 1: release is blocked.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from db_runtime import validate_database_configuration, uses_remote_database, connect
    validate_database_configuration()
    if (os.getenv("VERCEL") or os.getenv("VERCEL_ENV")) and not uses_remote_database():
        raise SystemExit("BLOCKED: Vercel requires remote persistent storage.")
    if (os.getenv("VERCEL") or os.getenv("VERCEL_ENV")) and len(os.getenv("SECRET_KEY", "")) < 32:
        raise SystemExit("BLOCKED: Production SECRET_KEY is too short.")
    from smart_translation_system import DB_PATH
    try:
        db = connect(DB_PATH)
        tables = {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        needed = {"users", "languages", "translations", "language_submissions",
                  "stem_editions", "video_tutorials", "published_terms",
                  "request_quotas", "stem_reviewer_roles"}
        missing = needed - tables
        if missing:
            raise RuntimeError("Missing migration tables: " + ", ".join(sorted(missing)))
        columns = {r[1] for r in db.execute("PRAGMA table_info(stem_editions)").fetchall()}
        if not {"steps_json", "task_text", "audio_url"} <= columns:
            raise RuntimeError("STEM edition migrations are incomplete.")
        db.execute("SELECT 1").fetchone()
        db.close()
    except Exception as exc:
        raise SystemExit("BLOCKED: Database readiness check failed: " + str(exc)) from exc
    print("PASS: Persistent database reachable and required tables present")
    print("IMPORTANT: CI cannot prove live backup recovery, previous leaked data remediation, "
          "or translated material review. Verify separately before production release.")


if __name__ == "__main__":
    main()
