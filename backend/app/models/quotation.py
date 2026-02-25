from sqlalchemy import Boolean, Column, Integer, Numeric, String, ForeignKeyConstraint
from app.models.zone import Base


class Quotation(Base):
    __tablename__ = "quotations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["link_zona", "semester"],
            ["omi.zones.link_zona", "omi.zones.semester"],
        ),
        {"schema": "omi"},
    )

    id = Column(Integer, primary_key=True)
    link_zona = Column(String(12), nullable=False, index=True)
    semester = Column(String(7), nullable=False)
    property_type_code = Column(Integer, index=True)
    property_type_desc = Column(String(60))
    conservation_state = Column(String(30))
    is_prevalent = Column(Boolean, default=False)
    price_min = Column(Numeric(10, 2))
    price_max = Column(Numeric(10, 2))
    surface_type_sale = Column(String(1))
    rent_min = Column(Numeric(10, 2))
    rent_max = Column(Numeric(10, 2))
    surface_type_rent = Column(String(1))
