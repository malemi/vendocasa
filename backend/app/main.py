import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import DEFAULT_ANTHROPIC_BASE_URL, settings

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
if settings.anthropic_base_url != DEFAULT_ANTHROPIC_BASE_URL:
    logger.warning(
        "ANTHROPIC_BASE_URL is overridden to %s -- every Anthropic request, "
        "including the API key, is being sent there instead of the default "
        "Anthropic host.",
        settings.anthropic_base_url,
    )

# /docs, /redoc, and /openapi.json publish exactly which routes exist --
# including which ones spend money on the paid Anthropic model -- to
# anyone who requests them. Disabled unless ENABLE_API_DOCS is set.
_docs_kwargs = (
    {}
    if settings.enable_api_docs
    else {"docs_url": None, "redoc_url": None, "openapi_url": None}
)

app = FastAPI(
    title="VendoCasa - Italian Real Estate Valuation",
    description="Personal tool for OMI-based property valuation across Italian cities",
    version="0.1.0",
    **_docs_kwargs,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def user_tracking(request: Request, call_next):
    """Set/read a vendocasa_uid cookie to identify users for abuse prevention."""
    user_id = request.cookies.get("vendocasa_uid")
    if not user_id:
        user_id = str(uuid4())
    request.state.user_id = user_id
    response = await call_next(request)
    response.set_cookie(
        "vendocasa_uid",
        user_id,
        max_age=365 * 24 * 3600,
        httponly=False,
        secure=True,
        samesite="none",
    )
    return response


app.include_router(api_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
