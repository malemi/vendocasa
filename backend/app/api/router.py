from fastapi import APIRouter, Depends

from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.quotas import route_quota
from app.api.semesters import router as semesters_router
from app.api.transactions import router as transactions_router
from app.api.valuations import router as valuations_router
from app.api.zones import router as zones_router
from app.auth import current_account

# Every API route requires a verified account. AuthMiddleware refuses
# unauthenticated requests before the body is read; this dependency is the
# second, per-route guarantee. /api/health is defined outside this router.
#
# Chat and upload apply the per-account and per-IP limits themselves. The
# direct valuation routes reach the public geocoders, so they get the same
# limits (set on those routes in valuations.py); every other route gets the
# lighter per-account route quota.
api_router = APIRouter(dependencies=[Depends(current_account)])
api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(documents_router, tags=["Documents"])
api_router.include_router(valuations_router, tags=["Valuations"])
api_router.include_router(zones_router, tags=["Zones"], dependencies=[Depends(route_quota)])
api_router.include_router(semesters_router, tags=["Semesters"], dependencies=[Depends(route_quota)])
api_router.include_router(transactions_router, tags=["Transactions"], dependencies=[Depends(route_quota)])
api_router.include_router(admin_router, tags=["Admin"], dependencies=[Depends(route_quota)])
