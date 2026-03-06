"""Chat API endpoint — streams AI agent responses via Server-Sent Events."""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.agent import run_agent_stream
from app.services.document_store import MAX_FILES_PER_MESSAGE, get_document

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    document_ids: list[str] | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@router.post("/api/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Stream a chat response from the AI valuation agent.

    Accepts the full conversation history and returns an SSE stream.
    The agent has access to all valuation tools and executes them server-side.
    User messages may include document_ids referencing previously uploaded PDFs.

    SSE event types:
      text_delta  - streamed text tokens
      tool_result - structured valuation data for inline cards
      map_update  - coordinates for map flyTo
      done        - stream complete
      error       - error occurred
    """
    user_id = getattr(request.state, "user_id", "unknown")
    logger.info("Chat request from user_id=%s (%d messages)", user_id, len(body.messages))

    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI agent not configured. Set ANTHROPIC_API_KEY in .env",
        )

    # Build Claude API messages, resolving document_ids to content blocks
    api_messages: list[dict] = []
    for m in body.messages:
        if m.document_ids and m.role == "user":
            if len(m.document_ids) > MAX_FILES_PER_MESSAGE:
                raise HTTPException(
                    400,
                    f"Massimo {MAX_FILES_PER_MESSAGE} documenti per messaggio.",
                )

            # Multi-block content: documents first, then text
            content_blocks: list[dict] = []
            for doc_id in m.document_ids:
                doc = get_document(doc_id)
                if doc is None:
                    raise HTTPException(
                        400,
                        f"Documento {doc_id} non trovato o scaduto. Ricaricalo.",
                    )
                content_blocks.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": doc.media_type,
                        "data": base64.standard_b64encode(doc.data).decode("ascii"),
                    },
                })
                logger.info(
                    "Resolved document %s (%s, %d bytes) for user_id=%s",
                    doc.doc_id, doc.filename, doc.size, user_id,
                )

            if m.content.strip():
                content_blocks.append({"type": "text", "text": m.content})

            api_messages.append({"role": m.role, "content": content_blocks})
        else:
            api_messages.append({"role": m.role, "content": m.content})

    return StreamingResponse(
        run_agent_stream(api_messages, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
