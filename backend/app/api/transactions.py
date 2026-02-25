from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.transaction import TransactionCreate, TransactionUpdate

router = APIRouter()


@router.post("/api/transactions")
async def create_transaction(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a manually entered transaction record."""
    result = await db.execute(
        text("""
            INSERT INTO omi.transactions
                (transaction_date, transaction_type, declared_price, municipality,
                 omi_zone, link_zona, cadastral_category, cadastral_vani,
                 cadastral_mq, cadastral_mc, notes)
            VALUES
                (:transaction_date, :transaction_type, :declared_price, :municipality,
                 :omi_zone, :link_zona, :cadastral_category, :cadastral_vani,
                 :cadastral_mq, :cadastral_mc, :notes)
            RETURNING id, created_at
        """),
        data.model_dump(),
    )
    row = result.first()
    await db.commit()
    return {"id": row.id, "created_at": str(row.created_at), **data.model_dump()}


@router.get("/api/transactions")
async def list_transactions(
    link_zona: str | None = Query(None),
    municipality: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List transactions, optionally filtered by zone or municipality."""
    conditions = []
    params = {}

    if link_zona:
        conditions.append("link_zona = :link_zona")
        params["link_zona"] = link_zona
    if municipality:
        conditions.append("UPPER(municipality) = UPPER(:municipality)")
        params["municipality"] = municipality

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    result = await db.execute(
        text(f"""
            SELECT id, transaction_date, transaction_type, declared_price,
                   municipality, omi_zone, link_zona, cadastral_category,
                   cadastral_vani, cadastral_mq, cadastral_mc, notes, created_at
            FROM omi.transactions
            {where}
            ORDER BY transaction_date DESC NULLS LAST
        """),
        params,
    )
    return [dict(row._mapping) for row in result.all()]


@router.put("/api/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a transaction record."""
    # Build SET clause from non-None fields
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = transaction_id

    result = await db.execute(
        text(f"UPDATE omi.transactions SET {set_clause} WHERE id = :id RETURNING id"),
        updates,
    )
    if not result.first():
        raise HTTPException(404, "Transaction not found")
    await db.commit()
    return {"id": transaction_id, "updated": True}


@router.delete("/api/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a transaction record."""
    result = await db.execute(
        text("DELETE FROM omi.transactions WHERE id = :id RETURNING id"),
        {"id": transaction_id},
    )
    if not result.first():
        raise HTTPException(404, "Transaction not found")
    await db.commit()
    return {"id": transaction_id, "deleted": True}
