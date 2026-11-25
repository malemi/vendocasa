# Deployment Guide

## Production Architecture

```
Vercel (frontend) --> Railway (backend) --> Supabase (PostgreSQL + PostGIS)
        |                    |          --> Anthropic API (Claude Sonnet 5.5)
        +--> Supabase Auth <-+ (the backend verifies its access tokens)
```

The browser signs in with Supabase Auth email links and calls the backend directly (`VITE_API_URL`) with the session's access token.

## Supabase

### Database

- **PostGIS.** Enable it with `CREATE EXTENSION postgis;`.
- **Connection string.** Settings > Database > Connection String. Use the **Session Pooler**, not the direct connection, on IPv4-only networks. Prefix it with `postgresql+psycopg://` for SQLAlchemy.
- **Schema.** The schema is managed by Alembic (`backend/migrations/`). Apply migrations from `backend/` before deploying a build that needs them:

  ```bash
  DATABASE_URL="postgresql+psycopg://..." .venv/bin/alembic upgrade head
  ```

  Alembic's version table is `app.alembic_version`. The migrations are additive. Migration 0005 prints a validation line per loaded semester; see [the data pipeline](data-pipeline.md).
- **Schemas exposed to clients.** Application state (`app`) and OMI data (`omi`) are reachable only through the backend. The migrations revoke every privilege on both schemas, and on their objects, from `anon`, `authenticated` and `PUBLIC`. Keep both schemas out of the Data API's exposed schemas.

### Auth

These settings are configured on the project, through the dashboard or the management API:
- email provider only, with email confirmation required; anonymous, phone and OAuth sign-in disabled;
- site URL and redirect URLs: the Vercel frontend URL;
- custom SMTP. Without it, Supabase sends sign-in emails only to the project's team members, at a very low rate. The auth email rate limit is set explicitly;
- the before-user-created hook: `pg-functions://postgres/app/before_user_created`, created by migration 0003, which refuses disposable email domains. Configure it after the migration has run.

The backend refuses disposable-domain accounts on its own as well, so a missing hook never yields a usable account. Refresh the domain list with `python -m scripts.refresh_disposable_domains`.

## Railway (Backend)

`railway.toml` builds the root `Dockerfile`. It installs the hashed lock `backend/requirements.lock` and starts one uvicorn worker (`--workers 1`). The in-process upload store and request limits depend on a single worker. The spending ledger is in PostgreSQL and does not.

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | local | Supabase connection string (`postgresql+psycopg://...`) |
| `ANTHROPIC_API_KEY` | *(required)* | The backend refuses to start without it; it is logged only as present or absent |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | Model ID; must have prices in `backend/app/services/pricing.py`, or paid calls refuse |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | Any other value refuses startup, so the key cannot be redirected |
| `SUPABASE_URL` | *(required for access)* | Project URL, e.g. `https://<ref>.supabase.co`. Without it every protected route refuses with 503 |
| `SUPABASE_JWT_ALGORITHM` | `ES256` | The accepted token algorithm. `HS256` uses `SUPABASE_JWT_SECRET`; others use the project's JWKS |
| `SUPABASE_JWT_SECRET` | | The legacy shared secret, only for `HS256` |
| `OWNER_USER_ID` | | Token subject of the owner account |
| `ACCOUNT_MONTHLY_CAP_USD` | `1.0` | Spending cap per account per calendar month (UTC) |
| `GLOBAL_MONTHLY_CAP_USD` | `100.0` | Spending cap for all accounts together per calendar month |
| `CORS_ORIGINS` | `http://localhost:5173` | The Vercel frontend URL |
| `GOOGLE_GEOCODING_API_KEY` | | Optional; each Google request is charged to the requesting account |
| `ENABLE_API_DOCS` | `false` | Serves `/docs`, `/redoc` and `/openapi.json` when `true` |
| `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_PER_DAY` | `5` / `50` | Chat, upload and direct valuations, per account and per IP independently |
| `ROUTE_REQUESTS_PER_MINUTE` | `60` | Other routes, per account |
| `RATE_LIMIT_GLOBAL_DAILY_MODEL_CALLS` | `2000` | Service-wide model calls per day, a backstop to the dollar caps |
| `AGENT_MAX_TOOL_ROUNDS` | `3` | Model rounds per chat request |
| `AGENT_MAX_TOKENS` | `4096` | Output tokens per model call; adaptive thinking counts toward it |
| `AGENT_CALL_TIMEOUT_SECONDS` | `120` | Per model call; the SDK makes no automatic retries |
| `AGENT_MAX_HISTORY_MESSAGES` | `50` | Messages per chat request |
| `AGENT_MAX_MESSAGE_CHARS` | `4000` | Characters per message |
| `AGENT_MAX_ATTACHMENT_BYTES` | `15728640` | Attachment bytes per chat request |

Request counters and uploads live in process memory, and a restart resets them. Spending survives restarts. A sweep runs at startup and every five minutes, and settles at its full amount any reservation open for more than 15 minutes. A reservation left open by a crash is therefore settled between 15 and 20 minutes after it opened.

### Paid-call switch and owner routes

Paid calls start switched off; this is migration 0004. The owner turns them on with `PUT /api/admin/paid-calls` and reads the month's spending with `GET /api/admin/spending`; see [the API](api.md).

### Spending made outside the application

