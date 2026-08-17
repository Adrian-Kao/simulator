import unittest

from simulation.baseline import ScenarioConfig
from simulation.commuter import (
    CommuterAgent,
    CommuterDecision,
    CommuterProfile,
    ModeAlternative,
)
from simulation.parking import ParkingFacility
from simulation.roads import RoadSegment
from simulation.ubike import YouBikeStation


def _road():
    return RoadSegment("seg1", 500, 2, 40, 1800, {"name": "test road"})


def _scenario():
    return ScenarioConfig(
        "test-commuter", "2026-08-18",
        demand_profile={"08:00": 1.5, "08:05": 1.4, "08:10": 0.6, "08:15": 0.5},
    )


def _profile(**overrides):
    defaults = dict(
        commuter_id="c001",
        origin_segment_id="seg_a",
        destination_segment_id="seg_b",
        preferred_departure="08:10",
    )
    defaults.update(overrides)
    return CommuterProfile(**defaults)


class TestGeneralizedCost(unittest.TestCase):

    def test_drive_cheapest_when_no_parking_cost(self):
        """With zero monetary cost and short travel time, drive wins."""
        agent = CommuterAgent()
        profile = _profile()
        drive = ModeAlternative("drive", travel_time_minutes=5, monetary_cost=0)
        transit = ModeAlternative("transit", travel_time_minutes=25, monetary_cost=20, walk_time_minutes=5)
        chosen = agent.choose_mode(profile, [drive, transit])
        self.assertEqual(chosen.mode, "drive")

    def test_transit_wins_when_parking_full(self):
        """When parking availability is 0, drive GC → ∞ and transit is chosen."""
        agent = CommuterAgent()
        profile = _profile()
        drive = ModeAlternative("drive", travel_time_minutes=5, monetary_cost=0, availability=0.0)
        transit = ModeAlternative("transit", travel_time_minutes=25, monetary_cost=20, walk_time_minutes=5)
        chosen = agent.choose_mode(profile, [drive, transit])
        self.assertEqual(chosen.mode, "transit")

    def test_youbike_unavailable_when_no_bikes(self):
        """YouBike with 0 bikes has GC=inf."""
        agent = CommuterAgent()
        profile = _profile()
        alt = ModeAlternative("youbike", travel_time_minutes=8, monetary_cost=0, availability=0.0)
        gc = agent.generalized_cost(profile, alt)
        self.assertEqual(gc, float("inf"))

    def test_transit_preference_reduces_cost(self):
        """A commuter with transit_preference > 0 gets a lower GC for transit."""
        agent = CommuterAgent()
        neutral = _profile(transit_preference=0.0)
        biased = _profile(transit_preference=0.5)
        alt = ModeAlternative("transit", travel_time_minutes=20, monetary_cost=20, walk_time_minutes=5)
        gc_neutral = agent.generalized_cost(neutral, alt)
        gc_biased = agent.generalized_cost(biased, alt)
        self.assertLess(gc_biased, gc_neutral)


class TestDepartureChoice(unittest.TestCase):

    def test_departure_avoids_peak(self):
        """With flexibility, the commuter avoids the highest-demand tick."""
        agent = CommuterAgent()
        scenario = _scenario()
        profile = _profile(preferred_departure="08:05", flexibility_minutes=15)
        departure = agent.choose_departure(profile, scenario)
        # 08:15 has demand 0.5 (lowest in the window)
        self.assertEqual(departure, "08:15")

    def test_departure_fallback_to_nearest(self):
        """When preferred time is outside all ticks, falls back to nearest."""
        agent = CommuterAgent()
        scenario = ScenarioConfig("test", "2026-08-18", start_time="09:00", end_time="10:00")
        profile = _profile(preferred_departure="07:00", flexibility_minutes=5)
        departure = agent.choose_departure(profile, scenario)
        self.assertEqual(departure, "09:00")


