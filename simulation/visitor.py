"""Visitor agent: deterministic mode-choice, departure-time, and parking decisions.

Visitors differ from commuters by having group sizes (which amortize driving costs),
shorter stay durations (reducing total parking fees), and a higher walk penalty.
They also have constraints (e.g. YouBike is generally unavailable for groups > 2).
"""

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .baseline import ScenarioConfig
from .commuter import ModeAlternative, _hhmm_to_minutes
from .parking import ParkingFacility, choose_parking
from .roads import RoadSegment
from .ubike import YouBikeStation, is_youbike_trip_available

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VisitorProfile:
    """Static attributes describing a visitor group."""

    visitor_id: str
    origin_segment_id: str
    destination_segment_id: str
    preferred_departure: str  # HH:MM
    group_size: int = 1
    stay_duration_hours: float = 3.0
    flexibility_minutes: int = 30
    value_of_time: float = 4.0        # NTD per minute
    price_sensitivity: float = 1.0
    walk_penalty_multiplier: float = 1.5  # Visitors are less willing to walk far
    transit_preference: float = 0.0   # 0–1 bonus for transit affinity

    def __post_init__(self) -> None:
        if self.group_size < 1:
            raise ValueError("group_size must be at least 1")
        if self.stay_duration_hours <= 0:
            raise ValueError("stay_duration_hours must be positive")
        if self.flexibility_minutes < 0:
            raise ValueError("flexibility_minutes cannot be negative")
        if self.value_of_time < 0:
            raise ValueError("value_of_time cannot be negative")
        if self.walk_penalty_multiplier < 1.0:
            raise ValueError("walk_penalty_multiplier should be >= 1.0")
        if not (0.0 <= self.transit_preference <= 1.0):
            raise ValueError("transit_preference must be between 0 and 1")


@dataclass(frozen=True)
class VisitorDecision:
    """The result of a visitor's deterministic decision process."""

    visitor_id: str
    chosen_mode: str
    departure_time: str          # HH:MM
    generalized_cost: float
    alternatives: Tuple[ModeAlternative, ...]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

YOUBIKE_SPEED_KPH = 15.0
TRANSIT_PREFERENCE_EQUIVALENT_MINUTES = 10.0


