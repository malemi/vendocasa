from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings

app = FastAPI(
    title="VendoCasa - Italian Real Estate Valuation",
    description="Personal tool for OMI-based property valuation across Italian cities",
    version="0.1.0",
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
