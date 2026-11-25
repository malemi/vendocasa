# Test audit: open product with spending caps

## Scope and source state

- **Workstream:** the execution plan `docs/execution-plans/2026-11-25-open-product-with-caps.md`, under the approved brief `docs/briefs/2026-11-22-secure-pilot-and-test-prune.md`, scope 6. Both are internal working documents, kept on disk and not published.
- **Scope:** the 24 backend tests in `backend/tests/`, their fixtures (`conftest.py`) and fakes (`fakes.py`), and the production paths they cover. New regression tests written in M2–M5 receive the same review before they are kept.
- **Source state:**
  - Commit `0fc8cbd7691b5ef69c7b7e6bacaa6ced47aa9079`, on branch `open-product`, created from `main` on 2026-11-25.
  - The uncommitted documentation-harness work (`AGENTS.md`, `docs/`) predates this workstream and is preserved.
- **Before-bytes:**
  - The exact bytes of every file in `backend/tests/` are retained in `/tmp/vendocasa-impl/m1/original-tests/`, with `SHA256SUMS`, the collected node IDs (`node-ids.txt`), `git status`, the tracked diff and `HEAD`.
  - That path is temporary evidence. This record keeps the hashes below.

| File | SHA-256 |
|---|---|
| `conftest.py` | `e2d5b60f6af2f21c029b043fad0c98996fcb70fb1a12e3667ed622a7553a8598` |
| `fakes.py` | `f798b4463560f05f24a7d726439c500bc5c4974410537d4f4ca8f07bac20e1c5` |
| `test_agent.py` | `7eaa0e0138a06f283c0977e3b0ae8c297c8cc13cd6b15368cc00d38ab9aac5ab` |
| `test_chat_caps.py` | `9d9b8820a7284f8cb90021fbd6aa3e07838bfe11f6109f08de308041b9a76eb5` |
| `test_main.py` | `cbeaf58d77a84527a9a32de1edf010bb1f83032c8b44adaa5fb46fca970cf438` |
| `test_rate_limit.py` | `b5cefcd2dfab8994de8e1c3785fe22970b51898ae4406fb34ddd64418715612a` |

## Baseline

- Command: `.venv/bin/python -m pytest -q`, from `backend/`, on 2026-11-25, in a fresh `uv` environment with the then-unlocked dependency graph.
- Result: 24 passed, exit 0. The log is `/tmp/vendocasa-impl/m0-baseline/pytest.log`.
- The only warning is the pytest-asyncio notice that the fixture loop scope is unset.

## Original tests and provisional dispositions

The dispositions below are provisional. Each one becomes a decision, with its reason recorded here before the test is edited. That happens in the milestone that changes the contract under test. The plan's rule applies: a test is kept, rewritten for the new contract, merged into a surviving test that keeps its preconditions, or retired with a reason.

Eleven tests post anonymously to `/api/chat`: 5 in `test_chat_caps.py` and 6 in `test_rate_limit.py`. M2 makes `/api/chat` require an account, so those eleven move to authenticated requests in M2. Their guarantees are otherwise unchanged.

