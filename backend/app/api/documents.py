"""Document upload endpoint for chat PDF attachments."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.document_store import (
    ALLOWED_MEDIA_TYPES,
    MAX_FILE_SIZE,
    store_document,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    size: int
    media_type: str


@router.post("/api/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile) -> UploadResponse:
    """Upload a PDF document for use in chat. Returns a document ID.

    Constraints:
      - PDF only (application/pdf)
      - Max 5 MB
      - Stored in memory for 30 minutes
    """
    # Validate content type
    if file.content_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo file non supportato: {file.content_type}. Solo PDF.",
        )

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File troppo grande ({len(data)} bytes). Massimo {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    # Additional PDF magic bytes check
    if not data[:5] == b"%PDF-":
        raise HTTPException(
            status_code=400,
            detail="Il file non sembra essere un PDF valido.",
        )

    doc = store_document(
        filename=file.filename or "document.pdf",
        media_type=file.content_type,
        data=data,
    )
    logger.info(
        "Document uploaded: %s (%s, %d bytes)", doc.doc_id, doc.filename, doc.size
    )

    return UploadResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        size=doc.size,
        media_type=doc.media_type,
    )
