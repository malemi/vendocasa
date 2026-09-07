"""Document upload endpoint for chat attachments (PDF + images)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.services.document_store import (
    ALLOWED_MEDIA_TYPES,
    IMAGE_MEDIA_TYPES,
    MAX_FILE_SIZE,
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
async def upload_document(file: UploadFile, request: Request) -> UploadResponse:
    """Upload a PDF or image for use in chat. Returns a document ID.

    Constraints:
      - PDF (application/pdf) or images (JPEG, PNG, WEBP, GIF)
      - Max 5 MB
      - Stored in memory for 30 minutes

    Public and unauthenticated, same as /api/chat -- shares its per-identity
    rate-limit budget so it can't be used to exhaust document_store's memory
    (no total-size cap, only opportunistic TTL cleanup) outside that budget.
    """
    user_id = getattr(request.state, "user_id", "unknown")
    decision = rate_limiter.check_identity(user_id, get_client_ip(request))
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": "Too many requests. Please wait before trying again.",
            },
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    # Validate content type
    if file.content_type not in ALLOWED_MEDIA_TYPES:
        allowed = ", ".join(sorted(ALLOWED_MEDIA_TYPES))
        raise HTTPException(
            status_code=400,
            detail=f"Tipo file non supportato: {file.content_type}. Formati accettati: PDF, JPEG, PNG, WEBP, GIF.",
        )

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File troppo grande ({len(data)} bytes). Massimo {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

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

    doc = store_document(
        filename=file.filename or "file",
        media_type=file.content_type,
        data=data,
    )
    logger.info(
        "Document uploaded: %s (%s, %s, %d bytes)", doc.doc_id, doc.filename, doc.media_type, doc.size
    )

    return UploadResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        size=doc.size,
        media_type=doc.media_type,
    )
