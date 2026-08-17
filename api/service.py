"""Translation layer between the HTTP payloads and the simulation orchestrator.

This module deliberately holds no traffic formulas. All policy effects live in
``simulation/policy_effects.py`` and all sequencing lives in
``simulation/orchestrator.py``.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from simulation.goals import GoalConfig
from simulation.orchestrator import SimulationOutcome, run_simulation
from simulation.scenario import (
    DEFAULT_BASELINE_GREEN_SECONDS,
    ParkingPolicy,
    RedLinePolicy,
    ScenarioDiff,
    ScenarioPolicy,
    SignalTimingPolicy,
)

from .schemas import (
    GoalConfigPayload,
    PolicyPayload,
    SimulationRequest,
    SimulationResponse,
)


UNMODELLED_POLICY_WARNING = (
    "traffic-restriction policies are recorded but do not affect the MVP "
    "simulation: route choice is not modelled yet."
)


def _green_seconds_from_phases(policy: PolicyPayload) -> Optional[int]:
    if not policy.phases:
        return None
    for phase in policy.phases:
        if phase.color == "green":
            return int(phase.seconds)
    return None


def _signal_policy(policy: PolicyPayload) -> SignalTimingPolicy:
    scenario_seconds = policy.scenario_seconds or _green_seconds_from_phases(policy)
    baseline_seconds = policy.baseline_seconds or DEFAULT_BASELINE_GREEN_SECONDS

    return SignalTimingPolicy(
        intersection_id=policy.intersection_id or "unspecified-intersection",
        baseline_seconds=int(baseline_seconds),
        scenario_seconds=int(
            scenario_seconds if scenario_seconds is not None else baseline_seconds
        ),
    )


def to_scenario_diff(request: SimulationRequest) -> ScenarioDiff:
    """Build the internal ScenarioDiff from the HTTP payload.

    Entries that do not differ from baseline are dropped, so an untouched
    scenario yields an empty diff.
    """
    policies: List[ScenarioPolicy] = []

    for payload in request.policies:
        if payload.type == "signal-timing":
            policies.append(_signal_policy(payload))
        elif payload.type == "red-line":
            policies.append(
                RedLinePolicy(
                    road_id=payload.road_id or request.road_id or "unspecified-road",
                    length_meters=float(payload.length_meters or 0.0),
                )
            )
        elif payload.type == "parking":
            policies.append(
                ParkingPolicy(
                    parking_id=payload.parking_id or "unspecified-parking",
                    spaces=int(payload.spaces or 0),
                )
            )
        # traffic-restriction is intentionally not converted: it is not one of
        # the three modelled variables. It is surfaced as a warning instead.

    return ScenarioDiff(
        scenario_id=request.scenario_id,
        policies=tuple(policies),
    ).changed_only()


def to_goal_config(payload: Optional[GoalConfigPayload]) -> Optional[GoalConfig]:
    if payload is None:
        return None
    return GoalConfig(
        travel_time_percent=payload.travel_time_percent,
        travel_speed_percent=payload.travel_speed_percent,
        congestion_vc_percent=payload.congestion_vc_percent,
        queue_percent=payload.queue_percent,
    )


def unmodelled_policy_warnings(policies: Iterable[PolicyPayload]) -> List[str]:
    if any(policy.type == "traffic-restriction" for policy in policies):
        return [UNMODELLED_POLICY_WARNING]
    return []


def simulate(request: SimulationRequest) -> SimulationOutcome:
    diff = to_scenario_diff(request)
    return run_simulation(
        diff,
        day_type=request.day_type,
        time_slot=request.time_slot,
        random_seed=request.random_seed,
        road_id=request.road_id,
        road_name=request.road_name,
        goals=to_goal_config(request.goals),
    )


def run_frontend_simulation(request: SimulationRequest) -> SimulationResponse:
    outcome = simulate(request)

    warnings: List[str] = list(outcome.warnings)
    warnings.extend(unmodelled_policy_warnings(request.policies))

    payload = outcome.to_dict()
    payload["warnings"] = warnings

    return SimulationResponse(**payload)
