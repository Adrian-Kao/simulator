"""HTTP-level tests for goals, /api/reason and /api/optimize.

``GEMINI_API_KEY`` is cleared in every test that could otherwise reach the real
Gemini API, so this file never makes a network call even on a machine that has a
key configured.
"""

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from api.main import app
from simulation.scenario import SIGNAL_GREEN_SECONDS_BOUNDS


client = TestClient(app)

NO_API_KEY = {"GEMINI_API_KEY": ""}


def scenario_request(**overrides):
    request = {
        "scenario_id": "scenario-a",
        "day_type": "weekday",
        "time_slot": "17:30",
        "random_seed": 42,
        "road_id": "shifu-road",
        "road_name": "市府路",
        "policies": [
            {
                "type": "signal-timing",
                "intersection_id": "i-7",
                "baseline_seconds": 40,
                "scenario_seconds": 55,
            },
            {
                "type": "red-line",
                "road_id": "shifu-road",
                "length_meters": 120.0,
            },
            {
                "type": "parking",
                "parking_id": "parking-new-1",
                "spaces": 80,
            },
        ],
    }
    request.update(overrides)
    return request


class HealthTests(unittest.TestCase):
    def test_health_reports_ai_configuration(self):
        with mock.patch.dict(os.environ, NO_API_KEY):
            body = client.get("/health").json()

        self.assertEqual(body["status"], "ok")
        self.assertFalse(body["ai_configured"])


class SimulationResponseTests(unittest.TestCase):
    def test_three_variables_are_reported(self):
        body = client.post("/api/simulations", json=scenario_request()).json()

        self.assertEqual(
            body["scenario_variables"],
            {
                "signal_green_seconds": 55,
                "red_line_meters": 120.0,
                "parking_spaces": 80,
            },
        )
        self.assertEqual(body["baseline_variables"]["signal_green_seconds"], 40)
        self.assertEqual(body["baseline_variables"]["red_line_meters"], 0.0)

    def test_red_line_and_parking_change_the_result(self):
        signal_only = client.post(
            "/api/simulations",
            json=scenario_request(
                policies=[
                    {
                        "type": "signal-timing",
                        "intersection_id": "i-7",
                        "baseline_seconds": 40,
                        "scenario_seconds": 55,
                    }
                ]
            ),
        ).json()

        everything = client.post("/api/simulations", json=scenario_request()).json()

        self.assertLess(
            everything["scenario"]["travel_time_minutes"],
            signal_only["scenario"]["travel_time_minutes"],
        )
        self.assertLess(
            everything["scenario"]["congestion_vc"],
            signal_only["scenario"]["congestion_vc"],
        )
        self.assertLess(
            everything["scenario"]["queue_vehicles"],
            signal_only["scenario"]["queue_vehicles"],
        )

    def test_empty_scenario_returns_zero_delta(self):
        body = client.post(
            "/api/simulations", json=scenario_request(policies=[])
        ).json()

        self.assertEqual(body["delta"]["travel_time_percent"], 0.0)
        self.assertEqual(body["scenario_variables"]["red_line_meters"], 0.0)
        self.assertEqual(body["metadata"]["scenario_diff"]["policies"], [])

    def test_goal_status_is_returned_when_goals_are_sent(self):
        body = client.post(
            "/api/simulations",
            json=scenario_request(goals={"queue_percent": -15, "travel_speed_percent": 1}),
        ).json()

        metrics = {status["metric"] for status in body["goal_status"]}
        self.assertEqual(metrics, {"queue_percent", "travel_speed_percent"})

        for status in body["goal_status"]:
            self.assertIn("target_percent", status)
            self.assertIn("current_percent", status)
            self.assertIn("gap_percent", status)
            self.assertIn("met", status)

    def test_metadata_declares_the_model_is_not_calibrated(self):
        body = client.post("/api/simulations", json=scenario_request()).json()

        self.assertFalse(body["metadata"]["assumptions"]["calibrated"])
        self.assertIn("sources", body["metadata"])
        self.assertTrue(body["warnings"])

    def test_deterministic_for_same_input_and_seed(self):
        first = client.post("/api/simulations", json=scenario_request()).json()
        second = client.post("/api/simulations", json=scenario_request()).json()
        self.assertEqual(first, second)

    def test_traffic_restriction_warns_only_about_direct_network_effect(self):
        body = client.post(
            "/api/simulations",
            json=scenario_request(
                policies=[
                    {
                        "type": "traffic-restriction",
                        "intersection_id": "i-7",
                        "restriction_type": "forbid-right-turn",
                        "target_road_id": "songgao-road",
                    }
                ]
            ),
        ).json()

        self.assertTrue(
            any(
                "direct road network capacity effect is not modelled" in warning
                for warning in body["warnings"]
            ),
            body["warnings"],
        )
        self.assertLess(
            body["behavior"]["scenario_mode_share"]["drive"],
            body["behavior"]["baseline_mode_share"]["drive"],
        )