| Test | Guarantee | Provisional disposition |
|---|---|---|
| `test_agent.py::test_loop_stops_at_max_tool_rounds` | A model that keeps requesting tools stops at the round cap | Keep |
| `test_agent.py::test_loop_stops_early_when_global_ceiling_hit` | The global daily model-call ceiling stops the loop mid-request | Keep; the ceiling stays (plan amendment of 2026-11-25). M2 adds its Italian refusal message (plan note P2) |
| `test_agent.py::test_model_id_is_server_config_only` | The model sent to the provider comes only from settings | Keep; M3 changes the default model, not the guarantee |
| `test_agent.py::test_sse_error_event_never_forwards_raw_exception_text` | Provider error detail never reaches the client | Keep |
| `test_agent.py::test_base_url_passed_explicitly` | The SDK client never falls back to an ambient base URL | Rewrite in M2: a non-canonical configured base URL refuses startup. The explicit-argument check stays |
| `test_chat_caps.py::test_history_length_cap_returns_400` | Over-long history is refused before the provider | Rewrite in M2 (authenticated); M4 raises the cap to 50 |
| `test_chat_caps.py::test_message_length_cap_returns_400` | An over-long message is refused before the provider | Rewrite in M2 (authenticated) |
| `test_chat_caps.py::test_within_caps_is_not_rejected` | Requests within the caps are accepted | Rewrite in M2 (authenticated); candidate to merge into the authenticated happy path |
| `test_chat_caps.py::test_attachment_byte_budget_returns_400` | One oversized attachment set is refused | Rewrite in M2 (authenticated, own uploads) |
| `test_chat_caps.py::test_attachment_byte_budget_sums_across_messages` | The attachment budget sums across messages | Rewrite in M2 (authenticated, own uploads); stays distinct from the single-attachment case |
| `test_main.py::test_docs_disabled_by_default` | Interactive API docs are off by default | Keep |
| `test_main.py::test_startup_fails_fast_without_anthropic_api_key` | The backend refuses to start without a model key | Keep |
| `test_rate_limit.py::test_per_minute_limit_returns_429` | The per-minute limit refuses with `Retry-After` | Rewrite in M2 (account identity) |
| `test_rate_limit.py::test_per_day_limit_returns_429` | The per-day limit refuses | Rewrite in M2 (account identity) |
| `test_rate_limit.py::test_global_ceiling_returns_503` | The global ceiling refuses new requests | Rewrite in M2 (authenticated); refusal code and Italian message per P2 |
| `test_rate_limit.py::test_ip_fallback_survives_cookie_deletion` | A new cookie on the same IP does not reset the budget | Transfer in M2: switching accounts from one IP does not reset the IP limit. The cookie identity is retired because the cookie is removed |
| `test_rate_limit.py::test_store_sweeps_expired_windows` | Expired windows do not accumulate in memory | Keep |
| `test_rate_limit.py::test_get_client_ip_ignores_x_envoy_external_address_entirely` | The Envoy header never sets the client IP | Keep |
| `test_rate_limit.py::test_get_client_ip_ignores_envoy_header_when_xff_absent` | Without XFF, a forged Envoy header is ignored | Keep |
| `test_rate_limit.py::test_get_client_ip_ignores_caller_supplied_leftmost_hop` | The caller-written leftmost XFF hop is ignored | Keep |
| `test_rate_limit.py::test_get_client_ip_falls_back_to_request_client_host` | Without XFF, the transport peer is used | Keep |
| `test_rate_limit.py::test_rotating_leftmost_xff_with_no_cookie_still_gets_limited` | Rotating the leftmost XFF hop does not evade the limit | Rewrite in M2 (authenticated); the evasion now targets the IP limit with one account |
| `test_rate_limit.py::test_forged_envoy_header_with_xff_present_still_gets_limited` | A rotated forged Envoy header does not evade the limit | Rewrite in M2 (authenticated) |
| `test_rate_limit.py::test_forged_envoy_header_without_xff_does_not_bypass` | Without XFF, a rotated Envoy header mints no new identity | Rewrite in M2 (authenticated) |

## Decisions

### M2 — accounts and access (recorded 2026-11-25, before the edits)

M2 makes every `/api/` route require a verified account (`backend/app/auth.py`), removes the `vendocasa_uid` cookie identity, and keeps the per-IP limits and the global daily ceiling. The test fixtures gain an HS256 test signing secret, a token helper and a fixed test disposable-domain set. No test is deleted.

