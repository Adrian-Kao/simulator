import unittest

from simulation.signals import SignalPhase, SignalPlan


class SignalModelTests(unittest.TestCase):
    def setUp(self):
        self.plan = SignalPlan(
            "xinyi-songren",
            cycle_seconds=120,
            phases=[
                SignalPhase("north_south", 50, {"north_straight", "south_straight"}),
                SignalPhase("east_west", 40, {"east_straight", "west_straight", "north_right"}),
            ],
            prohibited_movements={"17:30": {"north_right"}},
        )

    def test_green_time_changes_effective_capacity(self):
        self.assertEqual(self.plan.effective_capacity_vph("north_straight"), 750)
        self.assertEqual(self.plan.effective_capacity_vph("east_straight"), 600)

    def test_time_based_turn_restriction_blocks_movement(self):
        self.assertEqual(self.plan.effective_capacity_vph("north_right", "17:30"), 0)
        self.assertGreater(self.plan.effective_capacity_vph("north_right", "17:35"), 0)

    def test_queue_update_respects_capacity(self):
        result = self.plan.update_queue("east_straight", arrivals=100, queued=20, tick_minutes=5)
        self.assertEqual(result["departures"], 50)
        self.assertEqual(result["queue"], 70)


if __name__ == "__main__":
    unittest.main()
