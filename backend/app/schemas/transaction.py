from datetime import date

from pydantic import BaseModel


class TransactionCreate(BaseModel):
    transaction_date: date | None = None
    transaction_type: str | None = None
    declared_price: float | None = None
    municipality: str | None = None
    omi_zone: str | None = None
    link_zona: str | None = None
    cadastral_category: str | None = None
    cadastral_vani: float | None = None
    cadastral_mq: float | None = None
    cadastral_mc: float | None = None
    notes: str | None = None


class TransactionUpdate(BaseModel):
    transaction_date: date | None = None
    transaction_type: str | None = None
    declared_price: float | None = None
    municipality: str | None = None
    omi_zone: str | None = None
    link_zona: str | None = None
    cadastral_category: str | None = None
    cadastral_vani: float | None = None
    cadastral_mq: float | None = None
    cadastral_mc: float | None = None
    notes: str | None = None



