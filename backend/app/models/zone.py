from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Zone(Base):
    __tablename__ = "zones"
    __table_args__ = (
        UniqueConstraint("link_zona", "semester"),
        {"schema": "omi"},
    )

    id = Column(Integer, primary_key=True)
    link_zona = Column(String(12), nullable=False, index=True)
    zone_code = Column(String(10), nullable=False)
    fascia = Column(String(5))
    municipality_istat = Column(String(10), nullable=False)
    municipality_name = Column(Text)
    province_code = Column(String(3))
    zone_description = Column(Text)
    semester = Column(String(7), nullable=False, index=True)
    geom = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
