"""Document upload endpoint for chat attachments (PDF + images)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.auth import Account, current_account
from app.refusals import refusal
from app.services.document_store import (
    ALLOWED_MEDIA_TYPES,
    IMAGE_MEDIA_TYPES,
    MAX_FILE_SIZE,
    UploadStoreFull,
    store_document,
)
from app.services.rate_limit import get_client_ip, rate_limiter

logger = logging.getLogger(__name__)
router = APIRouter()


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    size: int
    media_type: str


@router.post("/api/documents/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile,
    request: Request,
    account: Account = Depends(current_account),
) -> UploadResponse:
    """Upload a PDF or image for use in chat. Returns a document ID.

    Constraints:
      - PDF (application/pdf) or images (JPEG, PNG, WEBP, GIF)
      - Max 5 MB
      - Stored in memory for 30 minutes

    Requires an account, and shares /api/chat's per-account and per-IP
    rate-limit budget. The document belongs to the uploading account: no
    other account can resolve or use it.
    """
    decision = rate_limiter.check_identity(account.id, get_client_ip(request))
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail=refusal("rate_limited"),
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    # Validate content type
    if file.content_type not in ALLOWED_MEDIA_TYPES:
        allowed = ", ".join(sorted(ALLOWED_MEDIA_TYPES))
        raise HTTPException(
            status_code=400,
            detail=f"Tipo file non supportato: {file.content_type}. Formati accettati: PDF, JPEG, PNG, WEBP, GIF.",
        )

    # Read at most MAX_FILE_SIZE + 1 bytes: enough to know the file is too large
    # without holding an oversized upload in memory.
    chunks: list[bytes] = []
    received = 0
    while received <= MAX_FILE_SIZE:
        chunk = await file.read(min(64 * 1024, MAX_FILE_SIZE + 1 - received))
        if not chunk:
            break
        chunks.append(chunk)
        received += len(chunk)
    if received > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=refusal("too_large"))
    data = b"".join(chunks)

    # Validate file content based on type
    if file.content_type == "application/pdf":
        if not data[:5] == b"%PDF-":
            raise HTTPException(
                status_code=400,
                detail="Il file non sembra essere un PDF valido.",
            )
    elif file.content_type in IMAGE_MEDIA_TYPES:
        # Basic image validation: check minimum size
        if len(data) < 100:
            raise HTTPException(
                status_code=400,
                detail="Il file immagine sembra vuoto o corrotto.",
            )

    try:
        doc = store_document(
            owner_id=account.id,
            filename=file.filename or "file",
            media_type=file.content_type,
            data=data,
        )
    except UploadStoreFull as full:
        status = 429 if full.code == "account_uploads_full" else 503
        raise HTTPException(status_code=status, detail=refusal(full.code)) from None
    logger.info(
        "Document uploaded: %s (%s, %d bytes) by account %s",
        doc.doc_id, doc.media_type, doc.size, account.id,
    )

    return UploadResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        size=doc.size,
        media_type=doc.media_type,
    )
