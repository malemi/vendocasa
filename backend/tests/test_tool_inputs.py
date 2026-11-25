"""Runtime validation of tool arguments (app/services/tool_inputs.py) and its
effect on the agent loop: an invalid call becomes a tool error, never a broken stream."""

from __future__ import annotations

import math

import pytest

from app.services import agent
from app.services.agent import run_agent_stream
from app.services.geocoder import _google_precision, _nominatim_precision, _photon_precision
from app.services.tool_inputs import validate_tool_input
from tests.fakes import FakeResponse, FakeToolUseBlock, make_fake_anthropic_factory


@pytest.mark.parametrize(
    ("tool", "arguments", "problem"),
    [
        ("valuate_property", {}, "address"),
        ("valuate_property", {"address": "Via Roma 1", "surface_m2": -5}, "surface_m2"),
        ("valuate_property", {"address": "Via Roma 1", "surface_m2": math.nan}, "surface_m2"),
        ("valuate_property", {"address": "Via Roma 1", "surface_m2": math.inf}, "surface_m2"),
        ("valuate_property", {"address": "Via Roma 1", "semester": "2024-2"}, "semester"),
        ("valuate_property", {"address": "Via Roma 1", "property_type": "abitazione"}, "property_type"),
        ("valuate_property", {"address": "Via Roma 1", "admin": True}, "admin"),
        ("enhanced_valuate_property", {"address": "Via Roma 1"}, "surface_m2"),
        ("enhanced_valuate_property", {"address": "Via Roma 1", "surface_m2": 80, "floor": "attic"}, "floor"),
        ("get_zone_quotations", {"link_zona": "MI00000290; DROP", "semester": "2024_S2"}, "link_zona"),
        ("get_zone_quotations", {"link_zona": "MI00000290"}, "semester"),
    ],
)
def test_invalid_arguments_are_refused_with_the_field_named(tool, arguments, problem):
    with pytest.raises(ValueError) as info:
        validate_tool_input(tool, arguments)
    assert problem in str(info.value)


def test_valid_arguments_get_their_defaults():
    args = validate_tool_input("enhanced_valuate_property", {"address": " Via Roma 1 ", "surface_m2": 80})
    assert (args.address, args.property_type, args.conservation_state) == ("Via Roma 1", 20, "NORMALE")


def test_unknown_tools_and_non_object_arguments_are_refused():
    with pytest.raises(ValueError, match="Unknown tool"):
        validate_tool_input("drop_tables", {})
    with pytest.raises(ValueError, match="JSON object"):
        validate_tool_input("valuate_property", ["Via Roma 1"])


async def _run_with_tool_call(monkeypatch, name, arguments):
    tool_round = FakeResponse(content=[FakeToolUseBlock(id="t1", name=name, input=arguments)])
    factory = make_fake_anthropic_factory([tool_round, FakeResponse(content=[])])
    monkeypatch.setattr("app.services.agent.AsyncAnthropic", factory)
    events = [e async for e in run_agent_stream([{"role": "user", "content": "Ciao"}], db=None, account_id="acct")]
    return factory, events


@pytest.mark.asyncio
async def test_an_invalid_tool_call_becomes_a_tool_error_and_the_stream_completes(monkeypatch):
    factory, events = await _run_with_tool_call(monkeypatch, "valuate_property", {"surface_m2": 80})
    second_round = factory.instance.messages.calls[1]["messages"][-1]["content"][0]
    assert second_round["is_error"] is True
    assert "address" in second_round["content"]
    assert events[-1].startswith("event: done")


@pytest.mark.asyncio
async def test_an_unexpected_tool_failure_is_contained(monkeypatch):
    async def _boom(*args, **kwargs):
        raise RuntimeError("database connection lost")

    monkeypatch.setattr(agent, "valuate_address", _boom)
    factory, events = await _run_with_tool_call(monkeypatch, "valuate_property", {"address": "Via Roma 1"})
    second_round = factory.instance.messages.calls[1]["messages"][-1]["content"][0]
    assert second_round["is_error"] is True
    assert "database connection lost" not in second_round["content"]
    assert events[-1].startswith("event: done")


def test_geocoder_precision_is_exact_only_for_building_level_matches():
    assert _photon_precision({"properties": {"housenumber": "17"}}) == "exact"
    assert _photon_precision({"properties": {"type": "street"}}) == "approximate"
    assert _nominatim_precision({"type": "house"}) == "exact"
    assert _nominatim_precision({"type": "residential", "addresstype": "road"}) == "approximate"
    assert _google_precision({"geometry": {"location_type": "ROOFTOP"}}) == "exact"
    assert _google_precision({"geometry": {"location_type": "GEOMETRIC_CENTER"}}) == "approximate"
    assert _photon_precision({}) == "approximate"
