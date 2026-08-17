"""MVP proxy policy-effect model for the three demo variables.

IMPORTANT HONESTY NOTE
----------------------
The elasticities in this module are **named, documented proxies**, not values
calibrated against Xinyi field data. They exist so the demo loop
(scenario -> simulation -> KPI -> goal -> reasoning -> patch) can run on real
Python simulation code instead of frontend placeholders.

Nothing here may be presented as a validated traffic model. ``DATA_SOURCES.md``
lists the observations still required before calibration can be claimed.

Effect chain
------------
    signal_green_seconds  -> signal capacity            -> queue
    red_line_meters       -> curb friction removed      -> effective road capacity
                                                        -> travel time / speed / V/C
    parking_spaces        -> cruising-for-parking relief -> effective demand
                                                        -> travel time / speed / V/C / queue

The model is analytic and therefore deterministic: identical inputs always
produce identical KPIs. ``random_seed`` is recorded in the response metadata but
does not currently influence the result, because no stochastic process is used.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .roads import RoadSegment
from .scenario import PolicyVariables
from .signals import SignalPhase, SignalPlan


MODEL_NAME = "mvp-proxy-v1"
MODEL_IS_CALIBRATED = False
MODEL_IS_STOCHASTIC = False


# --- Signal (X1) -----------------------------------------------------------

SIGNAL_CYCLE_SECONDS = 120
SIGNAL_CONFLICTING_GREEN_SECONDS = 50
SIGNAL_SATURATION_FLOW_VPH = 1_800.0
PRIMARY_MOVEMENT = "east_straight"
CONFLICTING_MOVEMENT = "north_straight"


# --- Red line (X2) ---------------------------------------------------------

# Removing kerbside stopping recovers part of the nearside lane. 4% effective
# capacity per 100 m of new red line, capped at 20%.
RED_LINE_CAPACITY_GAIN_PER_100_M = 0.04
RED_LINE_MAX_CAPACITY_GAIN = 0.20


# --- Parking (X3) ----------------------------------------------------------

# Each additional space removes a small amount of cruising-for-parking traffic
# from the corridor; removing spaces pushes it back on. Capped as a share of
# baseline demand so the proxy can never invent or erase a whole corridor.
PARKING_CRUISING_RELIEF_VPH_PER_SPACE = 0.6
PARKING_MAX_CRUISING_RELIEF_RATIO = 0.15


# --- Link performance ------------------------------------------------------

BPR_ALPHA = 0.15
BPR_BETA = 4.0


@dataclass(frozen=True)
class Kpi:
    travel_time_minutes: float
    travel_speed_kph: float
    congestion_vc: float
    queue_vehicles: float

    def to_dict(self) -> dict:
        return {
            "travel_time_minutes": self.travel_time_minutes,
            "travel_speed_kph": self.travel_speed_kph,
            "congestion_vc": self.congestion_vc,
            "queue_vehicles": self.queue_vehicles,
        }


@dataclass(frozen=True)
class KpiDelta:
    travel_time_percent: float
    travel_speed_percent: float
    congestion_vc_percent: float
    queue_percent: float

    def to_dict(self) -> dict:
        return {
            "travel_time_percent": self.travel_time_percent,
            "travel_speed_percent": self.travel_speed_percent,
            "congestion_vc_percent": self.congestion_vc_percent,
            "queue_percent": self.queue_percent,
        }


def red_line_capacity_gain(red_line_meters: float) -> float:
    """Fractional effective-capacity gain from new red-line metres."""
    if red_line_meters <= 0:
        return 0.0
    gain = red_line_meters / 100.0 * RED_LINE_CAPACITY_GAIN_PER_100_M
    return min(RED_LINE_MAX_CAPACITY_GAIN, gain)


def effective_road(road: RoadSegment, red_line_meters: float) -> RoadSegment:
    """Apply the red-line curb-friction proxy to a segment's capacity."""
    gain = red_line_capacity_gain(red_line_meters)
    if gain == 0.0:
        return road
    return replace(road, capacity_vph=road.capacity_vph * (1.0 + gain))


def parking_cruising_relief_vph(baseline_demand_vph: float, parking_spaces: int) -> float:
    """Vehicles per hour removed from (or added to) the corridor by parking supply.

    Positive spaces relieve cruising traffic; negative spaces add it back.
    """
    if parking_spaces == 0 or baseline_demand_vph <= 0:
        return 0.0
    cap = baseline_demand_vph * PARKING_MAX_CRUISING_RELIEF_RATIO
    raw = parking_spaces * PARKING_CRUISING_RELIEF_VPH_PER_SPACE
    return max(-cap, min(cap, raw))


