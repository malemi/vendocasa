# Active context archive

Earlier snapshots of [the active context](active-context.md), newest first. Each is kept verbatim when the living context is rewritten. They record what was true at their date and are not startup context; the current state is in the active context.

## 2026-11-25 — Before the M6 checks on real services

### State now

- **Code.** VendoCasa contains a FastAPI backend, a React/Vite frontend, OMI import scripts and Alembic migrations for PostgreSQL/PostGIS.
- **Branch.** Branch `open-product` implements the [open product with spending caps](execution-plans/2026-11-25-open-product-with-caps.md) through milestone M5. It is not merged or deployed, and production still runs the earlier anonymous build, which the owner has blocked. Milestone progress and blocked checks are tracked in the plan.
- **On that branch:**
  - every API route except `/api/health` requires a Supabase Auth account;
  - model and paid geocoding calls are charged against monthly caps ($1 per account, $100 in total) in a PostgreSQL ledger;
  - imports publish whole semesters with completion records.
- **Single worker.** Upload storage and request limits stay in process memory, which requires one worker. The Dockerfiles pin it.
- **Tests.** Backend tests are in `backend/tests/`; the real-database ones are in `backend/tests/integration/` and need `TEST_DATABASE_URL`. Frontend unit tests use Vitest. `.github/workflows/ci.yml` runs both, with PostGIS.

### Unresolved

- **Disk space.** The build machine's disk is nearly full. The real-PostgreSQL and real-PostGIS tests, the local Supabase stack, the browser checks and Docker builds have not run.
- **Production facts not established:**
  - deploy triggers and how the service is blocked;
  - database grants and exposed schemas;
  - the Supabase signing-key type and the auth settings;
  - any `ANTHROPIC_MODEL` override;
  - the loaded semesters' validation.
- **Operator-held inputs pending:**
  - Railway, Vercel and Supabase access;
  - an SMTP provider with a sending domain;
  - the owner's email;
  - a provider-reported cost source (Console reading or Admin API key).
- **Unverified claims.** Legal interpretations rest on the sources cited in [legal](legal.md). Supabase platform behavior has not been exercised locally.

### Next

- Run the blocked checks once disk space allows, then finish M6 (dependency updates, the test-prune ledger, `doc-end`) and the final review.
- With the operator-held inputs, run M7: inspection, migrations, Auth configuration, deploy, the cap test, and reopening.
