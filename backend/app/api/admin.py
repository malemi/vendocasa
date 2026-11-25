"""Owner-only operations: the month's spending, and the paid-call switch."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import Account, require_owner
from app.services import spending

router = APIRouter()


class PaidCallsSwitch(BaseModel):
    enabled: bool


@router.get("/api/admin/spending")
async def month_spending(_owner: Account = Depends(require_owner)) -> dict:
    """This month's global spending, each account's spending, the caps and the switch."""
    return await spending.month_report()


@router.put("/api/admin/paid-calls")
async def set_paid_calls(switch: PaidCallsSwitch, _owner: Account = Depends(require_owner)) -> dict:
    """Turn paid provider calls on or off; the rest of the site keeps working."""
    await spending.set_paid_calls(switch.enabled)
    return {"paid_calls_enabled": switch.enabled}
