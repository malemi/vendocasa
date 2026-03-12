"""In-memory temporary document storage with TTL expiration.

Uploaded PDFs are stored here briefly so the chat endpoint can resolve
document_ids into Claude API content blocks. Documents expire after
TTL_SECONDS and are cleaned up on the next store call.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_FILES_PER_MESSAGE = 4
ALLOWED_MEDIA_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp", "image/gif"}
IMAGE_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
TTL_SECONDS = 30 * 60  # 30 minutes


@dataclass
class StoredDocument:
    doc_id: str
    filename: str
    media_type: str
    data: bytes  # raw PDF or image bytes
    size: int
    created_at: float = field(default_factory=time.time)

    @property
    def is_image(self) -> bool:
        return self.media_type in IMAGE_MEDIA_TYPES

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > TTL_SECONDS


# Module-level store: {doc_id: StoredDocument}
_store: dict[str, StoredDocument] = {}


def store_document(filename: str, media_type: str, data: bytes) -> StoredDocument:
    """Store a document and return its metadata. Cleans expired entries first."""
    _cleanup_expired()
    doc_id = str(uuid.uuid4())
    doc = StoredDocument(
        doc_id=doc_id,
        filename=filename,
        media_type=media_type,
        data=data,
        size=len(data),
    )
    _store[doc_id] = doc
    return doc


def get_document(doc_id: str) -> StoredDocument | None:
    """Retrieve a document by ID. Returns None if expired or not found."""
    doc = _store.get(doc_id)
    if doc and doc.is_expired:
        del _store[doc_id]
        return None
    return doc


def _cleanup_expired() -> None:
    """Remove all expired documents."""
    expired = [k for k, v in _store.items() if v.is_expired]
    for k in expired:
        del _store[k]
