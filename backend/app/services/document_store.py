"""
In-memory document store for uploaded files (PDF, images).

IMPORTANT: This store uses a module-level dict that does NOT survive process
restarts. On platforms with multiple workers or auto-scaling (e.g., Railway
with >1 worker), documents uploaded by one worker are invisible to others.
Currently safe because Railway runs a single worker, but this is a latent
limitation.

For production use, consider Redis-backed or filesystem-backed storage.
Documents expire after 30 minutes (STORE_TTL_SECONDS).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_FILES_PER_MESSAGE = 4
ALLOWED_MEDIA_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp", "image/gif"}
IMAGE_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
TTL_SECONDS = 30 * 60  # 30 minutes
MAX_BYTES_PER_ACCOUNT = 20 * 1024 * 1024
MAX_BYTES_TOTAL = 200 * 1024 * 1024


class UploadStoreFull(Exception):
    """Storing would exceed a byte cap. `code` is a refusal code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass
class StoredDocument:
    doc_id: str
    owner_id: str  # account that uploaded it; only that account can use it
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
# Uploads arrive from async handlers but the store is plain data; one lock keeps
# the byte caps exact under concurrent uploads.
_lock = threading.Lock()


def store_document(owner_id: str, filename: str, media_type: str, data: bytes) -> StoredDocument:
    """Store a document and return its metadata, or raise UploadStoreFull.

    Expired entries are removed first. The account's bytes and the total bytes
    are checked against MAX_BYTES_PER_ACCOUNT and MAX_BYTES_TOTAL before insertion.
    """
    with _lock:
        _cleanup_expired_locked()
        account_bytes = sum(d.size for d in _store.values() if d.owner_id == owner_id)
        total_bytes = sum(d.size for d in _store.values())
        if account_bytes + len(data) > MAX_BYTES_PER_ACCOUNT:
            raise UploadStoreFull("account_uploads_full")
        if total_bytes + len(data) > MAX_BYTES_TOTAL:
            raise UploadStoreFull("uploads_full")
        doc_id = str(uuid.uuid4())
        doc = StoredDocument(
            doc_id=doc_id,
            owner_id=owner_id,
            filename=filename,
            media_type=media_type,
            data=data,
            size=len(data),
        )
        _store[doc_id] = doc
        return doc


def get_document(doc_id: str, owner_id: str) -> StoredDocument | None:
    """Retrieve an account's own document by ID.

    Returns None when the document is missing, expired, or belongs to another
    account -- the three cases are indistinguishable to the caller.
    """
    with _lock:
        doc = _store.get(doc_id)
        if doc and doc.is_expired:
            del _store[doc_id]
            return None
        if doc is None or doc.owner_id != owner_id:
            return None
        return doc


def cleanup_expired() -> int:
    """Remove all expired documents; returns how many were removed."""
    with _lock:
        return _cleanup_expired_locked()


def _cleanup_expired_locked() -> int:
    expired = [k for k, v in _store.items() if v.is_expired]
    for k in expired:
        del _store[k]
    return len(expired)
