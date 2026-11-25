"""Tests for the bounded tool-calling loop and model/key isolation in agent.py."""

from __future__ import annotations

import pytest

from app.config import settings
from app.services.agent import run_agent_stream
from tests.fakes import (
    FakeResponse,
    FakeToolUseBlock,
    make_fake_anthropic_factory,
    make_raising_anthropic_factory,
)


async def _collect(generator):
    return [chunk async for chunk in generator]


@pytest.mark.asyncio
async def test_loop_stops_at_max_tool_rounds(monkeypatch):
    """A model that always wants another tool call must not loop forever."""
    monkeypatch.setattr(settings, "agent_max_tool_rounds", 3)

    always_tool_use = FakeResponse(
        content=[FakeToolUseBlock(id="call-1", name="not_a_real_tool", input={})]
    )
    factory = make_fake_anthropic_factory([always_tool_use])
    monkeypatch.setattr("app.services.agent.AsyncAnthropic", factory)

    events = await _collect(run_agent_stream([{"role": "user", "content": "Ciao"}], db=None))

    assert len(factory.instance.messages.calls) == 3
    assert any(e.startswith("event: done") for e in events)
    # The loop must not have raised or produced an error event.
    assert not any(e.startswith("event: error") for e in events)


@pytest.mark.asyncio
async def test_loop_stops_early_when_global_ceiling_hit(monkeypatch):
    """The global daily model-call ceiling stops the loop even mid-request."""
    monkeypatch.setattr(settings, "agent_max_tool_rounds", 5)
    monkeypatch.setattr(settings, "rate_limit_global_daily_model_calls", 1)

    always_tool_use = FakeResponse(
        content=[FakeToolUseBlock(id="call-1", name="not_a_real_tool", input={})]
    )
    factory = make_fake_anthropic_factory([always_tool_use])
    monkeypatch.setattr("app.services.agent.AsyncAnthropic", factory)

    events = await _collect(run_agent_stream([{"role": "user", "content": "Ciao"}], db=None))

    # Only one round should have actually called the model: the ceiling is 1.
    assert len(factory.instance.messages.calls) == 1
    # The user is told why the answer stopped, then the stream ends.
    error_events = [e for e in events if e.startswith("event: error")]
    assert len(error_events) == 1
    assert '"error": "daily_limit"' in error_events[0]
    assert events[-1].startswith("event: done")


@pytest.mark.asyncio
async def test_model_id_is_server_config_only(monkeypatch):
    """The model sent to Anthropic always comes from settings, never the request."""
    monkeypatch.setattr(settings, "anthropic_model", "claude-sonnet-test-pin")

    factory = make_fake_anthropic_factory([FakeResponse(content=[])])
    monkeypatch.setattr("app.services.agent.AsyncAnthropic", factory)

    # Even if a message dict smuggled in a "model" key, it has no effect --
    # run_agent_stream never reads a model id out of the message content.
    messages = [{"role": "user", "content": "Ciao", "model": "claude-opus-4-6"}]
    await _collect(run_agent_stream(messages, db=None))

    assert factory.instance.messages.calls[0]["model"] == "claude-sonnet-test-pin"


@pytest.mark.asyncio
async def test_sse_error_event_never_forwards_raw_exception_text(monkeypatch):
    """The SSE error event must not leak provider error detail (status codes,
    rate-limit info, request internals) to an anonymous caller.
    """
    secret_looking_message = "401 Unauthorized: invalid x-api-key sk-ant-secret-abc123"
    factory = make_raising_anthropic_factory(RuntimeError(secret_looking_message))
    monkeypatch.setattr("app.services.agent.AsyncAnthropic", factory)

    events = await _collect(run_agent_stream([{"role": "user", "content": "Ciao"}], db=None))

    error_events = [e for e in events if e.startswith("event: error")]
    assert len(error_events) == 1
    assert secret_looking_message not in error_events[0]
    assert '"error": "assistant_unavailable"' in error_events[0]


@pytest.mark.asyncio
async def test_base_url_passed_explicitly(monkeypatch):
    """base_url is always passed to the SDK client, never left to fall back
    to an ambient ANTHROPIC_BASE_URL environment variable.
    """
    monkeypatch.setattr(settings, "anthropic_base_url", "https://api.anthropic.com")

    factory = make_fake_anthropic_factory([FakeResponse(content=[])])
    monkeypatch.setattr("app.services.agent.AsyncAnthropic", factory)

    await _collect(run_agent_stream([{"role": "user", "content": "Ciao"}], db=None))

    assert factory.instance.init_kwargs["base_url"] == "https://api.anthropic.com"
