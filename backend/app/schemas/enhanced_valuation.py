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


class CoefficientBreakdownItem(BaseModel):
    """One row of the coefficient breakdown table."""
    factor: str
    factor_label: str
    selected_key: str
    selected_label: str
    coefficient: float
    impact_eur_m2: float


class BenchmarkComparisonResponse(BaseModel):
    """Comparison of adjusted estimate vs real transaction data."""
    has_comparables: bool
    closest_eur_m2: float | None = None
    difference_pct: float | None = None
    confidence: str = "low"  # "high" | "medium" | "low"
    note: str = ""


class AdjustedEstimateResponse(BaseModel):
    """Full enhanced valuation result with coefficient adjustments."""
    base_price_min: float
    base_price_max: float
    base_conservation_state: str
    total_coefficient: float
    adjusted_price_min: float
    adjusted_price_max: float
    adjusted_mid: float
    total_min: float
    total_max: float
    total_mid: float
    surface_m2: float
    breakdown: list[CoefficientBreakdownItem]
    benchmark_comparison: BenchmarkComparisonResponse | None = None


class EnhancedValuationRequest(BaseModel):
    """Request body for the enhanced valuation endpoint."""
    address: str
    surface_m2: float
    property_type: int = 20
    semester: str | None = None
    details: PropertyDetails


class EnhancedValuationResponse(BaseModel):
    """Complete response from the enhanced valuation endpoint."""
    address: str
    coordinates: dict  # {"lat": float, "lng": float}
    zone: dict  # ZoneInfo-like dict
    semester: str
    quotations_by_state: dict[str, dict]  # conservation_state -> {price_min, price_max}
    adjusted_estimate: AdjustedEstimateResponse
    comparables: list[dict]


class CoefficientOptionsResponse(BaseModel):
    """All available coefficient factors and their options, for the frontend wizard."""
    factors: dict  # factor_name -> {label, label_en, options: [{key, label, pct}]}
