import unittest

from simulation.agent import SimpleTrafficPolicyAgent
from simulation.baseline import ScenarioConfig
from simulation.roads import RoadSegment


class PolicyAgentTests(unittest.TestCase):
    def test_agent_recommends_more_green_for_oversaturated_movement(self):
        road = RoadSegment("road", 500, 1, 40, 900, {"name": "test road"})
        scenario = ScenarioConfig("test", "2026-08-17")
        outcome = SimpleTrafficPolicyAgent().run(scenario, road, arrivals_per_tick=80)
        self.assertEqual(outcome["recommended"].policy_name, "Policy V1: 東西向綠燈 60 秒")
        self.assertLess(outcome["recommended"].queue_vehicles, outcome["results"][0].queue_vehicles)


if __name__ == "__main__":
    unittest.main()
