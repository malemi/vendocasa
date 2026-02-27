from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.enhanced_valuation import EnhancedValuationRequest
from app.services.coefficients import get_coefficient_options
from app.services.valuation import enhanced_valuate_address, valuate_address

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


@router.post("/api/valuate/enhanced")
async def enhanced_valuate(
    request: EnhancedValuationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Enhanced valuation with correction coefficients.

    Applies property-specific adjustments (floor, renovation, exposure, noise, etc.)
    on top of OMI zone data to produce a more accurate estimate.
    """
    try:
        result = await enhanced_valuate_address(
            address=request.address,
            property_type=request.property_type,
            surface_m2=request.surface_m2,
            semester=request.semester,
            property_details=request.details.model_dump(),
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/coefficients")
async def list_coefficients():
    """Return all available correction coefficient factors and options.

    Used by the frontend wizard to dynamically build the property details form.
    """
    return {"factors": get_coefficient_options()}
