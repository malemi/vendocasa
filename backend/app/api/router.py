from fastapi import APIRouter

from app.api.valuations import router as valuations_router
from app.api.zones import router as zones_router
from app.api.semesters import router as semesters_router
from app.api.transactions import router as transactions_router

api_router = APIRouter()
api_router.include_router(valuations_router, tags=["Valuations"])
api_router.include_router(zones_router, tags=["Zones"])
api_router.include_router(semesters_router, tags=["Semesters"])
api_router.include_router(transactions_router, tags=["Transactions"])