| Test | Decision | Reason |
|---|---|---|
| The five `test_chat_caps.py` tests | Rewrite: same assertions, sent with an account token. The attachment tests store their documents under the requesting account | `/api/chat` refuses anonymous requests now. The single-attachment and cross-message cases stay separate, because they catch different summing bugs |
| `test_per_minute_limit_returns_429`, `test_per_day_limit_returns_429` | Rewrite: one account sends the requests | The windows are unchanged, and only the identity source changes |
| `test_global_ceiling_returns_503` | Rewrite: authenticated. The refusal code changes from `service_unavailable` to `daily_limit`, with its Italian message | Intentional contract change: refusals now carry Italian messages (brief scope 1, plan note P2). The guarantee, refusal before any provider call, is unchanged |
| `test_ip_fallback_survives_cookie_deletion` | Transfer to `test_ip_limit_survives_switching_accounts` | The cookie identity no longer exists. The surviving guarantee is the same precondition with accounts: once one address has exhausted its IP limit, a different account from that address is still refused |
| `test_rotating_leftmost_xff_with_no_cookie_still_gets_limited` (renamed `test_rotating_leftmost_xff_with_fresh_accounts_still_gets_limited`), `test_forged_envoy_header_with_xff_present_still_gets_limited`, `test_forged_envoy_header_without_xff_does_not_bypass` | Rewrite: each request uses a fresh account. The first is renamed, because it no longer depends on a cookie | A fresh account per request is the analogue of the old cookie-less request. It keeps the account limit from masking the IP limit, so each test still proves that header forgery cannot evade the IP limit |
| `test_loop_stops_early_when_global_ceiling_hit` | Keep, and also assert the `daily_limit` error event before `done` | Intentional contract change (P2). The loop previously ended silently, and the user now sees why |
| `test_sse_error_event_never_forwards_raw_exception_text` | Keep. The expected text changes from the English "temporarily unavailable" to the `assistant_unavailable` code and its Italian message | Intentional contract change: the user sees Italian text (brief scope 1). The guarantee, no raw provider detail in the event, is unchanged |
| `test_base_url_passed_explicitly` | Keep | The explicit SDK argument is still the mechanism that ignores an ambient variable. The new startup refusal is a separate test in `test_main.py` |
| `test_startup_fails_fast_without_anthropic_api_key` | Keep. Its subprocess now sets `PYTHONPATH` to `backend/` | The subprocess imported `app` only through the editable install. A lock-only environment, such as CI, has none |
| All other originals | Keep unchanged | Their contracts do not change in M2 |

### M3 — spending caps, model and bounds (recorded 2026-11-25, before the edits)

| Test | Decision | Reason |
|---|---|---|
| The five `test_agent.py` tests | Rewrite: call `run_agent_stream` with the account to charge. The fakes gain token counting, usage and a stop reason | Signature change only. Every model round is now reserved and settled against an account. Each test's guarantee and its assertions are unchanged |
| `test_model_id_is_server_config_only` | Keep. The test now registers a price for its pinned model | Unpriced models are now refused before any call. Without a price the test would pass for the wrong reason, or fail. The new `test_an_unpriced_model_is_refused_before_any_call` covers the refusal itself |
| `test_access.py::test_an_upload_belongs_to_its_account`, `::test_foreign_and_missing_documents_are_indistinguishable` (M2) | Rewrite: assert the `document_expired` refusal code. The indistinguishability check compares whole bodies | Intentional contract change in M4: the refusal is machine-readable, so the client can re-upload. The guarantee, that a foreign document looks exactly like a missing one, is stronger now, because the bodies are equal with no ID in them |
| All tests that post to `/api/chat` | Keep. An autouse in-memory ledger (`tests/fakes.py::FakeLedger`) stands in for the database | Unit tests have no database. The ledger's own rules are tested on real PostgreSQL in `tests/integration/test_spend_ledger.py` |

### M2 evidence

