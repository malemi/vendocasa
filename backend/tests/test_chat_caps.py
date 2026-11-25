"""Tests for the 400 caps on /api/chat: history length, message length,
and total attachment bytes (backend/app/api/chat.py).
"""

from __future__ import annotations

from app.config import settings
from app.services.document_store import store_document
from tests.auth_helpers import auth_headers

ACCOUNT = "11111111-1111-4111-8111-111111111111"


def test_history_length_cap_returns_400(client, monkeypatch):
    monkeypatch.setattr(settings, "agent_max_history_messages", 2)

    body = {
        "messages": [
            {"role": "user", "content": "uno"},
            {"role": "assistant", "content": "due"},
            {"role": "user", "content": "tre"},
        ]
    }
    response = client.post("/api/chat", json=body, headers=auth_headers(ACCOUNT))
    assert response.status_code == 400


def test_message_length_cap_returns_400(client, monkeypatch):
    monkeypatch.setattr(settings, "agent_max_message_chars", 10)

    body = {"messages": [{"role": "user", "content": "x" * 11}]}
    response = client.post("/api/chat", json=body, headers=auth_headers(ACCOUNT))
    assert response.status_code == 400


def test_within_caps_is_not_rejected(client, fake_anthropic, monkeypatch):
    """Sanity check: the caps reject only what exceeds them."""
    fake_anthropic()
    monkeypatch.setattr(settings, "agent_max_history_messages", 5)
    monkeypatch.setattr(settings, "agent_max_message_chars", 100)

    body = {"messages": [{"role": "user", "content": "Ciao, valuta Via Roma 1 Milano"}]}
    response = client.post("/api/chat", json=body, headers=auth_headers(ACCOUNT))
    assert response.status_code == 200


def test_attachment_byte_budget_returns_400(client, monkeypatch):
    """AGENT_MAX_MESSAGE_CHARS bounds text only -- total attachment bytes
    across the whole request must be capped separately (integration review
    finding: without this, a request can carry MAX_FILES_PER_MESSAGE x
    AGENT_MAX_HISTORY_MESSAGES x 5 MB and re-bill that near the model's
    context window on every tool-calling round).
    """
    monkeypatch.setattr(settings, "agent_max_attachment_bytes", 100)  # tiny, deterministic

    doc = store_document(
        owner_id=ACCOUNT,
        filename="scan.pdf",
        media_type="application/pdf",
        data=b"%PDF-" + b"0" * 200,  # 205 bytes > the 100-byte budget
    )

    body = {
        "messages": [
            {"role": "user", "content": "Guarda questo documento", "document_ids": [doc.doc_id]}
        ]
    }
    response = client.post("/api/chat", json=body, headers=auth_headers(ACCOUNT))
    assert response.status_code == 400
    # The refusal is the byte budget, not a missing document (also a 400).
    assert "Allegati troppo grandi" in response.json()["detail"]


def test_attachment_byte_budget_sums_across_messages(client, monkeypatch):
    """The budget is a running total across the WHOLE request, not just one
    message -- several small attachments that individually fit must still
    be rejected once their sum exceeds the budget.
    """
    monkeypatch.setattr(settings, "agent_max_attachment_bytes", 150)

    doc_a = store_document(owner_id=ACCOUNT, filename="a.pdf", media_type="application/pdf", data=b"%PDF-" + b"a" * 90)
    doc_b = store_document(owner_id=ACCOUNT, filename="b.pdf", media_type="application/pdf", data=b"%PDF-" + b"b" * 90)

    body = {
        "messages": [
            {"role": "user", "content": "primo", "document_ids": [doc_a.doc_id]},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "secondo", "document_ids": [doc_b.doc_id]},
        ]
    }
    response = client.post("/api/chat", json=body, headers=auth_headers(ACCOUNT))
    assert response.status_code == 400
    assert "Allegati troppo grandi" in response.json()["detail"]
