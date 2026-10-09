# TechDialect v7 operations and editorial workflow

## Install and develop
1. Use Python 3.11+, then `python -m pip install -r requirements-dev.txt`.
2. Configure `SECRET_KEY` in a private environment file or deployment settings. Never copy example secrets into production.
3. Set `DATABASE_PATH` to an intentionally backed-up, persistent database location. The default development file lives under `instance/`.
4. To bootstrap a new admin, temporarily set `BOOTSTRAP_ADMIN_USERNAME`, `BOOTSTRAP_ADMIN_PASSWORD` (minimum 12 characters), and optionally `BOOTSTRAP_ADMIN_EMAIL`. Remove bootstrap environment values afterward.
5. Run `python -m pytest -q` and `python smart_translation_system.py` for local testing.

## A complete reviewed STEM learning unit
1. An administrator approves contributors in the existing user management interface.
2. An administrator opens `/studio/reviewers/` and assigns **science** and **language** specialties to appropriate approved accounts.
3. An administrator authors a draft at `/studio/lessons/`. Only approved target languages can be selected.
4. A different approved science reviewer validates concept accuracy, age-appropriateness, and examination terminology.
5. A different language reviewer validates the language, dialect and cultural meaning. Neither reviewer can be the author or the other reviewer.
6. An administrator explicitly publishes after both reviews. The lesson is then available by choosing the language at `/learn/<lesson-slug>`.
7. Editorial versions are currently immutable after publication; corrections require a versioned successor in the upcoming schema upgrade.

## Offline learning behavior
The learning page installs a service worker scoped only to `/learn/`. It pre-caches the five English starter lessons. Previously visited published local-language lesson pages are cached when accessed online. Other application routes and private administrator pages are **not** cached. This is an MVP offline experience, not full device synchronization or offline contribution uploads.

## Release blockers
- Legacy translation form CSRF and public AI endpoint rate limits need a separate security pass.
- The original SQLite database may still exist in earlier Git history. Removing the file from the working branch does not erase history.
- A persistent, backed-up production database and migration procedure must be configured before deployment; ephemeral Vercel storage is not durable.
- Ensure child-safe privacy defaults, accessibility reviews, educator signoff and dataset provenance checks.
- Keep PR #11 in draft until these gates are closed.

## Translation quality safeguards (October 2026)
- Manual, CSV and AI contributions start as `pending_review`. Pending/rejected entries are never returned as database-verified exact or fuzzy translations.
- The administrator may verify a submission. Editing any previously verified translation invalidates approval and restores `pending_review`.
- Editing does not overwrite the original author's `added_by` attribution.
- **Historical data warning:** earlier tracked SQLite datasets may have auto-assigned `verified` labels. These historical rows still need an explicit audit before relying on them for teaching or AI training. No claim is made that earlier approvals were trustworthy.
- Live AI-generated translations, if returned by an external service, must be visually identified as AI suggestions rather than human-verified content.