- **Rewritten originals and new tests.** `.venv/bin/python -m pytest -q` from `backend/` gives 144 passed, exit 0. The log is `/tmp/vendocasa-impl/m2/pytest-after.log`. The 24 originals keep their guarantees under the decisions above. One new startup test is added, and two new modules: `tests/test_auth.py` (token verification, 17 cases) and `tests/test_access.py` (the route matrix and ownership, 102 cases).
- **Failing before the fix.** The new tests ran against the unfixed commit `0fc8cbd`, in a temporary worktree held in memory under `/dev/shm`, so as to use no disk:
  - `tests/test_access.py`: 98 of 102 cases fail. For example, an anonymous `/api/chat` returns `200` instead of `401`, a `system` role returns `200` instead of `422`, and another account can use an upload. The four that pass were already true before: the public health check, the CORS preflight, accepted user and assistant roles, and readable transactions. The log is `/tmp/vendocasa-impl/m2/access-on-unfixed-code.log`.
  - `tests/test_main.py::test_startup_refuses_a_non_canonical_anthropic_base_url` fails, because the unfixed code only logged the override. The log is `/tmp/vendocasa-impl/m2/base-url-on-unfixed-code.log`.
  - `tests/test_auth.py` cannot run against the unfixed code, which has no token verifier at all. That absence is the defect the module covers.
- **Strengthened assertions.** The two attachment-budget tests now also assert that the refusal is the byte budget (`Allegati troppo grandi`), not a missing document, which is also a `400`. Without this, an ownership bug that hid the document would let both tests pass vacuously.
- **Prune review of the new tests.** The 91 matrix cases are kept: each route, crossed with each credential defect, is a distinct way a newly added route could ship unprotected. The parametrized claim cases in `test_auth.py` are kept: each claim is a separate check in `verify_token`.

### M3 evidence

- **Failing before.** A throwaway probe on the unfixed `0fc8cbd`, in a temporary RAM worktree, fails all six M3 bounds with the old API:
  - a 2 MB chat body is parsed in full (no 413);
  - a 7 MB upload is read before the size check;
  - 25 MB of uploads for one identity are all accepted;
  - `limit=101` on transactions is ignored;
  - zone GeoJSON without a bounding box is served;
  - no spending ledger exists (`app.services.spending` is absent).

  The log is `/tmp/vendocasa-impl/m3/bounds-on-unfixed-code.log`. The probe and its worktree were removed.
- **Not reproducible before.** Settlement, Google charging and pricing have no pre-fix behavior to fail. The features were absent, and the ledger-absent probe covers that.
- **Prune review of the new M3 tests.** All kept:
  - `test_pricing.py` (7) and `test_body_limit.py` (6), including the API-level chunked 413 case added after review: distinct arithmetic and parsing rules.
  - `test_spending_flow.py` (22): each case is a separate route or loop guarantee:
    - reservation and settlement;
    - error and cancellation settlement;
    - the cap mid-stream;
    - model refusal;
    - client options;
    - three door refusals;
    - concurrency, and a stale stream entry;
    - Google charging and skipping;
    - quotas;
    - pagination and the bounding box;
    - upload size, caps and expiry;
    - owner routes;
    - secrets.

    The FakeLedger cases do not duplicate `tests/integration/test_spend_ledger.py` (11). Those test the real transactions, locking, crash recovery and the month boundary, which the fake cannot.
- **After review (B2).** `test_auth.py::test_a_failed_key_fetch_is_unavailable_never_invalid` was added for the key-fetch failure path. Kept: no other test fails a JWKS fetch.

### M4 evidence

- **SSE parser.** The parser in `frontend/src/api/sse.ts` has tests in `frontend/src/api/sse.test.ts` (8 cases):
  - every two-part split of a five-frame stream with multi-byte UTF-8;
  - single-byte feeds;
  - CRLF and CR endings at every split;
  - multi-line data and comments;
  - incomplete endings and malformed JSON, which are reported as errors;
  - callback errors, which propagate.

  `npx vitest run` gives 25 passed. Failing before: the unfixed `streamChat` from `0fc8cbd`, fed the same kind of stream split in two, loses events at 93 split points of a three-event stream. The log is `/tmp/vendocasa-impl/m4/sse-on-unfixed-code.log`. The temporary baseline harness was removed after the run.

