"""Translation layer between the HTTP payloads and the simulation orchestrator.

This module deliberately holds no traffic formulas. All policy effects live in
``simulation/policy_effects.py`` and all sequencing lives in
``simulation/orchestrator.py``.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from simulation.goals import GoalConfig
from simulation.orchestrator import SimulationOutcome, run_simulation
from simulation.policy_behavior import (
    ModeContext,
    development_signals,
    evaluate_population,
    policy_mode_context,
)
from simulation.scenario import (
    DEFAULT_BASELINE_GREEN_SECONDS,
    ParkingPolicy,
    RedLinePolicy,
    ScenarioDiff,
    ScenarioPolicy,
    SignalTimingPolicy,
)

from .schemas import (
    BehaviorImpact,
    DevelopmentImpact,
    GoalConfigPayload,
    ModeShare,
    PolicyPayload,
    SimulationRequest,
    SimulationResponse,
)


UNMODELLED_POLICY_WARNING = (
    "traffic-restriction affects agent route/mode choice, but its direct road "
    "network capacity effect is not modelled yet."
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

    baseline_mode_share = evaluate_population(ModeContext())
    scenario_mode_share = evaluate_population(
        policy_mode_context(
            request.policies,
            outcome.scenario_variables.signal_green_seconds,
        )
    )
    shifted_share = sum(
        abs(scenario_mode_share[mode] - baseline_mode_share[mode])
        for mode in baseline_mode_share
    ) / 2.0
    payload["behavior"] = BehaviorImpact(
        population=100,
        baseline_mode_share=ModeShare(**baseline_mode_share),
        scenario_mode_share=ModeShare(**scenario_mode_share),
        shifted_people=round(shifted_share * 100),
    ).model_dump()
    payload["development"] = DevelopmentImpact(
        parking_demand_percent=_share_change(
            baseline_mode_share["drive"], scenario_mode_share["drive"]
        ),
        transit_demand_percent=_share_change(
            baseline_mode_share["transit"], scenario_mode_share["transit"]
        ),
        youbike_demand_percent=_share_change(
            baseline_mode_share["youbike"], scenario_mode_share["youbike"]
        ),
        transport_emissions_percent=_share_change(
            baseline_mode_share["drive"], scenario_mode_share["drive"]
        ),
        signals=development_signals(baseline_mode_share, scenario_mode_share),
    ).model_dump()

    if request.policies:
        payload["warnings"].append(
            "Agent and development impacts are deterministic planning estimates; "
            "calibrate coefficients with observed before/after data before deployment."
        )

    return SimulationResponse(**payload)


def _share_change(baseline: float, scenario: float) -> float:
    """Return percentage-point change for a population mode share."""
    return (scenario - baseline) * 100.0
