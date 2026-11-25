"""Body limits before parsing (backend/app/middleware.py), on a minimal app."""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app import middleware

reads: list[int] = []


async def echo_length(request: Request) -> JSONResponse:
    body = await request.body()
    reads.append(len(body))
    return JSONResponse({"received": len(body)})


@pytest.fixture
def small_limit_client(monkeypatch):
    monkeypatch.setattr(middleware, "BODY_LIMITS", {"/api/chat": 100})
    monkeypatch.setattr(middleware, "DEFAULT_BODY_LIMIT", 10)
    reads.clear()
    app = Starlette(routes=[Route("/api/chat", echo_length, methods=["POST"]),
                            Route("/api/other", echo_length, methods=["POST"])])
    app.add_middleware(middleware.BodyLimitMiddleware)
    with TestClient(app) as client:
        yield client


def test_a_body_within_the_limit_passes(small_limit_client):
    assert small_limit_client.post("/api/chat", content=b"x" * 100).json() == {"received": 100}


def test_a_declared_oversized_body_is_refused_before_it_is_read(small_limit_client):
    response = small_limit_client.post("/api/chat", content=b"x" * 101)
    assert response.status_code == 413
    assert response.json()["detail"]["error"] == "too_large"
    assert reads == []


def test_an_undeclared_oversized_body_is_refused_while_it_is_read(small_limit_client):
    def chunks():
        for _ in range(5):
            yield b"x" * 30  # 150 bytes, no Content-Length: sent chunked

    response = small_limit_client.post("/api/chat", content=chunks())
    assert response.status_code == 413
    assert reads == []  # the handler never got the body


def test_other_paths_get_the_default_limit(small_limit_client):
    assert small_limit_client.post("/api/other", content=b"x" * 11).status_code == 413
    assert small_limit_client.post("/api/other", content=b"x" * 10).status_code == 200


def test_a_malformed_content_length_is_refused(small_limit_client):
    response = small_limit_client.post("/api/chat", content=b"x", headers={"content-length": "abc"})
    assert response.status_code in (400, 413)
