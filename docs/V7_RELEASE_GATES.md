# V7 continuation: database isolation and quality gates

## Database lifecycle
Runtime files belong in `instance/`, which must never be committed. The original tracked database was deleted from the v7 branch, not from historical commits or the default branch. Database history removal and incident assessment remain separate actions.

## Verification requirements
- Run automated Python syntax compilation for all application modules.
- Test lesson routes and data submission validation using Flask's test client.
- Verify reviewer authorization, CSRF rejection, and staging-only approvals.
- Perform manual tests against a clean database and a restored backup.
- Review public API rate limits and cross-site request forgery protection before deployment.

## Publishing safeguards
Language submissions must remain staged until independently verified. Every approved publication should retain contributor attribution, dialect, license, provenance, reviewer identity, and version.
