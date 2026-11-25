"""Runtime validation of the agent's tool arguments.

The model writes tool arguments; nothing guarantees they match the declared
schema. Each tool's arguments are validated here before any service runs, and
an invalid call becomes a controlled tool error the model can correct, instead
of an exception that would break a stream already in progress.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

SEMESTER_PATTERN = r"^\d{4}_S[12]$"
LINK_ZONA_PATTERN = r"^[A-Z0-9]{2,12}$"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ValuatePropertyInput(_Strict):
    address: str = Field(min_length=3, max_length=300)
    property_type: int = Field(20, ge=1, le=99)
    surface_m2: float | None = Field(None, gt=0, le=100_000, allow_inf_nan=False)
    semester: str | None = Field(None, pattern=SEMESTER_PATTERN)


class EnhancedValuatePropertyInput(ValuatePropertyInput):
    surface_m2: float = Field(gt=0, le=100_000, allow_inf_nan=False)
    conservation_state: Literal["OTTIMO", "NORMALE", "SCADENTE"] = "NORMALE"
    renovation: Literal["premium_post_2015", "standard_recent", "none", "needs_work"] | None = None
    floor: Literal["ground_semi", "first", "second", "third_fourth", "fifth_plus", "penthouse"] | None = None
    exposure: Literal["south_dual", "east_west", "north_only", "internal_dark"] | None = None
    noise: Literal["very_silent", "silent_courtyard", "normal", "street_moderate", "busy_street"] | None = None
    common_areas: Literal["excellent", "good", "needs_maintenance", "poor", "serious_neglect"] | None = None
    building_facade: Literal["recently_restored", "good_condition", "needs_work", "visibly_degraded"] | None = None
    energy_class: Literal["A_B", "C_D", "E", "F_G"] | None = None
    elevator: Literal["yes", "no_low_floor", "no_high_floor"] | None = None


class CoefficientInfoInput(_Strict):
    pass


class ZoneQuotationsInput(_Strict):
    link_zona: str = Field(pattern=LINK_ZONA_PATTERN)
    semester: str = Field(pattern=SEMESTER_PATTERN)
    property_type: int = Field(20, ge=1, le=99)


TOOL_INPUTS: dict[str, type[_Strict]] = {
    "valuate_property": ValuatePropertyInput,
    "enhanced_valuate_property": EnhancedValuatePropertyInput,
    "get_coefficient_info": CoefficientInfoInput,
    "get_zone_quotations": ZoneQuotationsInput,
}

DETAIL_FIELDS = (
    "conservation_state", "renovation", "floor", "exposure", "noise",
    "common_areas", "building_facade", "energy_class", "elevator",
)


def validate_tool_input(tool_name: str, tool_input: object) -> _Strict:
    """Return the validated arguments, or raise ValueError describing the problem."""
    model = TOOL_INPUTS.get(tool_name)
    if model is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    if not isinstance(tool_input, dict):
        raise ValueError("Tool arguments must be a JSON object")
    try:
        return model.model_validate(tool_input)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in error['loc']) or 'arguments'}: {error['msg']}"
            for error in exc.errors()
        )
        raise ValueError(f"Invalid arguments for {tool_name}: {problems}") from None
