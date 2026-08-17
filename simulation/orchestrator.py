"""Simulation orchestrator.

    load baseline
        v
    build simulation state
        v
    apply ScenarioDiff
        v
    run road / signal / policy effects
        v
    aggregate KPIs
        v
    return result

Baseline data is taken from the repository's real assets when they are present:

    data/historical/xinyi_historical_observations.csv  (via simulation.historical)
    data/GIS/xinyi_impact_road_network.geojson         (via simulation.roads)

``data/`` is gitignored, so both may be absent on a fresh checkout. In that case
explicitly named ``FALLBACK_*`` defaults are used, every substitution is reported
in ``warnings``, and ``metadata["sources"]`` records exactly which fields came
from real data and which did not. The frontend must never present a fallback as
an observed historical value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .baseline import ScenarioConfig
from .goals import GoalConfig, GoalStatus, evaluate_goals, goals_met
from .historical import TypicalDayMetric, build_typical_day, load_historical_observations
from .policy_effects import (
    Kpi,
    KpiDelta,
    assumptions_manifest,
    build_delta,
    evaluate,
)
from .roads import RoadSegment, load_road_segments
from .scenario import (
    PolicyVariables,
    ScenarioDiff,
    baseline_variables,
    bounds_manifest,
    scenario_variables,
    variable_warnings,
)


# --- Real data locations ---------------------------------------------------

HISTORICAL_OBSERVATIONS_PATH = Path("data/historical/xinyi_historical_observations.csv")
ROAD_NETWORK_PATH = Path("data/GIS/xinyi_impact_road_network.geojson")


# --- Named fallbacks (used only when real data is unavailable) --------------

FALLBACK_SEGMENT_ID = "fallback-xinyi-corridor"
FALLBACK_ROAD_NAME = "信義商圈示範路段"
FALLBACK_ROAD_LENGTH_M = 500.0
FALLBACK_ROAD_LANES = 2
FALLBACK_SPEED_LIMIT_KPH = 40.0
FALLBACK_CAPACITY_VPH = 1_800.0

# Represents a near-capacity weekday evening peak (V/C ~ 1.0 against
# FALLBACK_CAPACITY_VPH). Chosen so the demo operates in the congested regime
# where the BPR curve is actually sensitive; it is a placeholder, not a
# measurement.
FALLBACK_DEMAND_VPH = 1_800.0


# Frontend road id -> historical observation segment candidates.
#
# The first entry is the canonical id emitted by scripts/generate_historical_data.py.
# Later entries are legacy aliases found in older synthetic population/data files.
# We prefer an exact road match and never silently substitute an unrelated Xinyi
# segment when a known road has no matching observation.
ROAD_ID_TO_SEGMENT_CANDIDATES: Dict[str, Tuple[str, ...]] = {
    "shifu-road": (
        "city_hall_road_eastbound",
        "city_hall_road_westbound",
    ),
    "songzhi-road": (
        "songzhi_road_northbound",
        "songzhi_rd_eastbound",
        "songzhi_rd_westbound",
    ),
    "songren-road": (
        "songren_road_northbound",
        "songren_road_southbound",
        "songren_rd_northbound",
        "songren_rd_southbound",
    ),
    "songshou-road": (
        "songshou_road_eastbound",
        "songshou_rd_eastbound",
        "songshou_rd_westbound",
    ),
    "songgao-road": (
        "songgao_road_eastbound",
        "songgao_rd_northbound",
        "songgao_rd_southbound",
    ),
    "zhongxiao-road": (
        "zhongxiao_east_sec5_eastbound",
        "zhongxiao_e_rd_sec5_eastbound",
    ),
}

# Backwards-compatible canonical manifest for callers/tests that need one id.
ROAD_ID_TO_SEGMENT_ID: Dict[str, str] = {
    road_id: candidates[0]
    for road_id, candidates in ROAD_ID_TO_SEGMENT_CANDIDATES.items()
}

# Frontend road id -> OpenStreetMap name used in the GeoJSON network.
ROAD_ID_TO_OSM_NAME: Dict[str, str] = {
    "shifu-road": "市府路",
    "songzhi-road": "松智路",
    "songren-road": "松仁路",
    "songshou-road": "松壽路",
    "songgao-road": "松高路",
    "zhongxiao-road": "忠孝東路五段",
}


def _segment_candidates_for_road(
    road_id: Optional[str],
    road_name: Optional[str],
) -> Optional[Tuple[str, ...]]:
    """Resolve a frontend road to historical ids.

    ``None`` means no road was specified, so a representative segment may be
    used. ``()`` means a road was explicitly specified but no mapping exists;
    that case must fall back rather than borrowing data from an unrelated road.
    """
    if road_id in ROAD_ID_TO_SEGMENT_CANDIDATES:
        return ROAD_ID_TO_SEGMENT_CANDIDATES[road_id]

    if road_name:
        for candidate_road_id, osm_name in ROAD_ID_TO_OSM_NAME.items():
            if osm_name == road_name:
                return ROAD_ID_TO_SEGMENT_CANDIDATES[candidate_road_id]

    if road_id or road_name:
        return ()

    return None


@dataclass(frozen=True)
class BaselineContext:
    """Everything the effect model needs, plus provenance for every field."""

    road: RoadSegment
    demand_vph: float
    tick_minutes: int
    day_type: str
    time_slot: str
    segment_id: str
    observation_count: int
    sources: Dict[str, str] = field(default_factory=dict)
    observed: Dict[str, float] = field(default_factory=dict)
    warnings: Tuple[str, ...] = ()

    @property
    def uses_fallback(self) -> bool:
        return any(value.startswith("fallback") for value in self.sources.values())


@dataclass(frozen=True)
class SimulationOutcome:
    scenario_id: str
    baseline: Kpi
    scenario: Kpi
    delta: KpiDelta
    baseline_variables: PolicyVariables
    scenario_variables: PolicyVariables
    recommended: str
    goal_status: Tuple[GoalStatus, ...]
    goals_met: bool
    warnings: Tuple[str, ...]
    metadata: Dict[str, object]

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "baseline": self.baseline.to_dict(),
            "scenario": self.scenario.to_dict(),
            "delta": self.delta.to_dict(),
            "baseline_variables": self.baseline_variables.to_dict(),
            "scenario_variables": self.scenario_variables.to_dict(),
            "recommended": self.recommended,
            "goal_status": [status.to_dict() for status in self.goal_status],
            "goals_met": self.goals_met,
            "warnings": list(self.warnings),
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Step 1: load baseline
# ---------------------------------------------------------------------------


def _load_historical_metric(
    historical_path: Path,
    day_type: str,
    time_slot: str,
    segment_ids: Optional[Tuple[str, ...]],
) -> Tuple[Optional[TypicalDayMetric], List[str]]:
    warnings: List[str] = []

    if not Path(historical_path).exists():
        warnings.append(
            f"Historical observations not found at {historical_path}; "
            "using FALLBACK_DEMAND_VPH instead of an observed typical day."
        )
        return None, warnings

    try:
        observations = load_historical_observations(historical_path)
        metrics = build_typical_day(
            observations,
            day_type,
            include_events=day_type == "event",
        )
    except (ValueError, KeyError, OSError) as error:
        warnings.append(
            f"Historical observations at {historical_path} could not be used "
            f"({error}); falling back to defaults."
        )
        return None, warnings

    slot_metrics = [metric for metric in metrics if metric.time_slot == time_slot]
    if not slot_metrics:
        warnings.append(
            f"No historical observations for day_type={day_type} time_slot={time_slot}; "
            "falling back to defaults."
        )
        return None, warnings

    if segment_ids == ():
        warnings.append(
            "No historical segment mapping exists for the requested road; "
            "using fallback demand instead of an unrelated representative segment."
        )
        return None, warnings

    if segment_ids:
        for index, segment_id in enumerate(segment_ids):
            exact = next(
                (
                    metric
                    for metric in slot_metrics
                    if metric.segment_id == segment_id
                ),
                None,
            )
            if exact is not None:
                if index > 0:
                    warnings.append(
                        f"Historical segment matched legacy alias {segment_id}; "
                        f"canonical id is {segment_ids[0]}."
                    )
                return exact, warnings

        warnings.append(
            "No historical observations matched the requested road's mapped "
            f"segment ids ({', '.join(segment_ids)}); using fallback demand "
            "instead of an unrelated representative segment."
        )
        return None, warnings

    # No road was requested at all: using a representative segment is explicit.
    return slot_metrics[0], warnings


def _load_road(
    road_network_path: Path,
    road_id: Optional[str],
    road_name: Optional[str],
) -> Tuple[Optional[RoadSegment], List[str]]:
    warnings: List[str] = []

    if not Path(road_network_path).exists():
        warnings.append(
            f"Road network not found at {road_network_path}; using FALLBACK road "
            "geometry (length/lanes/speed limit/capacity are defaults, not survey data)."
        )
        return None, warnings

    try:
        segments = load_road_segments(road_network_path)
    except (ValueError, OSError) as error:
        warnings.append(
            f"Road network at {road_network_path} could not be used ({error}); "
            "using FALLBACK road geometry."
        )
        return None, warnings

    wanted = {
        name
        for name in (road_name, ROAD_ID_TO_OSM_NAME.get(road_id or ""))
        if name
    }

    for segment in segments:
        properties = segment.properties
        candidates = {
            properties.get("name:zh"),
            properties.get("name"),
        }
        if wanted & {value for value in candidates if value}:
            return segment, warnings

    warnings.append(
        f"Road {road_name or road_id or '<unspecified>'} not found in "
        f"{road_network_path}; using FALLBACK road geometry."
    )
    return None, warnings


def load_baseline_context(
    *,
    day_type: str,
    time_slot: str,
    tick_minutes: int = 5,
    road_id: Optional[str] = None,
    road_name: Optional[str] = None,
    historical_path: Path = HISTORICAL_OBSERVATIONS_PATH,
    road_network_path: Path = ROAD_NETWORK_PATH,
) -> BaselineContext:
    warnings: List[str] = []
    sources: Dict[str, str] = {}
    observed: Dict[str, float] = {}

    segment_candidates = _segment_candidates_for_road(
        road_id,
        road_name,
    )
    metric, metric_warnings = _load_historical_metric(
        historical_path,
        day_type,
        time_slot,
        segment_candidates,
    )
    warnings.extend(metric_warnings)

    road, road_warnings = _load_road(road_network_path, road_id, road_name)
    warnings.extend(road_warnings)

    if road is None:
        road = RoadSegment(
            segment_id=road_id or FALLBACK_SEGMENT_ID,
            length_m=FALLBACK_ROAD_LENGTH_M,
            lanes=FALLBACK_ROAD_LANES,
            speed_limit_kph=FALLBACK_SPEED_LIMIT_KPH,
            capacity_vph=FALLBACK_CAPACITY_VPH,
            properties={"name:zh": road_name or FALLBACK_ROAD_NAME},
        )
        sources["road_geometry"] = "fallback-default"
        sources["road_capacity"] = "fallback-default"
    else:
        sources["road_geometry"] = "data/GIS/xinyi_impact_road_network.geojson"
        # roads.py derives capacity from lanes * DEFAULT_CAPACITY_VPH_PER_LANE,
        # which is a default rather than a measured saturation flow.
        sources["road_capacity"] = "derived-default-per-lane"

    if metric is None:
        demand_vph = FALLBACK_DEMAND_VPH
        sources["demand"] = "fallback-default"
        resolved_segment_id = (
            segment_candidates[0]
            if segment_candidates
            else FALLBACK_SEGMENT_ID
        )
        observation_count = 0
    else:
        demand_vph = metric.traffic_volume_vph
        sources["demand"] = "data/historical/xinyi_historical_observations.csv"
        resolved_segment_id = metric.segment_id
        observation_count = metric.observation_count
        observed = {
            "travel_time_minutes": metric.travel_time_minutes,
            "travel_speed_kph": metric.travel_speed_kph,
            "traffic_volume_vph": metric.traffic_volume_vph,
            "parking_occupancy_rate": metric.parking_occupancy_rate,
        }

    return BaselineContext(
        road=road,
        demand_vph=demand_vph,
        tick_minutes=tick_minutes,
        day_type=day_type,
        time_slot=time_slot,
        segment_id=resolved_segment_id,
        observation_count=observation_count,
        sources=sources,
        observed=observed,
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Steps 2-6: build state, apply diff, run effects, aggregate, return
# ---------------------------------------------------------------------------


def run_simulation(
    diff: ScenarioDiff,
    *,
    day_type: str = "weekday",
    time_slot: str = "17:30",
    random_seed: int = 42,
    tick_minutes: int = 5,
    road_id: Optional[str] = None,
    road_name: Optional[str] = None,
    goals: Optional[GoalConfig] = None,
    historical_path: Path = HISTORICAL_OBSERVATIONS_PATH,
    road_network_path: Path = ROAD_NETWORK_PATH,
) -> SimulationOutcome:
    diff.validate()

    scenario_config = ScenarioConfig(
        scenario_id=diff.scenario_id,
        service_date="historical-typical-day",
        tick_minutes=tick_minutes,
        random_seed=random_seed,
        demand_profile={time_slot: 1.0},
    )
    scenario_config.validate()

    context = load_baseline_context(
        day_type=day_type,
        time_slot=time_slot,
        tick_minutes=tick_minutes,
        road_id=road_id or (diff.red_line_policies[0].road_id if diff.red_line_policies else None),
        road_name=road_name,
        historical_path=historical_path,
        road_network_path=road_network_path,
    )

    base_variables = baseline_variables(diff)
    scen_variables = scenario_variables(diff)

    baseline_kpi = evaluate(
        context.road,
        context.demand_vph,
        context.tick_minutes,
        base_variables,
    )
    scenario_kpi = evaluate(
        context.road,
        context.demand_vph,
        context.tick_minutes,
        scen_variables,
    )

    delta = build_delta(baseline_kpi, scenario_kpi)
    statuses = evaluate_goals(delta, goals)
    met = goals_met(delta, goals)

    warnings: List[str] = list(context.warnings)
    warnings.extend(variable_warnings(diff))

    if diff.is_empty():
        warnings.append(
            "ScenarioDiff contains no change versus baseline; scenario KPIs equal "
            "baseline KPIs."
        )

    warnings.append(
        "Policy effects use the MVP proxy model 'mvp-proxy-v1' and are NOT "
        "calibrated against Xinyi field data."
    )

    if scenario_kpi.queue_vehicles < baseline_kpi.queue_vehicles:
        recommended = "scenario"
    elif scenario_kpi.queue_vehicles > baseline_kpi.queue_vehicles:
        recommended = "baseline"
    else:
        recommended = "tie"

    metadata: Dict[str, object] = {
        "scenario_config": scenario_config.manifest(),
        "day_type": context.day_type,
        "time_slot": context.time_slot,
        "tick_minutes": context.tick_minutes,
        "random_seed": random_seed,
        "segment_id": context.segment_id,
        "observation_count": context.observation_count,
        "baseline_demand_vph": context.demand_vph,
        "road": {
            "segment_id": context.road.segment_id,
            "name": context.road.properties.get("name:zh")
            or context.road.properties.get("name"),
            "length_m": context.road.length_m,
            "lanes": context.road.lanes,
            "speed_limit_kph": context.road.speed_limit_kph,
            "capacity_vph": context.road.capacity_vph,
        },
        "sources": context.sources,
        "uses_fallback": context.uses_fallback,
        "observed_baseline": context.observed,
        "assumptions": assumptions_manifest(),
        "bounds": bounds_manifest(),
        "scenario_diff": diff.to_dict(),
    }

    return SimulationOutcome(
        scenario_id=diff.scenario_id,
        baseline=baseline_kpi,
        scenario=scenario_kpi,
        delta=delta,
        baseline_variables=base_variables,
        scenario_variables=scen_variables,
        recommended=recommended,
        goal_status=tuple(statuses),
        goals_met=met,
        warnings=tuple(warnings),
        metadata=metadata,
    )
