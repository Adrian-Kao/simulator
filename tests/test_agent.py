import unittest

from simulation.agent import SimpleTrafficPolicyAgent
from simulation.baseline import ScenarioConfig
from simulation.historical import TypicalDayMetric
from simulation.roads import RoadSegment


class PolicyAgentTests(unittest.TestCase):
    def test_agent_recommends_more_green_for_oversaturated_movement(self):
        road = RoadSegment("road", 500, 1, 40, 900, {"name": "test road"})
        scenario = ScenarioConfig("test", "2026-08-17")
        outcome = SimpleTrafficPolicyAgent().run(scenario, road, arrivals_per_tick=80)
        self.assertEqual(outcome["recommended"].policy_name, "Policy V1: 東西向綠燈 60 秒")
        self.assertLess(outcome["recommended"].queue_vehicles, outcome["results"][0].queue_vehicles)

    def test_agent_uses_historical_volume_as_demand(self):
        road = RoadSegment("road", 500, 1, 40, 900, {"name": "test road"})
        metric = TypicalDayMetric("weekday", "17:30", "city-hall", 5, 8, 15, 960, 5000, .8, 30, 20)
        outcome = SimpleTrafficPolicyAgent().run_historical(ScenarioConfig("test", "2026-08-17"), road, metric)
        self.assertEqual(outcome["historical_baseline"]["observed_traffic_volume_vph"], 960)
        self.assertEqual(outcome["results"][0].congestion_vc, 960 / 900)


if __name__ == "__main__":
    unittest.main()
