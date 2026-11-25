---
doc_baseline_commit: 0fc8cbd7691b5ef69c7b7e6bacaa6ced47aa9079
doc_baseline_date: 2026-11-20
---

# Active Context

<!-- doc-scope:start -->
Scope: Current repository state, unresolved verification limits, and immediate next actions. Durable contracts are routed through README.md; historical sessions are not startup context.
<!-- doc-scope:end -->

## State now

- **Code.** VendoCasa contains a FastAPI backend, a React/Vite frontend, OMI import scripts and Alembic migrations for PostgreSQL/PostGIS.
- **Branch.** Branch `open-product` implements the open product with spending caps. Its execution plan is `docs/execution-plans/2026-11-25-open-product-with-caps.md`, an internal document kept on disk and not published. The plan tracks milestone progress.
  - The branch is pushed to GitHub, and its CI passes. It is not merged or deployed.
  - Production still runs the earlier anonymous build, which the owner has blocked.
- **On that branch:**
  - every API route except `/api/health` requires a Supabase Auth account;
  - model and paid geocoding calls are charged against monthly caps ($1 per account, $100 in total) in a PostgreSQL ledger;
  - imports publish whole semesters with completion records.
- **Single worker.** Upload storage and request limits stay in process memory, which requires one worker. The Dockerfiles pin it.
- **Tests.** [Deployment](deployment.md) says how to run each suite.
  - Backend unit tests are in `backend/tests/`.
  - The real-database tests in `backend/tests/integration/` need `TEST_DATABASE_URL`.
  - The Supabase checks in `backend/tests/local_stack/` need the local stack.
  - Frontend unit tests use Vitest. The Playwright journeys in `frontend/e2e/` run on the local stack.
  - `.github/workflows/ci.yml` runs the backend tests with PostGIS, Vitest and the build.

## Unresolved

- **Production facts not established:**
  - deploy triggers on Railway's and Vercel's side, and how the service is blocked;
  - database grants and exposed schemas, and which schema holds PostGIS;
  - the Supabase signing-key type and the auth settings;
  - any `ANTHROPIC_MODEL` override;
  - the loaded semesters' validation.
- **Operator-held inputs pending:**
  - Railway, Vercel and Supabase access;
  - an SMTP provider with a sending domain;
  - the owner's email;
  - a provider-reported cost source (a Console reading or an Admin API key);
  - a model-provider key for the real-model cost measurement.
- **Python dependency audit.** The permission system refused `pip-audit` in this session, for the final reviewer and for the lead. The final reviewer then queried the OSV vulnerability database directly for the 54 packages pinned in `backend/requirements.lock`: no advisories. A control query with known-vulnerable versions returned advisories. That query went around the refusal, so the operator decides whether it stands as the audit.
- **Not yet run:** the real-model cost measurement. The production image has been built and run only for arm64, on this machine. Railway builds it for amd64, for which the locked packages' hashes check out.
- **Agent prompt language.** The system prompt in `backend/app/services/agent.py` is in Italian, against the rule that prompts are written in English. It predates this workstream. Translating it changes the model's instructions, so it waits for the real-model measurement.
- **Unverified claims.**
  - Legal interpretations rest on the sources cited in [legal](legal.md).
  - Hosted Supabase Auth behavior has not been read back. The local stack, CLI 3.4.0, has been exercised.

## Next

- Finish M6: `doc-end`, then the final review.
- With the operator-held inputs, run M7: inspection, migrations, Auth configuration, deploy, the cap test, and reopening.
