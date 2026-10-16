# TechDialect v7: Vercel deployment and feature-freeze gates

**State: Release candidate for review, NOT a production-approved release.**

Vercel's Flask runtime supports a root `app.py` WSGI entry point. This repository provides that entry and `.python-version` (3.12). No `build` or `output` directory is required. Importing `app.py` no longer mutates the database.

## Mandatory checks before deploying a preview or production release

1. **Preserve existing data.** Take and verify an offline backup of the current production SQLite database, users, translations, and editorial records. Account for any historic tracked `techdialect.db` file in the main branch and old commits; inspect for exposed private data and credentials. Remove/rotate affected secrets, prepare appropriate history cleanup, and record decisions. Never force-push history without a coordinated migration.
2. **Provision durable shared storage.** Create a remote Turso **Database** compatible with the `turso_serverless` Python driver. Use **separate databases and tokens for Preview and Production**. A Vercel function cannot persist TechDialect users or datasets to a local SQLite file.
3. **Set Vercel environment variables.** In Vercel Project Settings → Environment Variables add `SECRET_KEY` (random 32+ chars with high entropy), `TURSO_DATABASE_URL` (remote libsql/HTTPS URL) and `TURSO_AUTH_TOKEN` (private write-capable token) to the matching environment. Optional: `HF_TOKEN`, `DAILY_GOAL`, `TRUSTED_HOSTS`. Never commit tokens or paste them into PRs, logs or support tickets.
4. **Migrate existing state.** New remote databases are empty. The existing production SQLite data does **not** transfer automatically. Use a separately verified import/migration plan with rehearsal, row counts, foreign keys, access controls and rollback. This codebase does not yet contain a validated automated legacy-data transfer process. Do not go live while existing users or contributions would be lost.
5. **Run explicit schema migration.** From a trusted operator machine, with appropriate `TURSO_*` and `SECRET_KEY` in private environment variables and a current restorable backup, execute:
   - `python scripts/migrate.py --apply --confirm-remote`
   - `python scripts/release_preflight.py`
   The migration is not run automatically by Vercel and must be completed before promoting the new code.
6. **Run CI and verify the remote database.** `python -m pytest -q` must pass. These CI tests use local SQLite and a mocked remote DB-API; **they are not a substitute for live Turso tests**. On an isolated staging Turso database, verify registration, login, admin review, translation submission, publication, audio, editor updates, YouTube visibility, concurrent requests, error handling and restore from backup.
7. **Protect children and contributor data.** Educator review, speaker audio consent, proper privacy notices, rate limits, verified data audit, accessibility and HTTPS domain settings must be checked.
8. **Verify live pages.** Test `/`, `/learn/`, `/learn/adults`, `/videos/`, `/login`, `/dashboard`, `/admin/videos/`, `/studio/lessons/`, and mobile layout. Confirm authenticated routes are inaccessible anonymously and video/audio links load only on explicit interaction.

## Importing to Vercel

- The user's current Vercel workspace has **no confirmed TechDialect project** as of the release review. Create one through Vercel's New Project interface from the correct `Silabs-Co-Technologies-Ltd/techdialect` repository.
- **Root directory:** repository root. **Framework:** Flask/Python automatic detection. **Production branch:** main, *after* explicit merge approval. Do not deploy the draft branch to production.
- Vercel preview deploys for the PR branch can be tested after **Preview** remote database variables and migrations are configured.
- `vercel.json` defines basic platform security headers and excludes non-runtime files. The application also sets secure cookie defaults.
- Vercel runtime has no trusted persistent local SQLite file. **If `VERCEL` is set and remote credentials are missing, application startup intentionally fails**, preventing false success with disposable data.
- **Never use the same database for Preview and Production**. Both environments may write rows during tests.
- Do not configure passwords or service tokens in `vercel.json`, `.env.example`, README, Git history or client code.

## Release blockers and acceptance

Release is blocked until the user or operator can establish **all** of:
- [ ] Staging Turso provisioned and reachable from a deployed Vercel preview
- [ ] Remote schema migration and real database-backed integration tests passed
- [ ] Old production records preserved, imported if required, and reconciled
- [ ] Complete tested backup-and-restore procedure and rollback plan
- [ ] Historical tracked database privacy/security assessment and mitigation completed
- [ ] Curriculum translation/audio consent/teacher reviews verified
- [ ] Vercel Preview deployed and tested on desktop/mobile and core flows
- [ ] Security and release checks approved before merge to main

Once every gate passes, merge the reviewed PR. Let the Git-linked Vercel project deploy main, then run production smoke tests and check runtime logs. Freeze application features on the PR during final QA: **release-blocker fixes only**.

## Implementation limitations

The remote driver uses `turso_serverless` (HTTP DB-API) through a row-compatible shim. Since no authorized remote Turso credentials have been connected to this project, real remote database operations, transactional behavior under load and the import of existing production data are **not yet validated**. That is an explicit stop-ship condition, not a task to gloss over.

Vercel/Flask documentation: https://vercel.com/docs/frameworks/backend/flask
Vercel SQLite constraints: https://vercel.com/kb/guide/is-sqlite-supported-in-vercel
Turso Python quickstart: https://github.com/tursodatabase/turso-docs/blob/main/sdk/python/quickstart.mdx
