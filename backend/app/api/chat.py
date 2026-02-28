"""Chat API endpoint — streams AI agent responses via Server-Sent Events."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.agent import run_agent_stream

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


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

    api_messages = [{"role": m.role, "content": m.content} for m in body.messages]

    return StreamingResponse(
        run_agent_stream(api_messages, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