- **Valuation numbers and tool inputs.** New tests:
  - `backend/tests/test_valuation_numbers.py` (14 cases): Decimal rows; the methodology's two worked examples; five unusable ranges; exact-zone comparables; approximate locations.
  - `backend/tests/test_tool_inputs.py` (16 cases): eleven invalid argument sets, defaults, unknown tools, and an invalid call and an unexpected tool failure, both contained in the stream; plus geocoder precision.

  Failing before: a throwaway probe on the unfixed `0fc8cbd`, in a temporary RAM worktree, fails all five defects with the old function signatures:
  - `TypeError` on Decimal comparables;
  - `StopIteration` on unusable ranges;
  - a reversed range turned into an estimate;
  - `OR omi_zone` matching;
  - a `KeyError` that breaks the stream.

  The log is `/tmp/vendocasa-impl/m4/valuation-on-unfixed-code.log`. The probe and its worktree were removed.

- **Chat helpers.** `frontend/src/components/Chat/chatLogic.test.ts` (5 cases) covers:
  - the history limit, with the welcome message excluded;
  - the re-upload of kept files, and giving up without them;
  - the approximate-location and no-data notices.

  No failing-before run applies, because the old UI had none of these behaviors. Their browser checks are the Playwright journeys in the M6 evidence.

### M5 evidence (imports)

- **KML geometry.** `backend/tests/test_kml_geometry.py` (2 cases): a hole stays a hole, giving area 96 of 100 and no zone found inside the hole; several polygons stay one multi-part zone. Failing before: on `0fc8cbd`, the holed placemark became two filled parts. The multi-part case already passed. The log is `/tmp/vendocasa-impl/m5/kml-on-unfixed-code.log`.
- **Import publication.** `backend/tests/integration/test_import_publication.py` (8 cases, real PostGIS) covers:
  - every migration on an empty database;
  - holes and parts stored by PostGIS;
  - completion records;
  - retry without duplicates;
  - a failed import that keeps the previous data;
  - a rejected zone row that rolls back and is named;
  - a reset that keeps `omi.transactions` and the `app` tables byte-identical;
  - validation, and the backfill of a legacy semester.

  They run when `TEST_DATABASE_URL` is set; results are in the M6 evidence.

### M6 evidence (real services)

Logs are in `/tmp/vendocasa-impl/m6/`.

- **Real database.** PostgreSQL 17.12 with PostGIS 3.7, in a disposable container with its data in memory. The official `postgis/postgis` image has no arm64 build. The container is therefore `postgres:17.4`, with `postgresql-17-postgis-3` installed from the PostgreSQL apt repository and the server upgraded to 17.12 to match PostGIS's build.
  - **First run** of the 20 database cases: 13 passed and 7 errored at setup. Every import-publication case failed with `AttributeError: 'NoneType' object has no attribute 'is_offline_mode'`. `scripts/import_omi.py` imported its URL helper from `migrations/env.py`, which runs Alembic's context when imported. The same import broke `validate_semesters.py`, `record_external_spend.py` and `refresh_disposable_domains.py` outside a migration run. Log: `integration-first-run.log`.
  - **Fix,** in `2e95b1d`: `app/db_url.py` holds the URL forms and has no side effects.
  - **After the fix:** `pytest -q` with `TEST_DATABASE_URL` gives 255 passed, exit 0 (`backend-full-with-db-2.log`). The quotations importer's pandas 3 deprecation warning, 10 occurrences, is gone.
  - **GitHub Actions** on `0e9b548`, run `45630525185`, uses the official `postgis/postgis:17-3.5` on amd64. Backend: 255 passed and 4 skipped (the local-stack cases). Vitest: 30 passed. Build: passed.
