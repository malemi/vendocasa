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
    image: postgis/postgis:16-3.4
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

Start:
```bash
docker compose up -d db
```

Connection string for local dev:
```
DATABASE_URL=postgresql+psycopg://vendocasa:vendocasa@localhost:5432/vendocasa
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

The OMI zip files are in `./data/` (not committed to git due to size).

```bash
# Import all semesters from all zips
python -m backend.scripts.import_omi ./data/ $DATABASE_URL
```

On Railway, run as a one-off command:
```bash
railway run python -m backend.scripts.import_omi ./data/ $DATABASE_URL
```

## Semiannual Data Refresh

1. Download new zip from Agenzia delle Entrate (SPID required)
2. Place in `./data/`
3. Run import script -- it skips existing semesters automatically
4. Frontend picks up new semester via `/api/semesters`

## Estimated Costs

Railway hobby plan: ~$5/month
- PostGIS: ~$3/month (small instance)
- Backend: ~$2/month (small instance, low traffic)
- Frontend: free on Vercel, or included in Railway plan
