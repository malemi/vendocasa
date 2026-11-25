from fastapi import APIRouter, Depends

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.semesters import router as semesters_router
from app.api.transactions import router as transactions_router
from app.api.valuations import router as valuations_router
from app.api.zones import router as zones_router
from app.auth import current_account

# Every API route requires a verified account. AuthMiddleware refuses
# unauthenticated requests before the body is read; this dependency is the
# second, per-route guarantee. /api/health is defined outside this router.
api_router = APIRouter(dependencies=[Depends(current_account)])
api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(documents_router, tags=["Documents"])
api_router.include_router(valuations_router, tags=["Valuations"])
api_router.include_router(zones_router, tags=["Zones"])
api_router.include_router(semesters_router, tags=["Semesters"])
api_router.include_router(transactions_router, tags=["Transactions"])
