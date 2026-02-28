FROM python:3.12-slim

# Install GDAL for spatial operations
RUN apt-get update && apt-get install -y gdal-bin libgdal-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY app/ app/
COPY sql/ sql/

# Railway sets PORT dynamically; default to 8000 for local Docker
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