Real-provider runs made outside the application, such as a cost measurement, spend from the same provider account. Record each one in the ledger of the month it happened in, so the month's global total stays true:

```bash
cd backend && DATABASE_URL="postgresql+psycopg://..." .venv/bin/python -m scripts.record_external_spend --usd 0.42 --month 2026-11 --note "cost measurement"
```

The amount is charged to the scope `external` and to `global`, as an already-settled reservation.

### Health check

`GET /api/health` returns `{"status": "ok"}`, and Railway uses it (`railway.toml`).

## Vercel (Frontend)

`vercel.json` builds with `cd frontend && npm ci && npm run build` and serves `frontend/dist` as a single-page app.

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Railway backend URL; unset locally, where Vite proxies `/api` to `localhost:8000` |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | The project's public client key; it grants nothing in `app` or `omi` |

## Local Development

### Database

```bash
docker compose up -d db
```

On a plain PostgreSQL database, the Supabase client roles do not exist and must be created before migrating:

```bash
psql "$DATABASE_URL_PSQL" -f backend/sql/client_roles.sql
cd backend && .venv/bin/alembic upgrade head
```

### Local Supabase stack

The full local stack is the Supabase CLI's, configured by `supabase/config.toml`: PostgreSQL with PostGIS, Auth, PostgREST, the API gateway and a mail catcher for sign-in links. From the repository root:

```bash
npx supabase@3.4.0 start -x realtime,storage-api,imgproxy,postgres-meta,studio,edge-runtime,logflare,vector,supavisor
npx supabase@3.4.0 status -o env > ~/.config/vendocasa/local-status.env   # the stack's development keys; chmod 600
cd backend && DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres" .venv/bin/alembic upgrade head
```

- **Disk.** The images take about 2 GB.
- **Schemas.** The local Data API also exposes `app` and `omi`, which production does not, so the privilege checks see refusals from privileges. `supabase/seed.sql` creates the two empty schemas, so the Data API can start before the migrations.
- **Email.** Sign-in emails go through the mail catcher's SMTP port, so the email rate limit (3 an hour locally) applies, as it does with custom SMTP in production. The messages appear at `http://127.0.0.1:54324`. Restarting the auth container (`docker restart supabase_auth_vendocasa`) resets the count.
- **Exposed ports.** The CLI publishes the stack's ports on every network interface, and the database uses the CLI's default password. On a machine with a public address, block the ports from outside before starting. For IPv4: `sudo iptables -I DOCKER-USER -i <public interface> -p tcp -m conntrack --ctorigdstport 54320:54329 -j DROP`. For IPv6, where Docker's proxy listens: `sudo ip6tables -I INPUT -i <public interface> -p tcp -m multiport --dports 54320:54329 -j DROP`. Such a rule does not survive a reboot, while the stack's containers restart with Docker unless they were stopped. Stop the stack when it is not in use: `npx supabase@3.4.0 stop`.

### Backend

```bash
cd backend
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python --require-hashes -r requirements-dev.lock
cp .env.example .env   # DATABASE_URL, ANTHROPIC_API_KEY, SUPABASE_URL, ...
.venv/bin/uvicorn app.main:app --reload
```

Lock changes: edit `pyproject.toml`, then regenerate both locks with `uv pip compile pyproject.toml [--extra dev] --generate-hashes --python-version 3.12 --python-platform x86_64-manylinux_2_28 -o requirements[-dev].lock`.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

### Tests

- **Backend.** `cd backend && .venv/bin/python -m pytest -q`. Cases that need an outside service skip without it:
  - `tests/integration/` (the ledger, the imports and the valuations) runs when `TEST_DATABASE_URL` points at a disposable PostGIS database. It drops and recreates `app` and `omi` there, so never point it at a database in use.
  - `tests/local_stack/` runs when `SUPABASE_STATUS_ENV` names the status file above. It covers client-role privileges on every migrated object, the sign-up hook, an unconfirmed sign-up, an account created behind the hook, and the email rate. It starts its own backend on port 8001. Its email-rate case uses up the hour's allowance.
- **Frontend.** `cd frontend && npx vitest run && npm run build`.
- **Browser journeys.** Install the browser once with `cd frontend && npx playwright install --only-shell chromium`, then run `E2E_SUPABASE_STATUS_ENV=<status file> npx playwright test`. Playwright builds the frontend and serves it on `127.0.0.1:4173`. It starts `backend/tests/e2e/serve.py` on `127.0.0.1:8000`: the real backend on the local stack, seeded with a synthetic semester. Only the model provider and the public geocoders are replaced, by deterministic stand-ins. Run the journeys before the email-rate case, or restart the auth container first.

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs the backend tests with a PostGIS service (`postgis/postgis:17-3.5`, which has no arm64 build), Vitest and the build. It starts neither Supabase nor a browser.

## Estimated Costs

| Service | Plan | Cost |
|---------|------|------|
| Supabase | Free (500 MB) | $0/month |
| Railway | Hobby | ~$5/month |
| Vercel | Hobby | $0/month |
| Anthropic | Pay-as-you-go | At most `GLOBAL_MONTHLY_CAP_USD`, default $100/month |

The spending caps bound provider spend. Each account may spend at most $1 a month, and all accounts together at most $100. Every model call reserves its maximum cost before it starts, so the ledger cannot be overrun by concurrent requests. A spending limit on the Anthropic account itself is a separate safety net that the operator sets.
