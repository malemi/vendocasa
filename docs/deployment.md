# Deployment Guide

## Railway Setup

### Services

The project runs as 3 services on Railway:

1. **PostGIS Database** -- deployed from the PostGIS template
2. **FastAPI Backend** -- Docker service from `backend/Dockerfile`
3. **React Frontend** -- static site build or Docker service

### PostGIS Database

Use the Railway PostGIS template (the default Railway Postgres does NOT include PostGIS):

https://railway.com/deploy/postgis

After deployment, Railway provides the `DATABASE_URL` environment variable automatically.

### Backend

Deployed as a Docker service:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y gdal-bin libgdal-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY app/ app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend

Options:
- **Railway static site** -- build Vite output and serve
- **Vercel** -- free tier, automatic deployments from git

## Environment Variables

Set these in the Railway dashboard:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | yes | PostgreSQL connection string (Railway provides this) |
| `GOOGLE_GEOCODING_API_KEY` | no | Google Maps Geocoding API key (fallback geocoder) |
| `CORS_ORIGINS` | yes | Comma-separated allowed origins for CORS |

## Local Development

### docker-compose.yml

```yaml
services:
  db:
    image: imresamu/postgis:16-3.5-alpine
    environment:
      POSTGRES_DB: vendocasa
      POSTGRES_USER: vendocasa
      POSTGRES_PASSWORD: vendocasa
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Note: uses `imresamu/postgis` instead of `postgis/postgis` for Apple Silicon (arm64) compatibility.

Start:
```bash
docker compose up -d db
```

### Backend Configuration

The backend reads configuration from `backend/.env`. Copy the example and edit:

```bash
cd backend
cp .env.example .env
# Edit .env with your settings
```

`.env` contents:
```
DATABASE_URL=postgresql+psycopg://vendocasa:vendocasa@localhost:5432/vendocasa
DATA_DIR=/path/to/your/omi/zip/files
GOOGLE_GEOCODING_API_KEY=
CORS_ORIGINS=http://localhost:5173
```

### Backend

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Initial Data Load

OMI zip files are stored outside the repo (configured via `DATA_DIR` in `backend/.env`).

```bash
cd backend
python -m scripts.import_omi
```

The script reads `DATA_DIR` and `DATABASE_URL` from `.env` automatically.

To override via CLI args:
```bash
python -m scripts.import_omi /path/to/data postgresql+psycopg://user:pass@host/db
```

To reset the database and re-import everything:
```bash
python -m scripts.import_omi --reset
```

On Railway, run as a one-off command:
```bash
railway run python -m scripts.import_omi
```

Full import (23 semesters) produces:
- ~620,000 zone polygons (with PostGIS geometries)
- ~3,750,000 quotation rows (EUR/m2 price ranges)

## Semiannual Data Refresh

1. Download new zip from Agenzia delle Entrate (SPID required)
2. Place in the data directory configured in `DATA_DIR`
3. Run: `cd backend && python -m scripts.import_omi`
4. The script detects the new semester and imports only new data (existing semesters are skipped via UNIQUE constraints)
5. Frontend picks up new semester via `/api/semesters`

## Estimated Costs

Railway hobby plan: ~$5/month
- PostGIS: ~$3/month (small instance)
- Backend: ~$2/month (small instance, low traffic)
- Frontend: free on Vercel, or included in Railway plan
