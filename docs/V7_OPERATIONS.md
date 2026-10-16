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

## Curriculum pathways and device-local progress
- `/learn/`: starter class pathways for Primary 4, Primary 5 and JSS 1, plus direct links to the first five lessons.
- `/learn/path/<path-slug>`: class-level learning sequence, ordered by planned learning progression.
- `/learn/progress`: device-only lesson mastery counts and correct/attempts figures. Can export an anonymous CSV locally; export does not upload names or learning data.
- Quiz attempts are measured locally, one short check per lesson, and do **not** replace teacher assessment.
- `/learn/progress.js` and public pathway/report pages are cached for offline use under the STEM-only service worker scope.
- Class levels are editorial **pilot groupings**, not an assertion of NERDC approval or full Nigerian national curriculum coverage.

## Video tutorials: YouTube publishing workflow
- The public library is `/videos/`; the admin dashboard is `/admin/videos/`, linked from both the TechDialect dashboard and the legacy admin page.
- Upload tutorial files **to your own YouTube account first**. TechDialect saves only the URL's validated video ID, title, description, language, optional linked STEM lesson, and visibility.
- Paste an HTTPS `youtube.com/watch?v=...`, `youtube.com/shorts/...`, `youtube.com/live/...`, `youtube.com/embed/...` or `youtu.be/...` URL. Unknown hosts, HTTP links, iframe markup and malformed IDs are rejected.
- New tutorials begin as **drafts** and are visible only to administrators. Publish them explicitly to list them in the public video library or alongside their selected lesson. Unpublish to remove them immediately; editing resets them to draft.
- Learners select **Play** before the browser creates an iframe on `youtube-nocookie.com`. Loading that third-party player still sends information to YouTube, so learners should be informed. YouTube streams are **not** saved offline.
- A tutorial should be set to Public or Unlisted on YouTube and embedding must be allowed. Private or restricted videos cannot be played by visitors.
- For young learners, administrators should use age-appropriate content, review subtitles and descriptions, and avoid relying on YouTube autoplay or collecting viewing analytics.
- Persistent production storage is still necessary: SQLite on ephemeral Vercel storage will lose edits. This v7 draft is not yet production-approved.

## Twenty English STEM starter lessons
- The pilot curriculum now contains **20 English lessons**: seven Primary 4, seven Primary 5 and six JSS 1.
- All 20 have one short multiple-choice practice check and offline-first public pages. Use the YouTube tutorial editor to connect your own published videos to any lesson.
- Language translations are **not** auto-generated or automatically approved. Every localized lesson still goes through specialist science and language review.
- Curriculum examples need classroom educator review and appropriate regional context before school adoption.
