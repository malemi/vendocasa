from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.zone_lookup import get_all_semesters

router = APIRouter()


@router.get("/api/semesters")
async def list_semesters(db: AsyncSession = Depends(get_db)):
    """List all available data semesters."""
    semesters = await get_all_semesters(db)
    return {
        "semesters": semesters,
        "latest": semesters[0] if semesters else None,
    }
