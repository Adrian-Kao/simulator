"""Commuter agent: deterministic mode-choice, departure-time, and parking decisions.

Each commuter evaluates three mode alternatives (drive, transit, YouBike) using
a linear generalized-cost utility function and picks the cheapest option.
Departure-time choice uses a peak-avoidance heuristic within the commuter's
flexibility window.  All decisions are deterministic given the same random seed.
"""

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .baseline import ScenarioConfig
from .historical import TypicalDayMetric
from .parking import ParkingFacility, choose_parking
from .roads import RoadSegment
from .ubike import YouBikeStation


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommuterProfile:
    """Static attributes describing a single commuter."""

    commuter_id: str
    origin_segment_id: str
    destination_segment_id: str
    preferred_departure: str  # HH:MM
    flexibility_minutes: int = 15
    value_of_time: float = 5.0        # NTD per minute
    price_sensitivity: float = 1.0
    transit_preference: float = 0.0   # 0–1 bonus for transit affinity

    def __post_init__(self) -> None:
        if self.flexibility_minutes < 0:
            raise ValueError("flexibility_minutes cannot be negative")
        if self.value_of_time < 0:
            raise ValueError("value_of_time cannot be negative")
        if not (0.0 <= self.transit_preference <= 1.0):
            raise ValueError("transit_preference must be between 0 and 1")


@dataclass(frozen=True)
class ModeAlternative:
    """A single mode-choice candidate evaluated for one OD pair."""

    mode: str                    # "drive" | "transit" | "youbike"
    travel_time_minutes: float
    monetary_cost: float         # NTD
    walk_time_minutes: float = 0.0
    availability: float = 1.0   # 0–1; 0 means unavailable

    def __post_init__(self) -> None:
        if self.travel_time_minutes < 0:
            raise ValueError("travel_time_minutes cannot be negative")
        if self.monetary_cost < 0:
            raise ValueError("monetary_cost cannot be negative")
        if self.walk_time_minutes < 0:
            raise ValueError("walk_time_minutes cannot be negative")
        if not (0.0 <= self.availability <= 1.0):
            raise ValueError("availability must be between 0 and 1")


@dataclass(frozen=True)
class CommuterDecision:
    """The result of a commuter's deterministic decision process."""

    commuter_id: str
    chosen_mode: str
    departure_time: str          # HH:MM
    generalized_cost: float
    alternatives: Tuple[ModeAlternative, ...]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

YOUBIKE_SPEED_KPH = 15.0
TRANSIT_PREFERENCE_EQUIVALENT_MINUTES = 10.0


class CommuterAgent:
    """Deterministic commuter: chooses mode, departure time, and parking."""

    # -- Generalized cost --------------------------------------------------

    @staticmethod
    def generalized_cost(profile: CommuterProfile, alt: ModeAlternative) -> float:
        """Linear weighted generalized cost in NTD-equivalent.

        GC = (travel_time + walk_time) × VOT
             + monetary_cost × price_sensitivity
             − transit_preference × EQUIVALENT_MINUTES × VOT  (transit only)

        Returns ``inf`` when the alternative is unavailable.
        """
        if alt.availability <= 0:
            return float("inf")
        time_cost = (alt.travel_time_minutes + alt.walk_time_minutes) * profile.value_of_time
        money_cost = alt.monetary_cost * profile.price_sensitivity
        bonus = 0.0
        if alt.mode == "transit":
            bonus = profile.transit_preference * TRANSIT_PREFERENCE_EQUIVALENT_MINUTES * profile.value_of_time
        return time_cost + money_cost - bonus

    # -- Mode choice --------------------------------------------------------

    def choose_mode(self, profile: CommuterProfile, alternatives: Iterable[ModeAlternative]) -> ModeAlternative:
        """Pick the alternative with the lowest generalized cost."""
        candidates = list(alternatives)
        if not candidates:
            raise ValueError("At least one mode alternative is required")
        return min(candidates, key=lambda alt: self.generalized_cost(profile, alt))

    # -- Departure time choice ---------------------------------------------

    @staticmethod
    def choose_departure(
        profile: CommuterProfile,
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
            # Fall back to the tick closest to preferred departure.
            window = [min(all_ticks, key=lambda t: abs(_hhmm_to_minutes(t) - pref_minutes))]

        # Demand at each tick (default 1.0 for unlisted ticks).
        demand = scenario.demand_profile

        def sort_key(tick: str) -> tuple:
            d = demand.get(tick, 1.0)
            distance = abs(_hhmm_to_minutes(tick) - pref_minutes)
            return (d, distance)

        return min(window, key=sort_key)

    # -- Build alternatives ------------------------------------------------

    @staticmethod
    def build_alternatives(
        profile: CommuterProfile,
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
                    best = choose_parking(facilities, price_weight=1.0, walk_minutes_per_m=1 / 80)
                    drive_cost = best.hourly_fee
                    drive_walk = best.walk_distance_m / 80  # ~80 m/min walking speed
                    drive_avail = 1.0
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
            bike_avail = min(youbike_station.bikes, 1)  # 0 or 1
            alternatives.append(ModeAlternative(
                mode="youbike",
                travel_time_minutes=bike_time,
                monetary_cost=0.0,
                walk_time_minutes=3.0,  # typical walk to station
                availability=float(bike_avail),
            ))

        return alternatives

    # -- Full single-commuter evaluation -----------------------------------

    def evaluate(
        self,
        profile: CommuterProfile,
        scenario: ScenarioConfig,
        road: RoadSegment,
        flow_vph: float,
        parking_facilities: Optional[Iterable[ParkingFacility]] = None,
        youbike_station: Optional[YouBikeStation] = None,
        transit_time_minutes: float = 25.0,
        transit_fare: float = 20.0,
        transit_walk_minutes: float = 5.0,
    ) -> CommuterDecision:
        """Run the full decision pipeline for one commuter."""
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
        return CommuterDecision(
            commuter_id=profile.commuter_id,
            chosen_mode=chosen.mode,
            departure_time=departure,
            generalized_cost=self.generalized_cost(profile, chosen),
            alternatives=tuple(alternatives),
        )

    # -- Batch evaluation --------------------------------------------------

    def run_batch(
        self,
        profiles: Iterable[CommuterProfile],
        scenario: ScenarioConfig,
        road: RoadSegment,
        flow_vph: float,
        parking_facilities: Optional[Iterable[ParkingFacility]] = None,
        youbike_station: Optional[YouBikeStation] = None,
        transit_time_minutes: float = 25.0,
        transit_fare: float = 20.0,
        transit_walk_minutes: float = 5.0,
    ) -> Dict[str, object]:
        """Evaluate a population of commuters and return aggregate statistics."""
        scenario.validate()
        parking_list = list(parking_facilities) if parking_facilities is not None else None

        decisions: List[CommuterDecision] = []
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
            raise ValueError("At least one commuter profile is required")

        # --- Aggregate statistics ---
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
            "total_commuters": n,
            "mode_share": mode_share,
            "average_generalized_cost": total_cost / n,
            "departure_distribution": dict(sorted(departure_counts.items())),
            "decisions": decisions,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hhmm_to_minutes(hhmm: str) -> int:
    """Convert ``'HH:MM'`` to minutes since midnight."""
    parts = hhmm.split(":")
    return int(parts[0]) * 60 + int(parts[1])
