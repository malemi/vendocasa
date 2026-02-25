from pydantic import BaseModel


class Coordinates(BaseModel):
    lat: float
    lng: float


class ZoneInfo(BaseModel):
    link_zona: str
    zone_code: str
    fascia: str | None
    municipality: str | None
    description: str | None
    distance_m: float | None = None


class QuotationItem(BaseModel):
    property_type_desc: str | None
    conservation_state: str | None
    is_prevalent: bool
    price_min: float | None
    price_max: float | None
    surface_type_sale: str | None
    rent_min: float | None
    rent_max: float | None
    surface_type_rent: str | None


class Estimate(BaseModel):
    min: float
    max: float
    mid: float
    eur_per_m2_range: list[float]


class ComparableItem(BaseModel):
    transaction_date: str | None
    declared_price: float | None
    cadastral_category: str | None
    cadastral_vani: float | None
    cadastral_mq: float | None
    notes: str | None


class ValuationResponse(BaseModel):
    address: str
    coordinates: Coordinates
    zone: ZoneInfo
    semester: str
    quotations: list[QuotationItem]
    estimate: Estimate | None
    comparables: list[ComparableItem]


class SemesterListResponse(BaseModel):
    semesters: list[str]
    latest: str | None
