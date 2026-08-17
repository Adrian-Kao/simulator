"""Optimisation-loop tests.

These never touch the Gemini API: a scripted recommender stands in for it, which
is also how the loop guarantees the LLM can only move the three bounded
variables.
"""

import unittest
from pathlib import Path

from api.gemini_service import (
    GeminiRecommendation,
    GeminiServiceError,
    GeminiUnavailableError,
)
from api.optimizer_service import (
    STATUS_AI_ERROR,
    STATUS_AI_UNAVAILABLE,
    STATUS_GOAL_REACHED,
    STATUS_MAX_ITERATIONS,
    run_optimization,
)
from simulation.goals import GoalConfig
from simulation.scenario import (
    PARKING_SPACES_BOUNDS,
    SIGNAL_GREEN_SECONDS_BOUNDS,
    ParkingPolicy,
    RedLinePolicy,
    ScenarioDiff,
    SignalTimingPolicy,
)


# Point the orchestrator at paths that cannot exist so every test uses the
# documented fallback baseline and stays deterministic.
MISSING_HISTORICAL = Path("tests/does-not-exist/historical.csv")
MISSING_ROADS = Path("tests/does-not-exist/roads.geojson")


def initial_diff() -> ScenarioDiff:
    return ScenarioDiff(
        scenario_id="scenario-a",
        policies=(
            SignalTimingPolicy("i-7", baseline_seconds=40, scenario_seconds=45),
            RedLinePolicy("shifu-road", length_meters=100.0),
            ParkingPolicy("parking-new-1", spaces=20),
        ),
    )


class ScriptedRecommender:
    """Returns a fixed sequence of recommendations and records the prompts."""

    def __init__(self, recommendations):
        self.recommendations = list(recommendations)
        self.calls = []

    def __call__(self, scenario, result, goals):
        self.calls.append((scenario, result, goals))
        if not self.recommendations:
            raise AssertionError("Recommender called more times than scripted")
        return self.recommendations.pop(0)


def optimize(goals, recommender, max_iterations=5):
    return run_optimization(
        initial_diff(),
        goals,
        day_type="weekday",
        time_slot="17:30",
        random_seed=42,
        road_id="shifu-road",
        road_name="市府路",
        max_iterations=max_iterations,
        recommender=recommender,
        historical_path=MISSING_HISTORICAL,
        road_network_path=MISSING_ROADS,
    )


class OptimizationLoopTests(unittest.TestCase):
    def test_scenario_is_patched_and_resimulated_each_round(self):
        recommender = ScriptedRecommender(
            [
                GeminiRecommendation(50, 120.0, 80, "iteration 1 reasoning"),
                GeminiRecommendation(55, 150.0, 70, "iteration 2 reasoning"),
            ]
        )

        # A queue target that one round of patching cannot reach, so the loop
        # must actually iterate.
        run = optimize(GoalConfig(queue_percent=-80), recommender, max_iterations=3)

        self.assertEqual(len(run.iterations), 3)
        self.assertEqual(len(recommender.calls), 2)

        first, second, third = run.iterations

        # Iteration 1 = the scenario the user built.
        self.assertEqual(first.scenario["policies"][0]["scenario_seconds"], 45)
        self.assertEqual(first.reasoning, "iteration 1 reasoning")
        self.assertEqual(
            first.recommendation,
            {
                "signal_green_seconds": 50,
                "red_line_meters": 120.0,
                "parking_spaces": 80,
            },
        )

        # Iteration 2 must be the validated patch from iteration 1.
        self.assertEqual(second.scenario["policies"][0]["scenario_seconds"], 50)
        self.assertEqual(second.scenario["policies"][1]["length_meters"], 120.0)
        self.assertEqual(second.scenario["policies"][2]["spaces"], 80)

        self.assertEqual(third.scenario["policies"][0]["scenario_seconds"], 55)
        self.assertEqual(third.scenario["policies"][1]["length_meters"], 150.0)
        self.assertEqual(third.scenario["policies"][2]["spaces"], 70)

        # Every round produced its own KPIs, and the last iteration was not
        # given a reasoning because no further patch followed it.
        self.assertIsNone(third.reasoning)
        self.assertNotEqual(
            first.result["scenario"]["queue_vehicles"],
            second.result["scenario"]["queue_vehicles"],
        )

    def test_anchors_are_never_retargeted_by_a_patch(self):
        recommender = ScriptedRecommender(
            [GeminiRecommendation(68, 400.0, 250, "push everything")]
        )
        run = optimize(GoalConfig(queue_percent=-95), recommender, max_iterations=2)

        second = run.iterations[1].scenario["policies"]
        self.assertEqual(second[0]["intersection_id"], "i-7")
        self.assertEqual(second[1]["road_id"], "shifu-road")
        self.assertEqual(second[2]["parking_id"], "parking-new-1")

    def test_stops_as_soon_as_goals_are_met(self):
        recommender = ScriptedRecommender(
            [GeminiRecommendation(68, 400.0, 300, "maximise everything")]
        )

        run = optimize(GoalConfig(queue_percent=-30), recommender, max_iterations=5)

        self.assertEqual(run.status, STATUS_GOAL_REACHED)
        self.assertEqual(len(run.iterations), 2)
        self.assertTrue(run.iterations[-1].goals_met)
        # Only one patch was needed, so only one reasoning call happened.
        self.assertEqual(len(recommender.calls), 1)

    def test_stops_at_max_iterations(self):
        recommender = ScriptedRecommender(
            [
                GeminiRecommendation(41, 1.0, 1, "tiny nudge"),
                GeminiRecommendation(42, 2.0, 2, "tiny nudge"),
                GeminiRecommendation(43, 3.0, 3, "tiny nudge"),
            ]
        )

        run = optimize(
            GoalConfig(travel_time_percent=-90), recommender, max_iterations=4
        )

        self.assertEqual(run.status, STATUS_MAX_ITERATIONS)
        self.assertEqual(len(run.iterations), 4)
        self.assertFalse(run.iterations[-1].goals_met)
        self.assertIn("max_iterations", run.message or "")

    def test_unreachable_goal_never_fakes_success(self):
        recommender = ScriptedRecommender(
            [GeminiRecommendation(68, 500.0, 300, "maximum effort")] * 4
        )
        run = optimize(
            GoalConfig(travel_time_percent=-99), recommender, max_iterations=3
        )

        self.assertEqual(run.status, STATUS_MAX_ITERATIONS)
        self.assertFalse(any(item.goals_met for item in run.iterations))


