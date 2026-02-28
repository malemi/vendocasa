# Deployment Guide

## Production Architecture

```
Vercel (frontend)  -->  Railway (backend)  -->  Supabase (PostgreSQL + PostGIS)
                                           -->  Anthropic API (Claude Sonnet 4)
```

## Supabase (Database)

### Setup

1. Create a Supabase project at https://supabase.com
2. Enable PostGIS in the SQL editor:
   ```sql
   CREATE EXTENSION postgis;
   ```
3. Get the connection string from Settings > Database > Connection String
   - Use **Session Pooler** (not Direct connection) if your network is IPv4-only
   - URL format: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`

### Data Import

Import OMI data from your local machine against the Supabase URL. Only import the semesters you need (2 semesters fits the free tier):

```bash
cd backend
source venv/bin/activate

# URL-encode special characters in the password first:
# python3 -c "from urllib.parse import quote; print(quote('YOUR_PASSWORD', safe=''))"

DATABASE_URL="postgresql+psycopg://postgres.[ref]:ENCODED_PASS@aws-0-region.pooler.supabase.com:5432/postgres" \
  python -m scripts.import_omi /path/to/omi/zips/
```

Note: The `+psycopg` in the URL is required -- it tells SQLAlchemy to use the psycopg3 driver (not psycopg2).

The import script auto-detects semesters from the CSV filenames inside each zip. To limit to specific semesters, place only the desired zip files in the data directory.

### Free Tier Limits

- 500 MB database storage
- 2 semesters of OMI data (~160K quotation rows + ~16K zone geometries) fits comfortably
- Pro plan ($25/month, 8 GB) if more semesters needed

## Railway (Backend)

### Setup

1. Create a Railway project from the GitHub repo
2. Railway auto-detects `railway.toml` which points to `backend/Dockerfile`
3. Set environment variables in the Railway dashboard:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Supabase connection string (with `postgresql+psycopg://` prefix) |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `CORS_ORIGINS` | Your Vercel frontend URL (e.g. `https://vendocasa.vercel.app`) |
| `GOOGLE_GEOCODING_API_KEY` | Optional Google Maps fallback geocoder |

### Configuration

`railway.toml` (at repo root):
```toml
[build]
builder = "dockerfile"
dockerfilePath = "backend/Dockerfile"
dockerContext = "backend"

[deploy]
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

The Dockerfile uses `${PORT:-8000}` for Railway's dynamic port assignment.

### Health Check

```bash
curl https://your-app.up.railway.app/api/health
# {"status": "ok"}
```

## Vercel (Frontend)

### Setup

1. Create a Vercel project from the GitHub repo
2. Framework preset: **Other** (not React/Vite -- our `vercel.json` handles everything)
3. Root directory: leave as default (repo root)
4. Set environment variable:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | Railway backend URL (e.g. `https://vendocasa-production.up.railway.app`) |

### Configuration

`vercel.json` (at repo root):
```json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

### How VITE_API_URL Works

The frontend API client reads `VITE_API_URL` at build time:
```typescript
const API_BASE = import.meta.env.VITE_API_URL || "";
```

- **Local dev**: `VITE_API_URL` is not set, so API calls go to `/api` (proxied by Vite to localhost:8000)
- **Production**: `VITE_API_URL=https://railway-url` so API calls go directly to Railway

## Local Development

### Docker Compose (PostGIS)

```bash
docker compose up -d db
```

Uses `imresamu/postgis:16-3.5-alpine` for Apple Silicon (arm64) compatibility.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your DATABASE_URL
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `http://localhost:8000` (configured in `vite.config.ts`).

### Initial Data Load

```bash
cd backend
python -m scripts.import_omi /path/to/omi/zips
```

The script reads `DATABASE_URL` from `.env`. To override:
```bash
DATABASE_URL="postgresql+psycopg://user:pass@host/db" python -m scripts.import_omi /path/to/data
```

The script is idempotent: already-imported semesters are skipped via UNIQUE constraints.

## Semiannual Data Refresh

1. Download new zip from Agenzia delle Entrate (SPID required)
2. Run: `python -m scripts.import_omi /path/to/new/zip`
3. The script detects the new semester and imports only new data
4. Frontend picks up the new semester via `/api/semesters`

## Estimated Costs

| Service | Plan | Cost |
|---------|------|------|
| Supabase | Free (500 MB, 2 semesters) | $0/month |
| Railway | Hobby | ~$5/month |
| Vercel | Hobby | $0/month |
| Anthropic | Pay-as-you-go | ~$0.01-0.05 per chat conversation |
| **Total** | | **~$5/month** |
