"""Deterministic stand-ins for the model provider and the public geocoders.

The browser journeys (frontend/e2e/) run the real backend over HTTP against
the local Supabase stack. Only two outside services are replaced: the model
provider, by the scripted substitute below, and the public geocoders, by
fixed coordinates for the two test addresses. Everything else is real: the
accounts, the spending ledger, the valuation queries and the stream.

The substitute answers the exact test prompts in SCRIPT with a tool call.
When a tool result comes back, it answers from the data the result carries,
so the journey sees what the database returned. A message with attachments
is answered with their count; any other message gets a short fixed reply.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.services.geocoder import GeoResult
from tests.fakes import FakeResponse, FakeTokenCount, FakeToolUseBlock, FakeUsage

EXACT_ADDRESS = "Via Roma 10, Milano"
APPROXIMATE_ADDRESS = "Via Incerta, Milano"

SCRIPT = {
    f"Valuta {EXACT_ADDRESS}, 80 mq": ("valuate_property", {"address": EXACT_ADDRESS, "surface_m2": 80}),
    f"Valuta {APPROXIMATE_ADDRESS}, 80 mq": (
        "valuate_property", {"address": APPROXIMATE_ADDRESS, "surface_m2": 80}),
}

# Inside the seeded zone MI00000001 (backend/tests/e2e/seed.py), outside its hole.
GEOCODED = {
    EXACT_ADDRESS: GeoResult(lat=45.42, lng=9.12, source="test", precision="exact",
                             matched_address="Via Roma 10, 20121 Milano"),
    APPROXIMATE_ADDRESS: GeoResult(lat=45.47, lng=9.18, source="test", precision="approximate",
                                   matched_address="Milano"),
}

FILLER_REPLY = "Risposta di prova."

# Typical sizes of a real call: the fixed prefix, about 9,000 tokens, is read
# from the prompt cache; a few hundred tokens are new. At the price table's
# Sonnet 5.5 rates one call costs 4,500 micro-dollars, which the journeys
# check against the ledger.
PREFIX_TOKENS = 9_000
NEW_INPUT_TOKENS = 300
OUTPUT_TOKENS = 300


async def geocode(self, address: str) -> GeoResult | None:
    """Replaces ItalianGeocoder.geocode: no request leaves the machine."""
    return GEOCODED.get(address.strip())


@dataclass
class TextBlock:
    text: str
    type: str = "text"


@dataclass
class _Delta:
    text: str


@dataclass
class _DeltaEvent:
    delta: _Delta
    type: str = "content_block_delta"


def _blocks(message: dict) -> list:
    content = message.get("content")
    return content if isinstance(content, list) else [{"type": "text", "text": content or ""}]


def _block_type(block) -> str:
    return block.get("type") if isinstance(block, dict) else getattr(block, "type", "")


def _summary(result: dict) -> str:
    if "error" in result:
        return f"Lo strumento ha risposto con un errore: {result['error']}"
    zone = result.get("zone") or {}
    parts = [f"Zona {zone.get('zone_code')} di {zone.get('municipality')}, semestre {result.get('semester')}."]
    for row in result.get("quotations") or []:
        parts.append(f"Quotazione OMI {row.get('conservation_state')}: "
                     f"{row.get('price_min')}-{row.get('price_max')} EUR/m2.")
    comparables = result.get("comparables") or []
    parts.append(f"Compravendite comparabili: {len(comparables)}.")
    for row in comparables:
        parts.append(f"{row.get('transaction_date')}: {row.get('declared_price')} EUR.")
    if result.get("no_data"):
        parts.append(result["no_data"].get("message", ""))
    return " ".join(parts)


def respond(messages: list[dict]) -> FakeResponse:
    """The substitute's answer to a conversation, as the provider would send it."""
    last = messages[-1]
    blocks = _blocks(last)
    tool_results = [b for b in blocks if _block_type(b) == "tool_result"]
    usage = FakeUsage(input_tokens=NEW_INPUT_TOKENS, output_tokens=OUTPUT_TOKENS,
                      cache_read_input_tokens=PREFIX_TOKENS)
    if tool_results:
        text = " ".join(_summary(json.loads(b["content"])) for b in tool_results)
        return FakeResponse(content=[TextBlock(text)], usage=usage)
    attachments = [b for b in blocks if _block_type(b) in ("document", "image")]
    if attachments:
        return FakeResponse(content=[TextBlock(f"Allegati ricevuti: {len(attachments)}.")], usage=usage)
    prompt = " ".join(b.get("text", "") for b in blocks if _block_type(b) == "text").strip()
    if prompt in SCRIPT:
        name, tool_input = SCRIPT[prompt]
        call = FakeToolUseBlock(id=f"toolu_{len(messages)}", name=name, input=tool_input)
        return FakeResponse(content=[call], usage=usage, stop_reason="tool_use")
    return FakeResponse(content=[TextBlock(FILLER_REPLY)], usage=usage)


class _Stream:
    def __init__(self, response: FakeResponse):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __aiter__(self):
        async def events():
            for block in self._response.content:
                if isinstance(block, TextBlock):
                    for word in block.text.split(" "):
                        yield _DeltaEvent(_Delta(word + " "))

        return events()

    async def get_final_message(self) -> FakeResponse:
        return self._response


class _Messages:
    async def count_tokens(self, **kwargs) -> FakeTokenCount:
        return FakeTokenCount(input_tokens=PREFIX_TOKENS + 100 * len(kwargs.get("messages", [])))

    def stream(self, **kwargs) -> _Stream:
        return _Stream(respond(kwargs["messages"]))


class SubstituteAnthropic:
    """Replaces anthropic.AsyncAnthropic in app/services/agent.py."""

    def __init__(self, **kwargs):
        self.messages = _Messages()
