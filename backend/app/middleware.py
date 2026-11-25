"""Request body limits, enforced before the body is parsed.

A declared `Content-Length` above the route's limit is refused at once. A body
without a length, or one that turns out longer than declared, is counted chunk
by chunk while the application reads it, and refused as soon as it passes the
limit. Refusals use the `too_large` code (app/refusals.py) with status 413.
"""

from __future__ import annotations

import json

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.refusals import refusal

KIB = 1024
MIB = 1024 * KIB

# Per-path limits; every other path gets DEFAULT_BODY_LIMIT.
BODY_LIMITS = {
    "/api/chat": 1 * MIB,
    "/api/documents/upload": 6 * MIB,
}
DEFAULT_BODY_LIMIT = 64 * KIB


class _BodyTooLarge(Exception):
    pass


async def _send_too_large(send: Send) -> None:
    body = json.dumps({"detail": refusal("too_large")}, ensure_ascii=False).encode()
    await send({
        "type": "http.response.start",
        "status": 413,
        "headers": [(b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode())],
    })
    await send({"type": "http.response.body", "body": body})


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = BODY_LIMITS.get(scope.get("path", ""), DEFAULT_BODY_LIMIT)
        declared = Headers(scope=scope).get("content-length")
        if declared is not None:
            try:
                too_long = int(declared) > limit
            except ValueError:
                too_long = True
            if too_long:
                await _send_too_large(send)
                return

        received = 0
        response_started = False

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _BodyTooLarge()
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _BodyTooLarge:
            if not response_started:
                await _send_too_large(send)
