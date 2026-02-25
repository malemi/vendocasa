from sqlalchemy import Column, Date, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.models.zone import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = {"schema": "omi"}

    id = Column(Integer, primary_key=True)
    transaction_date = Column(Date)
    transaction_type = Column(String(30))
    declared_price = Column(Numeric(12, 2))
    municipality = Column(Text)
    omi_zone = Column(String(10))
    link_zona = Column(String(12))
    cadastral_category = Column(String(10))
    cadastral_vani = Column(Numeric(6, 1))
    cadastral_mq = Column(Numeric(8, 1))
    cadastral_mc = Column(Numeric(8, 1))
    notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
