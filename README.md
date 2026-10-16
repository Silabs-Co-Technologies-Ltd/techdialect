# TechDialect

**Technology makes sense in every language.**

TechDialect, by Simeon's Laboratories and Co Technologies Ltd, is a Nigerian-language learning and data-contribution platform. It combines free STEM and adult digital-skills lessons, instructor-uploaded YouTube tutorials, and a reviewed local-language editorial workflow.

**Release candidate:** v7 is currently in Draft PR #11. **Do not promote it to production until all release gates in [docs/VERCEL_RELEASE.md](docs/VERCEL_RELEASE.md) pass.**

## Application areas

- `/`: responsive public landing page with school and adult learning discovery
- `/learn/`: 20 school STEM lessons, Primary 4 to JSS 1
- `/learn/adults`: 12 practical technology lessons for adult beginners
- `/videos/`: curator-published YouTube tutorials
- `/dashboard`: authenticated language-contributor workspace
- `/studio/lessons/`: full local-language editions and specialist review
- `/studio/reviewers/`: administrator-managed reviewer roles
- `/admin/videos/`: administrator YouTube metadata and publication management
- `/learn/progress`: device-local practice record with anonymous CSV export

## Development

Use Python 3.12. Install `requirements-dev.txt`, set `SECRET_KEY` in the environment, and run `python -m pytest -q` then `python smart_translation_system.py`. Local development uses `instance/techdialect.db`, which is excluded from Git.

**Vercel is not a persistent file host.** Production and preview environments must use a Turso remote database and separate credentials. See [Vercel release guide](docs/VERCEL_RELEASE.md) for configuration, migration commands, backups, validation and block conditions.

Never publish or train on unreviewed translations or private user data. The old tracked SQLite file may still exist in Git history and on main; handle it according to the release checklist.

## Documentation
- [Operations and reviewer workflow](docs/V7_OPERATIONS.md)
- [Vercel release gates](docs/VERCEL_RELEASE.md)
- [Development architecture](docs/TECHDIALECT_V7.md)

**License:** [MIT](LICENSE).
