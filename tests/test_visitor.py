import unittest

from simulation.baseline import ScenarioConfig
from simulation.visitor import (
    VisitorAgent,
    VisitorDecision,
    VisitorProfile,
    ModeAlternative,
)
from simulation.parking import ParkingFacility
from simulation.roads import RoadSegment
from simulation.ubike import YouBikeStation

def _road():
    return RoadSegment("seg1", 500, 2, 40, 1800, {"name": "test road"})

def _scenario():
    return ScenarioConfig(
        "test-visitor", "2026-08-18",
        start_time="10:00", end_time="12:00",
        demand_profile={"10:30": 1.5, "10:35": 1.4, "10:40": 0.6, "10:45": 0.5},
    )

def _profile(**overrides):
    defaults = dict(
        visitor_id="v001",
        origin_segment_id="seg_a",
        destination_segment_id="seg_b",
        preferred_departure="10:40",
    )
    defaults.update(overrides)
    return VisitorProfile(**defaults)

class TestVisitorGeneralizedCost(unittest.TestCase):

    def test_transit_cost_scales_with_group_size(self):
        """Transit cost should be multiplied by group size."""
        agent = VisitorAgent()
        p_single = _profile(group_size=1, value_of_time=5.0, price_sensitivity=1.0)
        p_family = _profile(group_size=4, value_of_time=5.0, price_sensitivity=1.0)
        
        transit = ModeAlternative("transit", travel_time_minutes=20, monetary_cost=20, walk_time_minutes=5)
        # Walk penalty defaults to 1.5
        # Single GC: (20 + 5*1.5)*5.0 + 20*1 = 137.5 + 20 = 157.5
        # Family GC: (20 + 5*1.5)*5.0 + 20*4 = 137.5 + 80 = 217.5
        gc_single = agent.generalized_cost(p_single, transit)
        gc_family = agent.generalized_cost(p_family, transit)
        
        self.assertLess(gc_single, gc_family)
        self.assertEqual(gc_family - gc_single, 60.0)  # 3 extra tickets * 20 NTD

    def test_drive_cost_does_not_scale_with_group_size(self):
        """Driving cost (parking) is per-vehicle, so it doesn't scale with group size."""
        agent = VisitorAgent()
        p_single = _profile(group_size=1)
        p_family = _profile(group_size=4)
        
        drive = ModeAlternative("drive", travel_time_minutes=10, monetary_cost=60, walk_time_minutes=2)
        gc_single = agent.generalized_cost(p_single, drive)
        gc_family = agent.generalized_cost(p_family, drive)
        
        self.assertEqual(gc_single, gc_family)

    def test_high_walk_penalty_discourages_walking(self):
        """A higher walk penalty makes an alternative with walking less attractive."""
        agent = VisitorAgent()
        p_low = _profile(walk_penalty_multiplier=1.0)
        p_high = _profile(walk_penalty_multiplier=3.0)
        
        alt = ModeAlternative("drive", travel_time_minutes=10, monetary_cost=50, walk_time_minutes=10)
        gc_low = agent.generalized_cost(p_low, alt)
        gc_high = agent.generalized_cost(p_high, alt)
        
        self.assertGreater(gc_high, gc_low)

class TestVisitorBuildAlternatives(unittest.TestCase):

    def test_youbike_unavailable_for_large_groups(self):
        """YouBike should be unavailable for group sizes > 2."""
        agent = VisitorAgent()
        p_couple = _profile(group_size=2)
        p_family = _profile(group_size=3)
        road = _road()
        station = YouBikeStation("ub1", capacity=30, bikes=10)
        
        alts_couple = agent.build_alternatives(p_couple, road, flow_vph=500, youbike_station=station)
        alts_family = agent.build_alternatives(p_family, road, flow_vph=500, youbike_station=station)
        
        ub_couple = next(a for a in alts_couple if a.mode == "youbike")
        ub_family = next(a for a in alts_family if a.mode == "youbike")
        
        self.assertEqual(ub_couple.availability, 1.0)
        self.assertEqual(ub_family.availability, 0.0)

    def test_youbike_unavailable_when_group_would_exhaust_reserve(self):
        profile = _profile(group_size=2)
        station = YouBikeStation("ub1", capacity=20, bikes=4)
        alts = VisitorAgent.build_alternatives(
            profile, _road(), flow_vph=500, youbike_station=station,
        )
        youbike = next(a for a in alts if a.mode == "youbike")
        self.assertEqual(youbike.availability, 0.0)

    def test_parking_fee_scales_with_stay_duration(self):
        """The total monetary cost for driving should equal hourly_fee * stay_duration_hours."""
        agent = VisitorAgent()
        p_short = _profile(stay_duration_hours=2.0)
        road = _road()
        parking = [ParkingFacility("p1", capacity=100, available_spaces=50, hourly_fee=60)]
        
        alts = agent.build_alternatives(p_short, road, flow_vph=500, parking_facilities=parking)
        drive = next(a for a in alts if a.mode == "drive")
        
        self.assertEqual(drive.monetary_cost, 120.0)  # 60 * 2.0

class TestVisitorBatchEvaluation(unittest.TestCase):

    def test_mode_share_reasonable(self):
        """Batch evaluation produces varied mode choices for different visitor profiles."""
        agent = VisitorAgent()
        scenario = _scenario()
        road = _road()
        parking = [ParkingFacility("p1", 200, 80, hourly_fee=50, walk_distance_m=100)]
        station = YouBikeStation("ub1", 30, 15)
        profiles = [
            _profile(visitor_id="v_family", group_size=4, stay_duration_hours=2.0, value_of_time=4.0),
            _profile(visitor_id="v_single_transit", group_size=1, stay_duration_hours=4.0, value_of_time=3.0, transit_preference=0.8),
            _profile(visitor_id="v_couple_bike", group_size=2, stay_duration_hours=3.0, value_of_time=6.0, price_sensitivity=2.0),
        ]
        result = agent.run_batch(
            profiles, scenario, road, flow_vph=600,
            parking_facilities=parking, youbike_station=station,
            transit_time_minutes=20.0, transit_fare=25.0, transit_walk_minutes=5.0
        )
        self.assertEqual(result["total_visitors"], 3)
        self.assertIn("mode_share", result)
        self.assertIn("average_generalized_cost", result)

class TestVisitorProfileValidation(unittest.TestCase):
    def test_invalid_group_size(self):
        with self.assertRaises(ValueError):
            _profile(group_size=0)
            
    def test_invalid_stay_duration(self):
        with self.assertRaises(ValueError):
            _profile(stay_duration_hours=-1.0)
            
    def test_invalid_walk_penalty(self):
        with self.assertRaises(ValueError):
            _profile(walk_penalty_multiplier=0.5)

if __name__ == "__main__":
    unittest.main()
