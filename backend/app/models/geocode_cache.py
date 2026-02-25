from sqlalchemy import Column, Float, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.models.zone import Base


class GeocodeCache(Base):
    __tablename__ = "geocode_cache"
    __table_args__ = {"schema": "omi"}

    address = Column(Text, primary_key=True)
    lat = Column(Float)
    lng = Column(Float)
    source = Column(String(30))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
