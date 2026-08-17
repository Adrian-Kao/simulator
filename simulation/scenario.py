"""ScenarioDiff: the machine-readable difference between baseline and a policy scenario.

Baseline data (roads, signals, parking, YouBike, existing red lines) is *not* a
scenario policy. Only a change relative to baseline belongs in a ``ScenarioDiff``.

The first demo release exposes exactly three optimisable variables:

    X1 = signal_green_seconds
    X2 = red_line_meters
    X3 = parking_spaces

Bounds for those three variables are centralised here so that the API, the
optimiser and the Gemini validation layer cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Bounds and defaults (single source of truth)
# ---------------------------------------------------------------------------

DEFAULT_BASELINE_GREEN_SECONDS = 40

SIGNAL_GREEN_SECONDS_BOUNDS: Tuple[int, int] = (20, 68)
RED_LINE_METERS_BOUNDS: Tuple[float, float] = (0.0, 500.0)
PARKING_SPACES_BOUNDS: Tuple[int, int] = (0, 300)

# Used only when a recommendation introduces a policy the initial scenario did
# not contain and no anchor id was supplied by the caller.
FALLBACK_INTERSECTION_ID = "unspecified-intersection"
FALLBACK_ROAD_ID = "unspecified-road"
FALLBACK_PARKING_ID = "unspecified-parking"


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignalTimingPolicy:
    """Green-time change for one movement at one intersection (X1)."""

    POLICY_TYPE: ClassVar[str] = "signal-timing"

    intersection_id: str
    baseline_seconds: int = DEFAULT_BASELINE_GREEN_SECONDS
    scenario_seconds: int = DEFAULT_BASELINE_GREEN_SECONDS

    @property
    def changed(self) -> bool:
        return int(self.scenario_seconds) != int(self.baseline_seconds)

    def to_dict(self) -> dict:
        return {
            "type": self.POLICY_TYPE,
            "intersection_id": self.intersection_id,
            "baseline_seconds": int(self.baseline_seconds),
            "scenario_seconds": int(self.scenario_seconds),
        }


@dataclass(frozen=True)
class RedLinePolicy:
    """Additional red-line (no-stopping) curb metres on one road (X2)."""

    POLICY_TYPE: ClassVar[str] = "red-line"

    road_id: str
    length_meters: float = 0.0

    @property
    def changed(self) -> bool:
        return float(self.length_meters) > 0.0

    def to_dict(self) -> dict:
        return {
            "type": self.POLICY_TYPE,
            "road_id": self.road_id,
            "length_meters": float(self.length_meters),
        }


@dataclass(frozen=True)
class ParkingPolicy:
    """Parking spaces added versus baseline (X3).

    The demo bounds are 0..300 added spaces; negative values are accepted by the
    dataclass but clamp to 0 through ``PARKING_SPACES_BOUNDS``.
    """

    POLICY_TYPE: ClassVar[str] = "parking"

    parking_id: str
    spaces: int = 0

    @property
    def changed(self) -> bool:
        return int(self.spaces) != 0

    def to_dict(self) -> dict:
        return {
            "type": self.POLICY_TYPE,
            "parking_id": self.parking_id,
            "spaces": int(self.spaces),
        }


ScenarioPolicy = Union[SignalTimingPolicy, RedLinePolicy, ParkingPolicy]

SUPPORTED_POLICY_TYPES: Tuple[str, ...] = (
    SignalTimingPolicy.POLICY_TYPE,
    RedLinePolicy.POLICY_TYPE,
    ParkingPolicy.POLICY_TYPE,
)


@dataclass(frozen=True)
class ScenarioDiff:
    scenario_id: str
    policies: Tuple[ScenarioPolicy, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.policies, tuple):
            object.__setattr__(self, "policies", tuple(self.policies))

    def validate(self) -> None:
        if not self.scenario_id:
            raise ValueError("scenario_id is required")
        for policy in self.policies:
            if not isinstance(
                policy, (SignalTimingPolicy, RedLinePolicy, ParkingPolicy)
            ):
                raise ValueError(f"Unsupported policy type: {type(policy)!r}")

    @property
    def signal_policies(self) -> Tuple[SignalTimingPolicy, ...]:
        return tuple(p for p in self.policies if isinstance(p, SignalTimingPolicy))

    @property
    def red_line_policies(self) -> Tuple[RedLinePolicy, ...]:
        return tuple(p for p in self.policies if isinstance(p, RedLinePolicy))

    @property
    def parking_policies(self) -> Tuple[ParkingPolicy, ...]:
        return tuple(p for p in self.policies if isinstance(p, ParkingPolicy))

    def is_empty(self) -> bool:
        return not any(policy.changed for policy in self.policies)

    def changed_only(self) -> "ScenarioDiff":
        """Drop policies that do not actually differ from baseline."""
        return ScenarioDiff(
            scenario_id=self.scenario_id,
            policies=tuple(p for p in self.policies if p.changed),
        )

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "policies": [policy.to_dict() for policy in self.policies],
        }


# ---------------------------------------------------------------------------
# Policy variables (X1, X2, X3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PolicyVariables:
    signal_green_seconds: int
    red_line_meters: float
    parking_spaces: int

    def to_dict(self) -> dict:
        return {
            "signal_green_seconds": int(self.signal_green_seconds),
            "red_line_meters": float(self.red_line_meters),
            "parking_spaces": int(self.parking_spaces),
        }


def clamp_signal_green_seconds(value: float) -> int:
    low, high = SIGNAL_GREEN_SECONDS_BOUNDS
    return int(max(low, min(high, round(float(value)))))


def clamp_red_line_meters(value: float) -> float:
    low, high = RED_LINE_METERS_BOUNDS
    return float(max(low, min(high, float(value))))


def clamp_parking_spaces(value: float) -> int:
    low, high = PARKING_SPACES_BOUNDS
    return int(max(low, min(high, round(float(value)))))


def clamp_variables(variables: PolicyVariables) -> PolicyVariables:
    return PolicyVariables(
        signal_green_seconds=clamp_signal_green_seconds(variables.signal_green_seconds),
        red_line_meters=clamp_red_line_meters(variables.red_line_meters),
        parking_spaces=clamp_parking_spaces(variables.parking_spaces),
    )


def bounds_manifest() -> dict:
    return {
        "signal_green_seconds": list(SIGNAL_GREEN_SECONDS_BOUNDS),
        "red_line_meters": list(RED_LINE_METERS_BOUNDS),
        "parking_spaces": list(PARKING_SPACES_BOUNDS),
    }


def baseline_variables(diff: ScenarioDiff) -> PolicyVariables:
    """Baseline is defined as: current green time, no extra red line, no extra parking."""
    signals = diff.signal_policies
    green = (
        int(signals[0].baseline_seconds)
        if signals
        else DEFAULT_BASELINE_GREEN_SECONDS
    )
    return PolicyVariables(
        signal_green_seconds=clamp_signal_green_seconds(green),
        red_line_meters=0.0,
        parking_spaces=0,
    )


def scenario_variables(diff: ScenarioDiff) -> PolicyVariables:
    signals = diff.signal_policies
    green = (
        int(signals[0].scenario_seconds)
        if signals
        else DEFAULT_BASELINE_GREEN_SECONDS
    )
    red_line = sum(float(p.length_meters) for p in diff.red_line_policies)
    parking = sum(int(p.spaces) for p in diff.parking_policies)
    return clamp_variables(
        PolicyVariables(
            signal_green_seconds=green,
            red_line_meters=red_line,
            parking_spaces=parking,
        )
    )


def variable_warnings(diff: ScenarioDiff) -> List[str]:
    """Report scenario content the MVP variable model collapses or ignores."""
    warnings: List[str] = []

    if len(diff.signal_policies) > 1:
        warnings.append(
            "Multiple signal-timing policies received; the MVP model only applies the "
            f"first one ({diff.signal_policies[0].intersection_id}) as X1."
        )

    if len(diff.red_line_policies) > 1:
        warnings.append(
            "Multiple red-line policies received; their lengths are summed into a "
            "single X2 curb-friction variable."
        )

    if len(diff.parking_policies) > 1:
        warnings.append(
            "Multiple parking policies received; their space changes are summed into "
            "a single X3 variable."
        )

    return warnings


# ---------------------------------------------------------------------------
# Recommendation validation (the only route an LLM can take into the model)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidatedRecommendation:
    variables: PolicyVariables
    notes: Tuple[str, ...]


def validate_recommendation(raw: object) -> ValidatedRecommendation:
    """Coerce an untrusted recommendation into bounded policy variables.

    Anything that is not one of the three allowed variables is discarded, and
    every out-of-bounds value is clamped and reported. This is the hard barrier
    between LLM output and the simulation.
    """
    if isinstance(raw, PolicyVariables):
        payload: Dict[str, object] = raw.to_dict()
    elif isinstance(raw, dict):
        payload = dict(raw)
    else:
        payload = {
            key: getattr(raw, key)
            for key in (
                "signal_green_seconds",
                "red_line_meters",
                "parking_spaces",
            )
            if hasattr(raw, key)
        }

    notes: List[str] = []

    rejected = sorted(
        key
        for key in payload
        if key
        not in {
            "signal_green_seconds",
            "red_line_meters",
            "parking_spaces",
            "reasoning",
        }
    )
    if rejected:
        notes.append(
            "Ignored fields outside the allowed policy variables: "
            + ", ".join(rejected)
        )

    def _number(key: str, fallback: float) -> float:
        value = payload.get(key, None)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            if value is not None:
                notes.append(f"{key} was not numeric; kept {fallback}.")
            return fallback
        return float(value)

    raw_signal = _number("signal_green_seconds", DEFAULT_BASELINE_GREEN_SECONDS)
    raw_red_line = _number("red_line_meters", 0.0)
    raw_parking = _number("parking_spaces", 0.0)

    variables = PolicyVariables(
        signal_green_seconds=clamp_signal_green_seconds(raw_signal),
        red_line_meters=clamp_red_line_meters(raw_red_line),
        parking_spaces=clamp_parking_spaces(raw_parking),
    )

    if variables.signal_green_seconds != round(raw_signal):
        notes.append(
            f"signal_green_seconds {raw_signal:g} clamped to "
            f"{variables.signal_green_seconds} "
            f"(bounds {SIGNAL_GREEN_SECONDS_BOUNDS[0]}-{SIGNAL_GREEN_SECONDS_BOUNDS[1]})."
        )

    if abs(variables.red_line_meters - raw_red_line) > 1e-9:
        notes.append(
            f"red_line_meters {raw_red_line:g} clamped to "
            f"{variables.red_line_meters:g} "
            f"(bounds {RED_LINE_METERS_BOUNDS[0]:g}-{RED_LINE_METERS_BOUNDS[1]:g})."
        )

    if variables.parking_spaces != round(raw_parking):
        notes.append(
            f"parking_spaces {raw_parking:g} clamped to {variables.parking_spaces} "
            f"(bounds {PARKING_SPACES_BOUNDS[0]}-{PARKING_SPACES_BOUNDS[1]})."
        )

    return ValidatedRecommendation(variables=variables, notes=tuple(notes))


def apply_variables(
    diff: ScenarioDiff,
    variables: PolicyVariables,
    *,
    intersection_id: Optional[str] = None,
    road_id: Optional[str] = None,
    parking_id: Optional[str] = None,
) -> ScenarioDiff:
    """Rebuild a ScenarioDiff so it expresses exactly ``variables``.

    Baseline green time is preserved from the incoming diff; only the three
    allowed variables move. Existing anchors (which intersection / road /
    parking facility) are reused so a patch never retargets a policy.
    """
    signals = diff.signal_policies
    red_lines = diff.red_line_policies
    parkings = diff.parking_policies

    baseline_green = (
        int(signals[0].baseline_seconds)
        if signals
        else DEFAULT_BASELINE_GREEN_SECONDS
    )

    signal_target = (
        signals[0].intersection_id
        if signals
        else (intersection_id or FALLBACK_INTERSECTION_ID)
    )
    road_target = red_lines[0].road_id if red_lines else (road_id or FALLBACK_ROAD_ID)
    parking_target = (
        parkings[0].parking_id if parkings else (parking_id or FALLBACK_PARKING_ID)
    )

    policies: List[ScenarioPolicy] = [
        SignalTimingPolicy(
            intersection_id=signal_target,
            baseline_seconds=baseline_green,
            scenario_seconds=clamp_signal_green_seconds(variables.signal_green_seconds),
        ),
        RedLinePolicy(
            road_id=road_target,
            length_meters=clamp_red_line_meters(variables.red_line_meters),
        ),
        ParkingPolicy(
            parking_id=parking_target,
            spaces=clamp_parking_spaces(variables.parking_spaces),
        ),
    ]

    return ScenarioDiff(scenario_id=diff.scenario_id, policies=tuple(policies))
