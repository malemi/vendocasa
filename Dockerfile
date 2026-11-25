FROM python:3.12-slim

# Install GDAL for spatial operations
RUN apt-get update && apt-get install -y gdal-bin libgdal-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY backend/app/ app/
COPY backend/sql/ sql/

# Railway sets PORT dynamically; default to 8000 for local Docker
# One worker: the upload store and request limits live in process memory.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
