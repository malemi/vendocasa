# The multi-platform index digest of python:3.12-slim: arm64 (the server) and
# amd64 (Railway) resolve the same index.
FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b

# Install GDAL for spatial operations
RUN apt-get update && apt-get install -y gdal-bin libgdal-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY backend/app/ app/
COPY backend/sql/ sql/
# Migrations, validation, imports and the Auth admin script run from this
# image as one-off containers (deploy/compose.yaml).
COPY backend/alembic.ini .
COPY backend/migrations/ migrations/
COPY backend/scripts/ scripts/
COPY backend/data/disposable_domains.txt data/disposable_domains.txt

# An unprivileged user; the files above stay owned by root and read-only to it.
RUN useradd --system --uid 10001 --no-create-home --home-dir /tmp vendocasa
USER 10001:10001
ENV HOME=/tmp PYTHONDONTWRITEBYTECODE=1

# Railway sets PORT dynamically; default to 8000 for local Docker
# One worker: the upload store and request limits live in process memory.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