class RecommendationSafetyTests(unittest.TestCase):
    def test_out_of_bounds_recommendation_is_clamped_before_simulating(self):
        recommender = ScriptedRecommender(
            [GeminiRecommendation(999, 99_999.0, 99_999, "ignore the bounds")]
        )

        run = optimize(GoalConfig(queue_percent=-99), recommender, max_iterations=2)

        patched = run.iterations[1].scenario["policies"]
        self.assertEqual(patched[0]["scenario_seconds"], SIGNAL_GREEN_SECONDS_BOUNDS[1])
        self.assertEqual(patched[2]["spaces"], PARKING_SPACES_BOUNDS[1])
        self.assertTrue(run.iterations[0].validation_notes)

    def test_unknown_fields_from_the_model_are_discarded(self):
        class Rogue:
            signal_green_seconds = 50
            red_line_meters = 100.0
            parking_spaces = 40
            reasoning = "trying to set capacity directly"
            capacity_vph = 99_999
            travel_time_minutes = 0.01

        recommender = ScriptedRecommender([Rogue()])
        run = optimize(GoalConfig(queue_percent=-99), recommender, max_iterations=2)

        patched = run.iterations[1].scenario["policies"]
        self.assertEqual(patched[0]["scenario_seconds"], 50)
        # capacity_vph must not have leaked into the road model.
        road = run.iterations[1].result["metadata"]["road"]
        self.assertNotEqual(road["capacity_vph"], 99_999)

    def test_no_change_recommendation_stops_the_loop(self):
        recommender = ScriptedRecommender(
            [
                GeminiRecommendation(45, 100.0, 20, "keep it as is"),
                GeminiRecommendation(45, 100.0, 20, "keep it as is"),
            ]
        )

        run = optimize(GoalConfig(queue_percent=-99), recommender, max_iterations=5)

        self.assertEqual(run.status, STATUS_MAX_ITERATIONS)
        self.assertEqual(len(run.iterations), 1)
        self.assertIn("no change", (run.message or "").lower())


class AiAvailabilityTests(unittest.TestCase):
    def test_missing_api_key_reports_ai_unavailable(self):
        def unavailable(scenario, result, goals):
            raise GeminiUnavailableError("AI unavailable: GEMINI_API_KEY is not configured.")

        run = optimize(GoalConfig(queue_percent=-99), unavailable)

        self.assertEqual(run.status, STATUS_AI_UNAVAILABLE)
        self.assertEqual(len(run.iterations), 1)
        self.assertIn("GEMINI_API_KEY", run.message or "")
        # The first simulation still produced real KPIs.
        self.assertGreater(run.iterations[0].result["scenario"]["travel_time_minutes"], 0)
        self.assertIsNone(run.iterations[0].reasoning)

    def test_gemini_failure_reports_ai_error(self):
        def failing(scenario, result, goals):
            raise GeminiServiceError("Gemini returned 503")

        run = optimize(GoalConfig(queue_percent=-99), failing)

        self.assertEqual(run.status, STATUS_AI_ERROR)
        self.assertIn("503", run.message or "")


class GoalRequirementTests(unittest.TestCase):
    def test_empty_goals_are_rejected(self):
        with self.assertRaises(ValueError):
            optimize(GoalConfig(), ScriptedRecommender([]))


class DeterminismTests(unittest.TestCase):
    def test_same_inputs_produce_identical_runs(self):
        def build():
            return optimize(
                GoalConfig(queue_percent=-80),
                ScriptedRecommender(
                    [
                        GeminiRecommendation(50, 120.0, 80, "a"),
                        GeminiRecommendation(55, 150.0, 70, "b"),
                    ]
                ),
                max_iterations=3,
            )

        first = build().to_dict()
        second = build().to_dict()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
