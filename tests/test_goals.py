import unittest

from simulation.goals import (
    GoalConfig,
    evaluate_goals,
    goal_status,
    goals_met,
    worst_gap,
)
from simulation.policy_effects import KpiDelta


def delta(travel_time=0.0, travel_speed=0.0, vc=0.0, queue=0.0) -> KpiDelta:
    return KpiDelta(
        travel_time_percent=travel_time,
        travel_speed_percent=travel_speed,
        congestion_vc_percent=vc,
        queue_percent=queue,
    )


class GoalConfigTests(unittest.TestCase):
    def test_empty_config(self):
        self.assertTrue(GoalConfig().is_empty())
        self.assertEqual(GoalConfig().items(), [])

    def test_only_set_metrics_are_returned(self):
        goals = GoalConfig(travel_time_percent=-10, queue_percent=-15)
        self.assertEqual(
            goals.items(),
            [("travel_time_percent", -10.0), ("queue_percent", -15.0)],
        )
        self.assertEqual(
            goals.to_dict(),
            {"travel_time_percent": -10.0, "queue_percent": -15.0},
        )


class GoalStatusTests(unittest.TestCase):
    def test_decrease_goal_not_yet_met_reports_gap(self):
        status = goal_status("travel_time_percent", -10.0, -9.4)

        self.assertEqual(status.direction, "decrease")
        self.assertAlmostEqual(status.target_percent, -10.0)
        self.assertAlmostEqual(status.current_percent, -9.4)
        self.assertAlmostEqual(status.gap_percent, 0.6)
        self.assertFalse(status.met)

    def test_decrease_goal_met_has_zero_gap(self):
        status = goal_status("queue_percent", -15.0, -22.0)
        self.assertAlmostEqual(status.gap_percent, 0.0)
        self.assertTrue(status.met)

    def test_exactly_on_target_is_met(self):
        self.assertTrue(goal_status("travel_time_percent", -10.0, -10.0).met)

    def test_increase_goal(self):
        not_met = goal_status("travel_speed_percent", 8.0, 5.0)
        self.assertEqual(not_met.direction, "increase")
        self.assertAlmostEqual(not_met.gap_percent, 3.0)
        self.assertFalse(not_met.met)

        met = goal_status("travel_speed_percent", 8.0, 11.0)
        self.assertAlmostEqual(met.gap_percent, 0.0)
        self.assertTrue(met.met)

    def test_wrong_direction_movement_is_not_met(self):
        status = goal_status("travel_time_percent", -10.0, 4.0)
        self.assertAlmostEqual(status.gap_percent, 14.0)
        self.assertFalse(status.met)

    def test_unknown_metric_rejected(self):
        with self.assertRaises(ValueError):
            goal_status("unknown_percent", -10.0, -10.0)


class EvaluateGoalsTests(unittest.TestCase):
    def test_evaluates_only_configured_metrics(self):
        statuses = evaluate_goals(
            delta(travel_time=-12.0, queue=-20.0),
            GoalConfig(travel_time_percent=-10, queue_percent=-15),
        )
        self.assertEqual([status.metric for status in statuses],
                         ["travel_time_percent", "queue_percent"])
        self.assertTrue(all(status.met for status in statuses))

    def test_no_goals_means_no_statuses_and_not_met(self):
        self.assertEqual(evaluate_goals(delta(), None), [])
        self.assertFalse(goals_met(delta(), None))
        self.assertFalse(goals_met(delta(), GoalConfig()))

    def test_goals_met_requires_every_goal(self):
        goals = GoalConfig(travel_time_percent=-10, queue_percent=-15)
        self.assertFalse(goals_met(delta(travel_time=-11.0, queue=-2.0), goals))
        self.assertTrue(goals_met(delta(travel_time=-11.0, queue=-16.0), goals))

    def test_accepts_mapping_delta(self):
        statuses = evaluate_goals(
            {"travel_time_percent": -11.0},
            GoalConfig(travel_time_percent=-10),
        )
        self.assertTrue(statuses[0].met)

    def test_missing_metric_in_mapping_raises(self):
        with self.assertRaises(KeyError):
            evaluate_goals({}, GoalConfig(travel_time_percent=-10))

    def test_worst_gap_picks_largest_shortfall(self):
        statuses = evaluate_goals(
            delta(travel_time=-1.0, queue=-14.0),
            GoalConfig(travel_time_percent=-10, queue_percent=-15),
        )
        worst = worst_gap(statuses)
        self.assertIsNotNone(worst)
        self.assertEqual(worst.metric, "travel_time_percent")

    def test_worst_gap_is_none_when_all_met(self):
        statuses = evaluate_goals(
            delta(travel_time=-11.0),
            GoalConfig(travel_time_percent=-10),
        )
        self.assertIsNone(worst_gap(statuses))


if __name__ == "__main__":
    unittest.main()