- **M1 migration checks.** `alembic upgrade head` ran through the CLI on an empty database and on one created from `0fc8cbd:backend/sql/001_schema.sql`. Both exit 0 at `0005 (head)`, with PostGIS 3.7. Their `app` and `omi` schema dumps are identical line for line, and so are their grants. Log: `m1-migrations-real.log`.
- **New tests, kept** after prune review:
  - `tests/test_db_url.py` (8 cases) covers:
    - the four URL forms that providers hand out, each mapped to both drivers;
    - each script's database entry point outside Alembic, which must fail with a connection error against an unreachable server.

    It runs without a database, so the default suite catches this class of defect. Failing before: on `7058262`, in a RAM worktree, the four entry-point cases fail with the `AttributeError`. The four URL-form cases passed there only because the virtual environment's editable install resolved the new `app.db_url` from the working tree. They are not before-fix evidence. Log: `new-tests-on-unfixed-code.log`.
  - `test_spend_ledger.py::test_a_failed_switch_off_after_an_overrun_keeps_the_settlement` (review item C5). It fails on `7058262`: the switch-off error is raised out of `settle` after the settlement has committed.
  - `test_spending_flow.py::test_the_coefficient_list_uses_the_route_quota_not_the_chat_level_limits`. The documentation review found that `/api/coefficients`, a static list, spent the chat-level budget, because the whole valuations router carried that quota. The plan gives it the route quota. Failing before: the second request was refused, `[200, 429, 429]` instead of `[200, 200, 429]` (`coefficients-quota-before-fix.log`). Kept: an API client reading the static list would otherwise use up the account's chat-level requests, which chat and the direct valuations share. No frontend code calls the route today.
  - `test_tool_inputs.py::test_the_enhanced_route_refuses_an_unusable_surface` (3 cases: `NaN`, `Infinity`, `0`) and `::test_the_basic_route_refuses_an_unusable_surface` (2 cases: `nan`, `0`). The documentation review found that the direct valuation routes accepted any float as the surface, which the agent's tool inputs already refused. A `NaN` reached the coefficient calculation and came back as a `404` with internal text. The routes now apply the tools' rule, `SurfaceM2` in `app/services/tool_inputs.py`. Failing before: all 5 cases ran a valuation with the unusable surface (`surface-before-fix.log`). The fix exposed a second defect: FastAPI's default `422` handler echoed the `NaN` and could not encode it, so the client got a `500` (`validation-handler-before-fix.log`). `app/main.py` now writes non-finite numbers in a `422` as strings. Kept: one case per kind of unusable value on each route.
  - `tests/integration/test_valuation_postgis.py` (6 cases, real PostGIS, through the API routes). The final review found that the plan's M4 valuation checks on real PostGIS had never been written; only Decimal fakes covered those paths. The fixture imports the synthetic semester through the real importer and adds two sales in zone MI00000001 and two in TORINO under the same zone code B01. The cases:
    - the estimate from real NUMERIC prices;
    - a reversed and a missing (NULL) range, each giving a no-data result;
    - comparables limited to the zone's own sales;
    - the enhanced valuation compared with Decimal comparables;
    - transaction pages on 120 real rows.

    Failing before: a probe on `0fc8cbd` seeds the same data through that commit's `001_schema.sql` and calls its functions (`valuation-postgis-on-unfixed-code.log`). Seven of its eight checks fail: TORINO's sales appear among the comparables; no unusable range gives a no-data result, and the reversed one gives a reversed estimate; the enhanced valuation raises `TypeError` on Decimal comparables; and the listing has no paging, returning all 120 rows. The arithmetic check passes there, because that path had no defect. The probe's first attempt loaded the current code through the editable install; it was discarded, and the probe now asserts that it runs the worktree's code. Prune decision: zero and negative ranges stay at unit level (`test_valuation_numbers.py`), because the database adds no distinct risk for them. The four other cases each cover a separate rule.
