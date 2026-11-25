import asyncio
import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.auth import AuthMiddleware
from app.config import DEFAULT_ANTHROPIC_BASE_URL, settings
from app.middleware import BodyLimitMiddleware
from app.services import document_store, spending

logger = logging.getLogger(__name__)

# Fail loudly at startup rather than per-request: a missing key means the
# chat agent would otherwise return a 503 on every single /api/chat call
# instead of the deployment failing once, clearly, before it takes traffic.
if not settings.anthropic_api_key:
    raise RuntimeError(
        "ANTHROPIC_API_KEY is not set. Refusing to start -- the chat agent "
        "cannot function without it."
    )

logger.info(
    "Anthropic configured: model=%s api_key_present=%s base_url=%s",
    settings.anthropic_model,
    bool(settings.anthropic_api_key),
    settings.anthropic_base_url,
)
# The API key may only ever be sent to the Anthropic API host. A different
# configured base URL is a misconfiguration (or an attempt to redirect the
# key), so the process refuses to start rather than merely logging it.
if settings.anthropic_base_url != DEFAULT_ANTHROPIC_BASE_URL:
    raise RuntimeError(
        "ANTHROPIC_BASE_URL must be "
        f"{DEFAULT_ANTHROPIC_BASE_URL}; refusing to start with a different provider host."
    )

# /docs, /redoc, and /openapi.json publish exactly which routes exist --
# including which ones spend money on the paid Anthropic model -- to
# anyone who requests them. Disabled unless ENABLE_API_DOCS is set.
_docs_kwargs = (
    {}
    if settings.enable_api_docs
    else {"docs_url": None, "redoc_url": None, "openapi_url": None}
)

SPEND_SWEEP_SECONDS = 300
UPLOAD_SWEEP_SECONDS = 60


async def _every(seconds: float, name: str, job) -> None:
    """Run `job` now and then every `seconds`, logging (never raising) failures."""
    while True:
        try:
            await job()
        except Exception as exc:
            logger.warning("%s failed: %s", name, type(exc).__name__)
        await asyncio.sleep(seconds)


async def _sweep_uploads() -> None:
    document_store.cleanup_expired()


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    # Stale spending reservations (a crash mid-call) are settled in full, and
    # expired uploads are deleted, at startup and periodically.
    tasks = [
        asyncio.create_task(_every(SPEND_SWEEP_SECONDS, "Spending sweep", spending.sweep_stale)),
        asyncio.create_task(_every(UPLOAD_SWEEP_SECONDS, "Upload sweep", _sweep_uploads)),
    ]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(
    lifespan=lifespan,
    title="VendoCasa - Italian Real Estate Valuation",
    description="OMI-based property valuation for registered users",
    version="0.1.0",
    **_docs_kwargs,
)

# Middleware order: the last one added is the outermost. CORS stays outside
# everything so preflight requests are answered and refusals carry CORS
# headers the browser can read; body limits apply before authentication.
app.add_middleware(AuthMiddleware)
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


app.include_router(api_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
