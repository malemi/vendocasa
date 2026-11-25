"""Chat API endpoint — streams AI agent responses via Server-Sent Events."""

from __future__ import annotations

import base64
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import Account, current_account
from app.config import settings
from app.database import get_db
from app.refusals import refusal
from app.services.agent import run_agent_stream
from app.services.document_store import MAX_FILES_PER_MESSAGE, get_document
from app.services.rate_limit import get_client_ip, rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    # Only conversation turns. A client-supplied "system" entry would reach the
    # model as operator instructions, so any other role is refused (422).
    role: Literal["user", "assistant"]
    content: str
    document_ids: list[str] | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@router.post("/api/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(current_account),
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
    client_ip = get_client_ip(request)
    logger.info("Chat request from account %s (%d messages)", account.id, len(body.messages))

    identity_decision = rate_limiter.check_identity(account.id, client_ip)
    if not identity_decision.allowed:
        raise HTTPException(
            status_code=429,
            detail=refusal("rate_limited"),
            headers={"Retry-After": str(identity_decision.retry_after_seconds)},
        )

    global_decision = rate_limiter.peek_global_model_calls()
    if not global_decision.allowed:
        raise HTTPException(status_code=503, detail=refusal("daily_limit"))

    # ANTHROPIC_API_KEY presence is enforced at startup (app/main.py) --
    # this process would not be serving traffic if it were missing.

    # Bound the worst-case cost of a single request: cap how much conversation
    # history a client can make the backend re-send to Claude on every
    # tool-calling round (see agent.py's max_tool_rounds loop).
    if len(body.messages) > settings.agent_max_history_messages:
        raise HTTPException(
            400,
            f"Conversazione troppo lunga (massimo {settings.agent_max_history_messages} messaggi).",
        )
    for m in body.messages:
        if len(m.content) > settings.agent_max_message_chars:
            raise HTTPException(
                400,
                f"Messaggio troppo lungo (massimo {settings.agent_max_message_chars} caratteri).",
            )

    # Build Claude API messages, resolving document_ids to content blocks.
    # AGENT_MAX_MESSAGE_CHARS above bounds text only -- a message can still
    # carry MAX_FILES_PER_MESSAGE attachments, and the client can send up to
    # agent_max_history_messages such messages, so track a running total of
    # attachment bytes across the WHOLE request and cut it off before that
    # dwarfs the text-only cost bound (see agent_max_attachment_bytes).
    api_messages: list[dict] = []
    total_attachment_bytes = 0
    for m in body.messages:
        if m.document_ids and m.role == "user":
            if len(m.document_ids) > MAX_FILES_PER_MESSAGE:
                raise HTTPException(
                    400,
                    f"Massimo {MAX_FILES_PER_MESSAGE} documenti per messaggio.",
                )

            # Multi-block content: documents/images first, then text
            content_blocks: list[dict] = []
            for doc_id in m.document_ids:
                doc = get_document(doc_id, account.id)
                if doc is None:
                    raise HTTPException(
                        400,
                        f"Documento {doc_id} non trovato o scaduto. Ricaricalo.",
                    )
                total_attachment_bytes += doc.size
                if total_attachment_bytes > settings.agent_max_attachment_bytes:
                    raise HTTPException(
                        400,
                        "Allegati troppo grandi (massimo "
                        f"{settings.agent_max_attachment_bytes // (1024 * 1024)} MB totali per conversazione).",
                    )
                b64_data = base64.standard_b64encode(doc.data).decode("ascii")
                if doc.is_image:
                    content_blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": doc.media_type,
                            "data": b64_data,
                        },
                    })
                else:
                    content_blocks.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": doc.media_type,
                            "data": b64_data,
                        },
                    })
                logger.info(
                    "Resolved %s %s (%d bytes) for account %s",
                    "image" if doc.is_image else "document",
                    doc.doc_id, doc.size, account.id,
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
