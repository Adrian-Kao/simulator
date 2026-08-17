"""A small deterministic policy agent for a terminal demonstration."""

from dataclasses import dataclass
from typing import Dict

from .baseline import ScenarioConfig
from .historical import TypicalDayMetric
from .roads import RoadSegment
from .signals import SignalPhase, SignalPlan


@dataclass(frozen=True)
class PolicyResult:
    policy_name: str
    queue_vehicles: float
    travel_time_minutes: float
    travel_speed_kph: float
    congestion_vc: float


class SimpleTrafficPolicyAgent:
    """Chooses the candidate with the lowest queue, then lowest travel time."""

    def run(self, scenario: ScenarioConfig, road: RoadSegment, arrivals_per_tick: float) -> Dict[str, object]:
        scenario.validate()
        candidates = [
            ("Baseline: 東西向綠燈 40 秒", self._plan(east_west_green=40)),
            ("Policy V1: 東西向綠燈 60 秒", self._plan(east_west_green=60)),
        ]
        results = [self._evaluate(name, plan, road, arrivals_per_tick, scenario.tick_minutes) for name, plan in candidates]
        selected = min(results, key=lambda result: (result.queue_vehicles, result.travel_time_minutes))
        return {
            "scenario": scenario.manifest(),
            "road_name": road.properties.get("name:zh") or road.properties.get("name") or road.segment_id,
            "results": results,
            "recommended": selected,
        }

    def run_historical(self, scenario: ScenarioConfig, road: RoadSegment, baseline: TypicalDayMetric) -> Dict[str, object]:
        """Run a policy comparison from an observed historical typical-day metric."""
        arrivals_per_tick = baseline.traffic_volume_vph * scenario.tick_minutes / 60
        outcome = self.run(scenario, road, arrivals_per_tick)
        outcome["historical_baseline"] = {
            "day_type": baseline.day_type,
            "time_slot": baseline.time_slot,
            "segment_id": baseline.segment_id,
            "observation_count": baseline.observation_count,
            "observed_travel_time_minutes": baseline.travel_time_minutes,
            "observed_travel_speed_kph": baseline.travel_speed_kph,
            "observed_traffic_volume_vph": baseline.traffic_volume_vph,
            "observed_footfall_per_hour": baseline.footfall_per_hour,
            "observed_parking_occupancy_rate": baseline.parking_occupancy_rate,
            "observed_youbike_borrows": baseline.youbike_borrows,
            "observed_youbike_returns": baseline.youbike_returns,
        }
        return outcome

    @staticmethod
    def _plan(east_west_green: int) -> SignalPlan:
        return SignalPlan(
            intersection_id="demo-intersection",
            cycle_seconds=120,
            phases=[
                SignalPhase("north_south", 50, {"north_straight", "south_straight"}),
                SignalPhase("east_west", east_west_green, {"east_straight", "west_straight"}),
            ],
        )

    @staticmethod
    def _evaluate(name: str, plan: SignalPlan, road: RoadSegment, arrivals: float, tick_minutes: int) -> PolicyResult:
        queue = plan.update_queue("east_straight", arrivals=arrivals, queued=0, tick_minutes=tick_minutes)["queue"]
        flow_vph = arrivals * 60 / tick_minutes
        return PolicyResult(
            policy_name=name,
            queue_vehicles=queue,
            travel_time_minutes=road.travel_time_minutes(flow_vph),
            travel_speed_kph=road.travel_speed_kph(flow_vph),
            congestion_vc=flow_vph / road.capacity_vph,
        )