def effective_demand_vph(baseline_demand_vph: float, parking_spaces: int) -> float:
    relief = parking_cruising_relief_vph(baseline_demand_vph, parking_spaces)
    return max(0.0, baseline_demand_vph - relief)


def build_signal_plan(green_seconds: int) -> SignalPlan:
    return SignalPlan(
        intersection_id="policy-effect-intersection",
        cycle_seconds=SIGNAL_CYCLE_SECONDS,
        phases=[
            SignalPhase(
                "conflicting",
                SIGNAL_CONFLICTING_GREEN_SECONDS,
                {CONFLICTING_MOVEMENT},
            ),
            SignalPhase(
                "primary",
                int(green_seconds),
                {PRIMARY_MOVEMENT},
            ),
        ],
        saturation_flow_vph=SIGNAL_SATURATION_FLOW_VPH,
    )


def evaluate(
    road: RoadSegment,
    baseline_demand_vph: float,
    tick_minutes: int,
    variables: PolicyVariables,
) -> Kpi:
    """Run the proxy effect chain for one 5-minute tick."""
    if baseline_demand_vph < 0:
        raise ValueError("baseline_demand_vph cannot be negative")
    if tick_minutes <= 0:
        raise ValueError("tick_minutes must be positive")

    adjusted_road = effective_road(road, variables.red_line_meters)
    flow_vph = effective_demand_vph(baseline_demand_vph, variables.parking_spaces)
    arrivals_per_tick = flow_vph * tick_minutes / 60.0

    plan = build_signal_plan(variables.signal_green_seconds)
    queue = plan.update_queue(
        PRIMARY_MOVEMENT,
        arrivals=arrivals_per_tick,
        queued=0,
        tick_minutes=tick_minutes,
    )["queue"]

    travel_time = adjusted_road.travel_time_minutes(
        flow_vph,
        alpha=BPR_ALPHA,
        beta=BPR_BETA,
    )
    travel_speed = adjusted_road.length_m / 1000.0 / (travel_time / 60.0)

    return Kpi(
        travel_time_minutes=travel_time,
        travel_speed_kph=travel_speed,
        congestion_vc=flow_vph / adjusted_road.capacity_vph,
        queue_vehicles=queue,
    )


def percent_change(baseline: float, scenario: float) -> float:
    if abs(baseline) < 1e-9:
        return 0.0
    return (scenario - baseline) / baseline * 100.0


def build_delta(baseline: Kpi, scenario: Kpi) -> KpiDelta:
    return KpiDelta(
        travel_time_percent=percent_change(
            baseline.travel_time_minutes, scenario.travel_time_minutes
        ),
        travel_speed_percent=percent_change(
            baseline.travel_speed_kph, scenario.travel_speed_kph
        ),
        congestion_vc_percent=percent_change(
            baseline.congestion_vc, scenario.congestion_vc
        ),
        queue_percent=percent_change(
            baseline.queue_vehicles, scenario.queue_vehicles
        ),
    )


def assumptions_manifest() -> dict:
    """Machine-readable description of the proxy model, for response metadata."""
    return {
        "model": MODEL_NAME,
        "calibrated": MODEL_IS_CALIBRATED,
        "stochastic": MODEL_IS_STOCHASTIC,
        "signal": {
            "cycle_seconds": SIGNAL_CYCLE_SECONDS,
            "conflicting_green_seconds": SIGNAL_CONFLICTING_GREEN_SECONDS,
            "saturation_flow_vph": SIGNAL_SATURATION_FLOW_VPH,
        },
        "red_line": {
            "capacity_gain_per_100_m": RED_LINE_CAPACITY_GAIN_PER_100_M,
            "max_capacity_gain": RED_LINE_MAX_CAPACITY_GAIN,
        },
        "parking": {
            "cruising_relief_vph_per_space": PARKING_CRUISING_RELIEF_VPH_PER_SPACE,
            "max_cruising_relief_ratio": PARKING_MAX_CRUISING_RELIEF_RATIO,
        },
        "link_performance": {"bpr_alpha": BPR_ALPHA, "bpr_beta": BPR_BETA},
    }
