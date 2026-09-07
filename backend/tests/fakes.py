"""Fake Anthropic SDK objects for testing the agent loop without network access."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class FakeResponse:
    content: list = field(default_factory=list)


class FakeStreamContext:
    """Mimics `client.messages.stream(...)` as an async context manager."""

    def __init__(self, response: FakeResponse):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __aiter__(self):
        async def _empty():
            return
            yield  # pragma: no cover -- makes this an async generator

        return _empty()

    async def get_final_message(self) -> FakeResponse:
        return self._response


class FakeMessages:
    """Records every `.stream(**kwargs)` call and returns responses in order.

    `responses` is a list of FakeResponse; once exhausted, the last response
    is repeated (so a test can force N rounds by supplying N-1 tool-use
    responses followed by one final no-tool-use response, or force the loop
    to run out its cap by supplying only tool-use responses).
    """

    def __init__(self, responses: list[FakeResponse]):
        self._responses = responses
        self.calls: list[dict] = []

    def stream(self, **kwargs):
        index = min(len(self.calls), len(self._responses) - 1)
        self.calls.append(kwargs)
        return FakeStreamContext(self._responses[index])


class FakeAsyncAnthropic:
    """Drop-in replacement for `anthropic.AsyncAnthropic` used in tests."""

    def __init__(self, responses: list[FakeResponse]):
        self.init_kwargs: dict = {}
        self.messages = FakeMessages(responses)

    def __call__(self, **kwargs):
        # Supports being used as a monkeypatched class: AsyncAnthropic(**kwargs)
        self.init_kwargs = kwargs
        return self


class FakeMessagesRaising:
    """A `.messages` whose `.stream(...)` always raises, for testing that the
    agent loop never forwards raw exception text to the client.
    """

    def __init__(self, exc: Exception):
        self._exc = exc

    def stream(self, **kwargs):
        raise self._exc


class FakeAsyncAnthropicRaising:
    def __init__(self, exc: Exception):
        self.init_kwargs: dict = {}
        self.messages = FakeMessagesRaising(exc)

    def __call__(self, **kwargs):
        self.init_kwargs = kwargs
        return self


def make_raising_anthropic_factory(exc: Exception):
    """Return a monkeypatch replacement for AsyncAnthropic whose first API
    call raises `exc` -- simulates an Anthropic SDK/HTTP error mid-request.
    """
    instance = FakeAsyncAnthropicRaising(exc)

    def _factory(**kwargs):
        instance.init_kwargs = kwargs
        return instance

    _factory.instance = instance
    return _factory


def make_fake_anthropic_factory(responses: list[FakeResponse]):
    """Return a callable usable as a monkeypatch replacement for AsyncAnthropic.

    `agent.py` does `AsyncAnthropic(api_key=..., base_url=...)` -- calling the
    returned factory captures those kwargs on the single fake client instance
    it always returns.
    """
    instance = FakeAsyncAnthropic(responses)

    def _factory(**kwargs):
        instance.init_kwargs = kwargs
        return instance

    _factory.instance = instance
    return _factory