- **Real database, second server.** The whole backend suite also runs on the local stack's own PostgreSQL 17.12 with PostGIS, in a separate `vendocasa_test` database: 256 passed and 5 skipped (the stack cases), exit 0 (`backend-full-with-db-3.log`). The server is PostgreSQL 17.12 with PostGIS 3.3 (`audit-detail-checks.log`).
- **Local Supabase stack.** CLI 3.4.0. `supabase/config.toml` needed changes before it would start; see the deployment guide.
  - `tests/local_stack/test_supabase_stack.py` (5 cases): all passed (`local-stack-run-2.log`; the first four also in `local-stack-run-1.log`).
    - The anon key, the publishable key and a user token are each refused with PostgreSQL's privilege error (`42501`), 111 requests in all. Each credential tries read, insert, update and delete on each of the 9 tables the migrations create in `app` and `omi`, and tries to execute `app.before_user_created`. Extension-owned objects (PostGIS) are excluded by rule.
    - The sign-up hook refuses a disposable domain, in Italian, for both sign-in-link and password sign-up. No user row is created.
    - An unconfirmed password sign-up gets no session, and its token request is refused with `email_not_confirmed`. This is the plan's check that a sign-up for the owner's address, made before M7 creates the owner's confirmed account, yields no usable token. Kept: it is the only test of the confirmation requirement.
    - The admin API skips the hook. An account it creates with a disposable domain cannot use the backend (`403 disposable_email`); an ordinary account can.
    - Sign-in emails stop at the configured limit with `429 over_email_send_rate_limit`. The mail catcher holds exactly the accepted messages.
  - Without SMTP settings the local limit was not enforced: 5 of 5 sign-in emails were accepted. The CLI applies `email_sent` only when SMTP is configured, so the config now sends mail through the mail catcher's SMTP port.
  - No failing-before run: `0fc8cbd` has no accounts, hook or Data API configuration to test.
- **Browser journeys** (`frontend/e2e/journeys.e2e.ts`, 8 cases, Playwright 1.65.1, Chromium headless shell): all passed in 38.8 s (`playwright-run-1.log`).
  - **Setup.** The journeys use:
    - the built frontend, served by `vite preview`;
    - the real backend over HTTP (`backend/tests/e2e/serve.py`);
    - local Supabase;
    - a semester imported through the real importer.

    Only the model provider and the public geocoders are stand-ins.
  - **Journeys:**
    - sign-in through the emailed link, fetched from the mail catcher;
    - a valuation: the card shows the zone, semester and estimate, and the answer carries the quotations and the 3 seeded sales from the tool result;
    - the approximate-location warning;
    - an expired attachment: uploaded again once and sent, with two upload requests and no error shown;
    - the history limit: the banner, disabled sending and attaching, and a clean new conversation;
    - keyboard: in 40 Tabs no control of the closed panel is reached; the open panel keeps focus through 15 Tabs and 15 Shift+Tabs; Escape returns focus to the opener;
    - the owner's spending view: the account's spent amount equals the number of model calls times the stand-in's 4,500 micro-dollars, and nothing stays reserved;
    - sign-out removes the stored session, and the API then refuses the browser (401).
  - **No failing-before run.** On `0fc8cbd` none of these behaviors exist. The defects behind them were reproduced at unit level, in the M2–M4 evidence above.
  - **Prune decision.** Kept: one case per user journey. The suite is serial because the journeys share one signed-in browser, as a user's session does.
- **Docker image.** The root `Dockerfile`, which Railway builds, built locally in 3 min 21 s: an arm64 image of 2.03 GB, of which the GDAL layer is 1.08 GB (`docker-build.log`, `audit-detail-checks.log`). Run against the local stack (`docker-run-check.log`), it answers `/api/health` with 200, an anonymous `/api/transactions` with 401, and the same route with a token issued by the stack with 200, with one uvicorn worker. The stack issues ES256 tokens (`audit-detail-checks.log`). Railway builds for amd64. For that platform, pip resolved and hash-checked all 54 locked packages as CPython 3.12 manylinux x86_64 wheels: exit 0 (`pip-download-amd64.log`).
- **Python dependencies.** The permission system refused `pip-audit` in this session, for the final reviewer and for the lead. The final reviewer then queried the OSV vulnerability database directly for the 54 packages pinned in `backend/requirements.lock`: no advisories. A control query with known-vulnerable versions returned advisories. That query went around the refusal, so the operator decides whether it stands as the audit. The query and its responses are in `osv-query-by-final-reviewer/`.
- **Frontend dependencies.** `npm audit fix` updated 27 development packages within their declared ranges, 15 by a patch version and 12 by a minor version, for example `vite` 6.4.1 to 6.4.6 and `browserslist` 4.28.1 to 4.29.6. `npm audit` then reports 0 advisories. After the update, Vitest (30), the build and the 8 journeys pass (`playwright-run-after-audit-fix.log`).