class ReasonEndpointTests(unittest.TestCase):
    def test_missing_api_key_is_reported_not_crashed(self):
        with mock.patch.dict(os.environ, NO_API_KEY):
            response = client.post(
                "/api/reason",
                json={
                    "scenario": {"scenario_id": "scenario-a", "policies": []},
                    "result": {},
                    "goals": {"queue_percent": -15},
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ai_unavailable")
        self.assertIn("GEMINI_API_KEY", body["message"])
        self.assertIsNone(body["recommendation"])
        self.assertEqual(
            body["bounds"]["signal_green_seconds"],
            list(SIGNAL_GREEN_SECONDS_BOUNDS),
        )

    def test_simulation_still_works_without_a_key(self):
        with mock.patch.dict(os.environ, NO_API_KEY):
            response = client.post("/api/simulations", json=scenario_request())

        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()["scenario"]["travel_time_minutes"], 0)

    def test_reasoning_requires_at_least_one_goal(self):
        response = client.post(
            "/api/reason",
            json={"scenario": {}, "result": {}, "goals": {}},
        )
        self.assertEqual(response.status_code, 400)


class OptimizeEndpointTests(unittest.TestCase):
    def test_without_a_key_the_first_simulation_still_runs(self):
        with mock.patch.dict(os.environ, NO_API_KEY):
            response = client.post(
                "/api/optimize",
                json={
                    "initial_scenario": scenario_request(),
                    "goals": {"queue_percent": -99},
                    "max_iterations": 5,
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["status"], "ai_unavailable")
        self.assertEqual(len(body["iterations"]), 1)
        self.assertGreater(
            body["iterations"][0]["result"]["scenario"]["travel_time_minutes"], 0
        )
        self.assertIsNone(body["iterations"][0]["reasoning"])
        self.assertEqual(body["metadata"]["max_iterations"], 5)

    def test_goal_already_met_stops_before_calling_the_model(self):
        # A goal the user's own scenario already satisfies, so no reasoning is
        # needed and no API key is required.
        with mock.patch.dict(os.environ, NO_API_KEY):
            body = client.post(
                "/api/optimize",
                json={
                    "initial_scenario": scenario_request(),
                    "goals": {"queue_percent": -5},
                    "max_iterations": 5,
                },
            ).json()

        self.assertEqual(body["status"], "goal_reached")
        self.assertEqual(len(body["iterations"]), 1)
        self.assertTrue(body["iterations"][0]["goals_met"])

    def test_optimize_requires_at_least_one_goal(self):
        response = client.post(
            "/api/optimize",
            json={
                "initial_scenario": scenario_request(),
                "goals": {},
                "max_iterations": 5,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_max_iterations_is_bounded_by_the_schema(self):
        response = client.post(
            "/api/optimize",
            json={
                "initial_scenario": scenario_request(),
                "goals": {"queue_percent": -15},
                "max_iterations": 999,
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
