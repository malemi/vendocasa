"""Pydantic schemas for the enhanced valuation endpoint with correction coefficients."""

from pydantic import BaseModel


class PropertyDetails(BaseModel):
    """User-provided property characteristics for coefficient adjustment."""
    conservation_state: str = "NORMALE"  # "OTTIMO" | "NORMALE" | "SCADENTE"
    renovation: str = "none"
    floor: str = "second"
    exposure: str = "east_west"
    noise: str = "normal"
    common_areas: str = "good"
    building_facade: str = "good_condition"
    energy_class: str = "E"
    elevator: str = "yes"


class EnhancedValuationRequest(BaseModel):
    """Request body for the enhanced valuation endpoint."""
    address: str
    surface_m2: float
    property_type: int = 20
    semester: str | None = None
    details: PropertyDetails
