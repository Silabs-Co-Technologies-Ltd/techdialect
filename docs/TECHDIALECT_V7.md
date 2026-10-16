# TechDialect v7: STEM learning and language-data infrastructure

## Mission
Help Nigerian learners understand foundational STEM concepts through trustworthy bilingual resources while collecting consented, reviewed local-language material for education and AI research.

## Two product tracks
1. **Learn:** curriculum-aligned STEM lessons, quizzes, audio, offline packs and school dashboards.
2. **Data Studio:** terminology, variants, recordings, reviewer queues, provenance, licenses and reproducible dataset versions.

## Current implemented slice
- English STEM learning catalogue at `/learn/` with five sample lessons and responsive quiz UI.
- Explicit labelling: local-language editions are **not** available until reviewed.
- Mandatory app secret, optional environment-based admin bootstrap, example configuration, tests and CI.
- Existing Flask translation workflows remain in place.

## Next build milestones
- Replace legacy monolith with modular application factory and migration system.
- Add reviewer roles and a structured bilingual lesson schema.
- Import the existing multilingual CSV only after duplicate, provenance, dialect and licensing review.
- Build 20 educator-reviewed lessons, beginning with English and Tiv.
- Add offline lesson packs, real learning-progress persistence, and child privacy safeguards.
- Move persistent production records to managed PostgreSQL.

## Dataset quality rules
Each translated learning unit needs: language and dialect identifier, English source, local text, contributor/consent record, educational level, subject, reviewer IDs, review time, quality status, source/license and dataset version. AI output must never automatically become verified training data.

## Release gates
No production rollout until security review, production secret rotation, CSRF protection, API rate limiting, data privacy review, migration validation, backup/restore rehearsal, and accessibility checks.

## Existing database caution
`techdialect.db` is already tracked in the repository history. Gitignore alone does NOT remove it or eliminate previous Git copies. Inspect whether it contains real users; if so treat exposure as an incident, rotate credentials and plan coordinated history rewriting before another public release.
