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
class FakeUsage:
    input_tokens: int = 1_000
    output_tokens: int = 200
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class FakeResponse:
    content: list = field(default_factory=list)
    usage: FakeUsage | None = field(default_factory=FakeUsage)
    stop_reason: str = "end_turn"


@dataclass
class FakeTokenCount:
    input_tokens: int


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
        self.counted: list[dict] = []

    async def count_tokens(self, **kwargs):
        self.counted.append(kwargs)
        return FakeTokenCount(input_tokens=1_000)

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

    async def count_tokens(self, **kwargs):
        return FakeTokenCount(input_tokens=1_000)

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


class FakeLedger:
    """In-memory stand-in for app/services/spending.py in unit tests.

    It applies the same cap and switch rules; the real ledger's transactions,
    locking and recovery are tested on PostgreSQL in tests/integration/.
    """

    def __init__(self, account_cap: int = 1_000_000, global_cap: int = 100_000_000):
        self.account_cap = account_cap
        self.global_cap = global_cap
        self.enabled = True
        self.spent: dict[str, int] = {}
        self.reserved: dict[str, int] = {}
        self.open: dict[str, tuple[str, int]] = {}
        self.settlements: list[tuple[str, int | None]] = []
        self.kinds: list[str] = []
        self._next = 0

    def _total(self, scope):
        return self.spent.get(scope, 0) + self.reserved.get(scope, 0)

    async def reserve(self, account_id, kind, amount_micro, *, now=None):
        from app.services.spending import Reservation, SpendRefused, month_of

        if not self.enabled:
            raise SpendRefused("paused")
        if self._total("global") + amount_micro > self.global_cap:
            raise SpendRefused("global_limit")
        if self._total(account_id) + amount_micro > self.account_cap:
            raise SpendRefused("account_limit")
        for scope in ("global", account_id):
            self.reserved[scope] = self.reserved.get(scope, 0) + amount_micro
        self._next += 1
        rid = f"r{self._next}"
        self.open[rid] = (account_id, amount_micro)
        self.kinds.append(kind)
        return Reservation(rid, account_id, month_of(now), amount_micro)

    async def settle(self, reservation, actual_micro):
        rid = reservation.id if hasattr(reservation, "id") else reservation
        if rid not in self.open:
            return False
        account_id, amount = self.open.pop(rid)
        charged = amount if actual_micro is None else actual_micro
        for scope in ("global", account_id):
            self.reserved[scope] -= amount
            self.spent[scope] = self.spent.get(scope, 0) + charged
        self.settlements.append((rid, actual_micro))
        return True

    async def precheck(self, account_id):
        from app.services.spending import SpendRefused

        if not self.enabled:
            raise SpendRefused("paused")
        if self._total("global") >= self.global_cap:
            raise SpendRefused("global_limit")
        if self._total(account_id) >= self.account_cap:
            raise SpendRefused("account_limit")
