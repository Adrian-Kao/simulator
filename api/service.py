from __future__ import annotations

from typing import Iterable

from simulation.baseline import ScenarioConfig
from simulation.roads import RoadSegment
from simulation.signals import SignalPhase, SignalPlan

from .schemas import (
    PolicyPayload,
    SimulationDelta,
    SimulationKpi,
    SimulationRequest,
    SimulationResponse,
)


BASELINE_GREEN_SECONDS = 40
DEFAULT_SCENARIO_GREEN_SECONDS = 60
MIN_SCENARIO_GREEN_SECONDS = 1
MAX_SCENARIO_GREEN_SECONDS = 68
ARRIVALS_PER_TICK = 120.0


def run_frontend_simulation(request: SimulationRequest) -> SimulationResponse:
    scenario_config = ScenarioConfig(
        scenario_id=request.scenario_id,
        service_date="frontend-simulation",
        random_seed=request.random_seed,
        demand_profile={request.time_slot: 1.0},
    )
    scenario_config.validate()

    road = RoadSegment(
        segment_id=request.road_id or "frontend-demo",
        length_m=500.0,
        lanes=2,
        speed_limit_kph=40.0,
        capacity_vph=1_800.0,
        properties={
            "name:zh": request.road_name or "信義商圈示範路段",
        },
    )

    scenario_green = _signal_green_seconds(request.policies)

    baseline = _evaluate(
        road=road,
        green_seconds=BASELINE_GREEN_SECONDS,
        arrivals_per_tick=ARRIVALS_PER_TICK,
        tick_minutes=scenario_config.tick_minutes,
    )

    scenario = _evaluate(
        road=road,
        green_seconds=scenario_green,
        arrivals_per_tick=ARRIVALS_PER_TICK,
        tick_minutes=scenario_config.tick_minutes,
    )

    delta = SimulationDelta(
        travel_time_percent=_percent_change(
            baseline.travel_time_minutes,
            scenario.travel_time_minutes,
        ),
        travel_speed_percent=_percent_change(
            baseline.travel_speed_kph,
            scenario.travel_speed_kph,
        ),
        congestion_vc_percent=_percent_change(
            baseline.congestion_vc,
            scenario.congestion_vc,
        ),
        queue_percent=_percent_change(
            baseline.queue_vehicles,
            scenario.queue_vehicles,
        ),
    )

    warnings = _warnings(request.policies)

    if scenario.queue_vehicles < baseline.queue_vehicles:
        recommended = "scenario"
    elif scenario.queue_vehicles > baseline.queue_vehicles:
        recommended = "baseline"
    else:
        recommended = "tie"

    return SimulationResponse(
        scenario_id=request.scenario_id,
        baseline=baseline,
        scenario=scenario,
        delta=delta,
        recommended=recommended,
        warnings=warnings,
    )


def _signal_green_seconds(policies: Iterable[PolicyPayload]) -> int:
    for policy in policies:
        if policy.type != "signal-timing" or not policy.phases:
            continue

        for phase in policy.phases:
            if phase.color == "green":
                return max(
                    MIN_SCENARIO_GREEN_SECONDS,
                    min(MAX_SCENARIO_GREEN_SECONDS, int(phase.seconds)),
                )

    return DEFAULT_SCENARIO_GREEN_SECONDS


def _evaluate(
    road: RoadSegment,
    green_seconds: int,
    arrivals_per_tick: float,
    tick_minutes: int,
) -> SimulationKpi:
    plan = SignalPlan(
        intersection_id="frontend-demo-intersection",
        cycle_seconds=120,
        phases=[
            SignalPhase(
                "north_south",
                50,
                {"north_straight", "south_straight"},
            ),
            SignalPhase(
                "east_west",
                green_seconds,
                {"east_straight", "west_straight"},
            ),
        ],
    )

    queue = plan.update_queue(
        "east_straight",
        arrivals=arrivals_per_tick,
        queued=0,
        tick_minutes=tick_minutes,
    )["queue"]

    flow_vph = arrivals_per_tick * 60 / tick_minutes

    return SimulationKpi(
        travel_time_minutes=road.travel_time_minutes(flow_vph),
        travel_speed_kph=road.travel_speed_kph(flow_vph),
        congestion_vc=flow_vph / road.capacity_vph,
        queue_vehicles=queue,
    )


def _percent_change(baseline: float, scenario: float) -> float:
    if abs(baseline) < 1e-9:
        return 0.0
    return (scenario - baseline) / baseline * 100.0


def _warnings(policies: Iterable[PolicyPayload]) -> list[str]:
    warnings: list[str] = []

    if any(policy.type == "red-line" for policy in policies):
        warnings.append(
            "Red-line policy received, but curb-capacity impact is not calibrated yet."
        )

    if any(policy.type == "parking" for policy in policies):
        warnings.append(
            "Parking policy received, but parking-behavior impact is not calibrated yet."
        )

    if any(policy.type == "traffic-restriction" for policy in policies):
        warnings.append(
            "Traffic restriction received, but route-choice impact is not calibrated yet."
        )

    return warnings