class VisitorAgent:
    """Deterministic visitor: chooses mode, departure time, and parking."""

    # -- Generalized cost --------------------------------------------------

    @staticmethod
    def generalized_cost(profile: VisitorProfile, alt: ModeAlternative) -> float:
        """Linear weighted generalized cost in NTD-equivalent.

        For Visitors:
        - Walk time is heavily penalized (walk_penalty_multiplier).
        - Monetary cost for Transit scales with group_size, while Drive cost is amortized
          across the group in real terms, meaning it becomes highly competitive.
        """
        if alt.availability <= 0:
            return float("inf")
        
        # Base time cost (driving/riding) + Penalized walk cost
        time_cost = (alt.travel_time_minutes + alt.walk_time_minutes * profile.walk_penalty_multiplier) * profile.value_of_time
        
        # Monetary cost
        if alt.mode == "transit":
            # Fare is per-person
            money_cost = (alt.monetary_cost * profile.group_size) * profile.price_sensitivity
        else:
            # Parking fee is per-vehicle (total for the group)
            money_cost = alt.monetary_cost * profile.price_sensitivity

        bonus = 0.0
        if alt.mode == "transit":
            bonus = profile.transit_preference * TRANSIT_PREFERENCE_EQUIVALENT_MINUTES * profile.value_of_time
            
        return time_cost + money_cost - bonus

    # -- Mode choice --------------------------------------------------------

    def choose_mode(self, profile: VisitorProfile, alternatives: Iterable[ModeAlternative]) -> ModeAlternative:
        """Pick the alternative with the lowest generalized cost."""
        candidates = list(alternatives)
        if not candidates:
            raise ValueError("At least one mode alternative is required")
        return min(candidates, key=lambda alt: self.generalized_cost(profile, alt))

    # -- Departure time choice ---------------------------------------------

    @staticmethod
    def choose_departure(
        profile: VisitorProfile,
        scenario: ScenarioConfig,
    ) -> str:
        """Pick the tick in [preferred − flex, preferred + flex] with the
        lowest demand, breaking ties by proximity to the preferred time.
        """
        all_ticks = scenario.ticks()
        if not all_ticks:
            raise ValueError("Scenario produces no ticks")

        pref_minutes = _hhmm_to_minutes(profile.preferred_departure)
        flex = profile.flexibility_minutes

        window = []
        for tick in all_ticks:
            tick_minutes = _hhmm_to_minutes(tick)
            if pref_minutes - flex <= tick_minutes <= pref_minutes + flex:
                window.append(tick)

        if not window:
            window = [min(all_ticks, key=lambda t: abs(_hhmm_to_minutes(t) - pref_minutes))]

        demand = scenario.demand_profile

        def sort_key(tick: str) -> tuple:
            d = demand.get(tick, 1.0)
            distance = abs(_hhmm_to_minutes(tick) - pref_minutes)
            return (d, distance)

        return min(window, key=sort_key)

    # -- Build alternatives ------------------------------------------------

    @staticmethod
    def build_alternatives(
        profile: VisitorProfile,
        road: RoadSegment,
        flow_vph: float,
        parking_facilities: Optional[Iterable[ParkingFacility]] = None,
        youbike_station: Optional[YouBikeStation] = None,
        transit_time_minutes: float = 25.0,
        transit_fare: float = 20.0,
        transit_walk_minutes: float = 5.0,
    ) -> List[ModeAlternative]:
        """Assemble mode alternatives from current infrastructure state."""
        alternatives: List[ModeAlternative] = []

        # --- Drive ---
        drive_time = road.travel_time_minutes(flow_vph)
        drive_cost = 0.0
        drive_walk = 0.0
        drive_avail = 1.0
        if parking_facilities is not None:
            facilities = list(parking_facilities)
            if facilities:
                try:
                    # Choose parking considering the stay duration and walk penalty
                    # GC = (fee * duration) + (walk_distance * walk_penalty)
                    def parking_gc(fac: ParkingFacility) -> float:
                        if fac.available_spaces in (None, 0):
                            return float("inf")
                        fee_cost = fac.hourly_fee * profile.stay_duration_hours
                        walk_cost = fac.walk_distance_m * profile.walk_penalty_multiplier
                        return fee_cost + walk_cost

                    valid = [f for f in facilities if f.available_spaces not in (None, 0)]
                    if valid:
                        best = min(valid, key=parking_gc)
                        drive_cost = best.hourly_fee * profile.stay_duration_hours
                        drive_walk = best.walk_distance_m / 80  # ~80 m/min walking speed
                    else:
                        drive_avail = 0.0
                except LookupError:
                    drive_avail = 0.0
        alternatives.append(ModeAlternative(
            mode="drive",
            travel_time_minutes=drive_time,
            monetary_cost=drive_cost,
            walk_time_minutes=drive_walk,
            availability=drive_avail,
        ))

        # --- Transit ---
        alternatives.append(ModeAlternative(
            mode="transit",
            travel_time_minutes=transit_time_minutes,
            monetary_cost=transit_fare,
            walk_time_minutes=transit_walk_minutes,
            availability=1.0,
        ))

        # --- YouBike ---
        if youbike_station is not None:
            bike_time = (road.length_m / 1000) / YOUBIKE_SPEED_KPH * 60  # minutes
            # Larger groups are unlikely to find enough bikes together. Smaller
            # groups must also pass the shared distance and stock-reserve rules.
            bike_avail = float(
                profile.group_size <= 2
                and is_youbike_trip_available(
                    youbike_station,
                    trip_distance_m=road.length_m,
                    riders=profile.group_size,
                )
            )
            alternatives.append(ModeAlternative(
                mode="youbike",
                travel_time_minutes=bike_time,
                monetary_cost=0.0,
                walk_time_minutes=3.0,  # typical walk to station
                availability=bike_avail,
            ))

        return alternatives

    # -- Full single-visitor evaluation -----------------------------------

    def evaluate(
        self,
        profile: VisitorProfile,
        scenario: ScenarioConfig,
        road: RoadSegment,
        flow_vph: float,
        parking_facilities: Optional[Iterable[ParkingFacility]] = None,
        youbike_station: Optional[YouBikeStation] = None,
        transit_time_minutes: float = 25.0,
        transit_fare: float = 20.0,
        transit_walk_minutes: float = 5.0,
    ) -> VisitorDecision:
        """Run the full decision pipeline for one visitor."""
        scenario.validate()
        departure = self.choose_departure(profile, scenario)
        alternatives = self.build_alternatives(
            profile, road, flow_vph,
            parking_facilities=parking_facilities,
            youbike_station=youbike_station,
            transit_time_minutes=transit_time_minutes,
            transit_fare=transit_fare,
            transit_walk_minutes=transit_walk_minutes,
        )
        chosen = self.choose_mode(profile, alternatives)
        return VisitorDecision(
            visitor_id=profile.visitor_id,
            chosen_mode=chosen.mode,
            departure_time=departure,
            generalized_cost=self.generalized_cost(profile, chosen),
            alternatives=tuple(alternatives),
        )

    # -- Batch evaluation --------------------------------------------------

    def run_batch(
        self,
        profiles: Iterable[VisitorProfile],
        scenario: ScenarioConfig,
        road: RoadSegment,
        flow_vph: float,
        parking_facilities: Optional[Iterable[ParkingFacility]] = None,
        youbike_station: Optional[YouBikeStation] = None,
        transit_time_minutes: float = 25.0,
        transit_fare: float = 20.0,
        transit_walk_minutes: float = 5.0,
    ) -> Dict[str, object]:
        """Evaluate a population of visitors and return aggregate statistics."""
        scenario.validate()
        parking_list = list(parking_facilities) if parking_facilities is not None else None

        decisions: List[VisitorDecision] = []
        for profile in profiles:
            decision = self.evaluate(
                profile, scenario, road, flow_vph,
                parking_facilities=parking_list,
                youbike_station=youbike_station,
                transit_time_minutes=transit_time_minutes,
                transit_fare=transit_fare,
                transit_walk_minutes=transit_walk_minutes,
            )
            decisions.append(decision)

        if not decisions:
            raise ValueError("At least one visitor profile is required")

        mode_counts: Dict[str, int] = {}
        total_cost = 0.0
        departure_counts: Dict[str, int] = {}
        for d in decisions:
            mode_counts[d.chosen_mode] = mode_counts.get(d.chosen_mode, 0) + 1
            total_cost += d.generalized_cost
            departure_counts[d.departure_time] = departure_counts.get(d.departure_time, 0) + 1

        n = len(decisions)
        mode_share = {mode: count / n for mode, count in sorted(mode_counts.items())}

        return {
            "scenario": scenario.manifest(),
            "road_name": road.properties.get("name:zh") or road.properties.get("name") or road.segment_id,
            "total_visitors": n,
            "mode_share": mode_share,
            "average_generalized_cost": total_cost / n,
            "departure_distribution": dict(sorted(departure_counts.items())),
            "decisions": decisions,
        }