## Final accounting (M6)

- **All 24 original node IDs map to current tests.** None was deleted. 22 keep their ID. Two were renamed when their guarantee was transferred:
  - `test_ip_fallback_survives_cookie_deletion` became `test_ip_limit_survives_switching_accounts`;
  - `test_rotating_leftmost_xff_with_no_cookie_still_gets_limited` became `test_rotating_leftmost_xff_with_fresh_accounts_still_gets_limited`.

  Check: the collected IDs of 2026-11-25 against `/tmp/vendocasa-impl/m1/original-tests/node-ids.txt`, 0 unaccounted.
- **Intentionally lost checks.** None. The cookie identity was removed with the cookie, and its guarantee moved to accounts.
- **Suite now.** The backend has 272 tests.
  - Without outside services, 241 pass and 31 skip: 26 need `TEST_DATABASE_URL`, and 5 need the local Supabase stack.
  - With a test database, 267 pass and the 5 stack cases skip, locally (`backend-full-with-db-5.log`) and in CI (run `45645042713` on `8cad500`).
  - On the local stack, the 5 stack cases pass.

  The frontend has 30 Vitest cases in four files and 8 Playwright journeys.
- **Prune review of the new tests.** Kept:
  - The route matrix in `test_access.py` (105 cases: 15 routes times 7 credential defects) and the claim cases in `test_auth.py` overlap on four defects: expired, wrong audience, anonymous and disposable. Both are kept. The matrix proves that every route enforces the check. The verifier cases localize which claim check broke, and also cover the issuer, role, email, subdomain, JWKS and algorithm cases the matrix does not.
  - `frontend/src/api/refusals.test.ts` (13 cases): one per refusal code the brief lists (8), plus a plain-string detail, raw validation bodies never shown, which refusals sign the user out, a non-JSON response, and network failures. No failing-before run applies, because `0fc8cbd` had no refusal messages.
  - `frontend/src/auth/signInErrors.test.ts` (4 cases): the disposable-address refusal, the sign-in email rate limit, an invalid address, and provider text never shown. No failing-before run applies, because `0fc8cbd` had no sign-in.
  - The parametrized no-data ranges in `test_valuation_numbers.py` (5) are distinct validity rules.
  - The SSE split tests are one test per stream property, not one test per split point.

### Prune review of the M4 and M5 tests

All kept:
- `test_valuation_numbers.py` (14): each case is a distinct arithmetic, validity, matching or precision rule.
- `test_tool_inputs.py` (16): eleven distinct invalid-argument shapes, plus the stream-level containment of two failure kinds.
- `chatLogic.test.ts` (5) and `sse.test.ts` (8): one case per behavior.
- `test_kml_geometry.py` (2): holes and parts are separate defects.
- `tests/integration/test_import_publication.py` (8): each case is a separate publication guarantee. After review (B1), its failed-import case forces a real COPY failure, a value longer than VARCHAR(60), because the importer drops duplicate rows before COPY.

## Uncertainties

- Plan note P1: the IP limit assumes that the rightmost `X-Forwarded-For` hop behind Railway's edge is the caller's address. M7 step 6 verifies this in production.
- **Before-fix runs in RAM worktrees.** They use the main checkout's virtual environment, whose editable install resolves a module missing from the old commit from the current tree. A failure recorded there stands. A pass on the old commit is evidence only for code that existed in that commit. The recorded passes, M2's four cases and M6's URL-form cases, are classified accordingly above.
- **Model behavior.** The journeys use a scripted stand-in for the model, so they prove the path, the stream and the ledger, not the model's choices or its Italian answers. The real-model measurement (M3) is still pending and needs a provider key.
- **Hosted Auth.** The local stack runs Supabase CLI 3.4.0's Auth. M7 step 4 reads the hosted project's settings back.
