import unittest
from pathlib import Path

from simulation.parking import ParkingFacility, choose_parking, load_taipei_parking


class ParkingModelTests(unittest.TestCase):
    def test_choice_uses_available_lowest_generalized_cost(self):
        nearby_full = ParkingFacility("near", 20, 0, hourly_fee=20, walk_distance_m=50)
        available = ParkingFacility("available", 20, 4, hourly_fee=30, walk_distance_m=200)
        self.assertEqual(choose_parking([nearby_full, available], 1, 0.01).facility_id, "available")

    def test_arrivals_and_departures_respect_capacity(self):
        facility = ParkingFacility("p1", 10, 2)
        self.assertEqual(facility.park(5), 2)
        self.assertEqual(facility.available_spaces, 0)
        self.assertEqual(facility.leave(3), 3)
        self.assertEqual(facility.available_spaces, 3)

    def test_taipei_snapshots_merge(self):
        facilities = load_taipei_parking(
            Path("data/parking/taipei_parking_static.json"),
            Path("data/parking/taipei_parking_dynamic.json"),
        )
        self.assertEqual(len(facilities), 1749)
        self.assertTrue(any(facility.available_spaces is not None for facility in facilities))


if __name__ == "__main__":
    unittest.main()