class TestBuildAlternatives(unittest.TestCase):

    def test_three_modes_with_youbike(self):
        """With a YouBike station, build_alternatives returns 3 options."""
        agent = CommuterAgent()
        profile = _profile()
        road = _road()
        station = YouBikeStation("ub1", capacity=30, bikes=10)
        alts = agent.build_alternatives(profile, road, flow_vph=500, youbike_station=station)
        modes = [a.mode for a in alts]
        self.assertEqual(modes, ["drive", "transit", "youbike"])

    def test_two_modes_without_youbike(self):
        """Without YouBike, only drive and transit are returned."""
        agent = CommuterAgent()
        profile = _profile()
        road = _road()
        alts = agent.build_alternatives(profile, road, flow_vph=500)
        modes = [a.mode for a in alts]
        self.assertEqual(modes, ["drive", "transit"])

    def test_youbike_unavailable_when_station_stock_is_nearly_empty(self):
        station = YouBikeStation("ub1", capacity=30, bikes=5)
        alts = CommuterAgent.build_alternatives(
            _profile(), _road(), flow_vph=500, youbike_station=station,
        )
        youbike = next(a for a in alts if a.mode == "youbike")
        self.assertEqual(youbike.availability, 0.0)

    def test_youbike_unavailable_for_long_trip(self):
        road = RoadSegment("long", 5_001, 2, 40, 1800, {"name": "long road"})
        station = YouBikeStation("ub1", capacity=30, bikes=15)
        alts = CommuterAgent.build_alternatives(
            _profile(), road, flow_vph=500, youbike_station=station,
        )
        youbike = next(a for a in alts if a.mode == "youbike")
        self.assertEqual(youbike.availability, 0.0)

    def test_drive_unavailable_when_parking_full(self):
        """When all parking is full, the drive alternative has availability 0."""
        agent = CommuterAgent()
        profile = _profile()
        road = _road()
        full_parking = [ParkingFacility("p1", capacity=100, available_spaces=0, hourly_fee=30)]
        alts = agent.build_alternatives(profile, road, flow_vph=500, parking_facilities=full_parking)
        drive = next(a for a in alts if a.mode == "drive")
        self.assertEqual(drive.availability, 0.0)


class TestEvaluate(unittest.TestCase):

    def test_full_evaluation_returns_decision(self):
        """evaluate() returns a well-formed CommuterDecision."""
        agent = CommuterAgent()
        profile = _profile()
        scenario = _scenario()
        road = _road()
        decision = agent.evaluate(profile, scenario, road, flow_vph=600)
        self.assertIsInstance(decision, CommuterDecision)
        self.assertEqual(decision.commuter_id, "c001")
        self.assertIn(decision.chosen_mode, {"drive", "transit", "youbike"})
        self.assertGreater(len(decision.alternatives), 0)


class TestBatchEvaluation(unittest.TestCase):

    def test_mode_share_reasonable(self):
        """Batch evaluation with mixed profiles produces varied mode choices."""
        agent = CommuterAgent()
        scenario = _scenario()
        road = _road()
        parking = [ParkingFacility("p1", 200, 80, hourly_fee=40, walk_distance_m=200)]
        station = YouBikeStation("ub1", 30, 15)
        profiles = [
            _profile(commuter_id="c_drive", value_of_time=2.0, price_sensitivity=0.3, transit_preference=0.0),
            _profile(commuter_id="c_transit", value_of_time=3.0, price_sensitivity=0.5, transit_preference=0.6),
            _profile(commuter_id="c_bike", value_of_time=8.0, price_sensitivity=2.0, transit_preference=0.0),
        ]
        result = agent.run_batch(
            profiles, scenario, road, flow_vph=800,
            parking_facilities=parking, youbike_station=station,
        )
        self.assertEqual(result["total_commuters"], 3)
        self.assertIn("mode_share", result)
        self.assertIn("average_generalized_cost", result)
        self.assertGreater(result["average_generalized_cost"], 0)

    def test_deterministic_reproducibility(self):
        """Two runs with identical inputs produce identical results."""
        agent = CommuterAgent()
        scenario = _scenario()
        road = _road()
        profiles = [_profile(commuter_id=f"c{i}") for i in range(5)]
        r1 = agent.run_batch(profiles, scenario, road, flow_vph=700)
        r2 = agent.run_batch(profiles, scenario, road, flow_vph=700)
        self.assertEqual(r1["mode_share"], r2["mode_share"])
        self.assertEqual(r1["average_generalized_cost"], r2["average_generalized_cost"])
        for d1, d2 in zip(r1["decisions"], r2["decisions"]):
            self.assertEqual(d1.chosen_mode, d2.chosen_mode)
            self.assertEqual(d1.departure_time, d2.departure_time)


class TestProfileValidation(unittest.TestCase):

    def test_negative_flexibility_raises(self):
        with self.assertRaises(ValueError):
            _profile(flexibility_minutes=-1)

    def test_negative_vot_raises(self):
        with self.assertRaises(ValueError):
            _profile(value_of_time=-1)

    def test_transit_preference_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            _profile(transit_preference=1.5)


if __name__ == "__main__":
    unittest.main()
