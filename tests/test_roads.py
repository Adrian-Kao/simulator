import unittest
from pathlib import Path

from simulation.roads import RoadSegment, calibrate_free_flow_speed, load_road_segments


class RoadModelTests(unittest.TestCase):
    def test_bpr_travel_time_increases_with_flow(self):
        segment = RoadSegment("test", 1_000, 1, 50, 900, {})
        self.assertGreater(segment.travel_time_minutes(1_800), segment.travel_time_minutes(0))
        self.assertLess(segment.travel_speed_kph(1_800), 50)

    def test_calibration_uses_observed_free_flow_speed(self):
        segment = RoadSegment("test", 500, 1, 30, 900, {})
        calibrated = calibrate_free_flow_speed(segment, [40, 44, 42])
        self.assertEqual(calibrated.speed_limit_kph, 42)

    def test_xinyi_geojson_loads(self):
        path = Path("data/GIS/xinyi_impact_road_network.geojson")
        roads = load_road_segments(path)
        self.assertGreater(len(roads), 2_000)
        self.assertTrue(all(road.length_m > 0 for road in roads))


if __name__ == "__main__":
    unittest.main()
