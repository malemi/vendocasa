from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.valuation import valuate_address

router = APIRouter()


@router.get("/api/valuate")
async def valuate(
    address: str = Query(..., description="Italian address to valuate"),
    property_type: int = Query(20, description="Property type code (20=Abitazioni civili)"),
    surface_m2: float | None = Query(None, description="Surface area in m2 for total estimate"),
    semester: str | None = Query(None, description="Semester, e.g. 2024_S2"),
    db: AsyncSession = Depends(get_db),
):
    """Main valuation endpoint. Geocodes an address and returns OMI zone + price data."""
    try:
        result = await valuate_address(address, property_type, surface_m2, semester, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
