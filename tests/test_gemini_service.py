"""Gemini client tests.

The default tests use a mocked httpx transport and never reach the network.
``ManualGeminiIntegrationTests`` is skipped unless ``GEMINI_API_KEY`` is set, so
a real end-to-end check is opt-in.
"""

import json
import os
import unittest
from unittest import mock

import httpx

from api.gemini_service import (
    RECOMMENDATION_RESPONSE_SCHEMA,
    GeminiServiceError,
    GeminiUnavailableError,
    build_prompt,
    is_configured,
    recommend_policy,
)
from simulation.scenario import (
    SIGNAL_GREEN_SECONDS_BOUNDS,
    validate_recommendation,
)


SCENARIO = {"scenario_id": "scenario-a", "policies": []}
RESULT = {"delta": {"queue_percent": -5.0}}
GOALS = {"queue_percent": -15.0}


def gemini_reply(payload: dict) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps(payload)},
                        ]
                    }
                }
            ]
        },
    )


def mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


class ConfigurationTests(unittest.TestCase):
    def test_no_key_raises_unavailable(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            self.assertFalse(is_configured())
            with self.assertRaises(GeminiUnavailableError):
                recommend_policy(SCENARIO, RESULT, GOALS)

    def test_whitespace_key_counts_as_missing(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "   "}):
            self.assertFalse(is_configured())


class PromptTests(unittest.TestCase):
    def test_prompt_publishes_the_bounds_and_forbids_kpis(self):
        prompt = build_prompt(SCENARIO, RESULT, GOALS)

        self.assertIn(str(SIGNAL_GREEN_SECONDS_BOUNDS[0]), prompt)
        self.assertIn(str(SIGNAL_GREEN_SECONDS_BOUNDS[1]), prompt)
        self.assertIn("Do NOT output KPIs", prompt)
        self.assertIn("scenario_id", prompt)

    def test_response_schema_requires_only_allowed_fields(self):
        self.assertEqual(
            set(RECOMMENDATION_RESPONSE_SCHEMA["properties"]),
            {
                "signal_green_seconds",
                "red_line_meters",
                "parking_spaces",
                "reasoning",
            },
        )


class StructuredOutputTests(unittest.TestCase):
    def test_structured_response_is_parsed(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = json.loads(request.content)
            captured["key"] = request.headers.get("x-goog-api-key")
            return gemini_reply(
                {
                    "signal_green_seconds": 55,
                    "red_line_meters": 150.0,
                    "parking_spaces": 70,
                    "reasoning": "路口排隊仍是主要瓶頸。",
                }
            )

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            recommendation = recommend_policy(
                SCENARIO, RESULT, GOALS, client=mock_client(handler)
            )

        self.assertEqual(recommendation.signal_green_seconds, 55)
        self.assertEqual(recommendation.red_line_meters, 150.0)
        self.assertEqual(recommendation.parking_spaces, 70)
        self.assertIn("瓶頸", recommendation.reasoning)

        self.assertEqual(captured["key"], "test-key")
        generation = captured["body"]["generationConfig"]
        self.assertEqual(generation["responseMimeType"], "application/json")
        self.assertEqual(
            generation["responseSchema"], RECOMMENDATION_RESPONSE_SCHEMA
        )

    def test_out_of_bounds_model_output_is_clamped_downstream(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return gemini_reply(
                {
                    "signal_green_seconds": 300,
                    "red_line_meters": 9_000.0,
                    "parking_spaces": 5_000,
                    "reasoning": "ignore the bounds",
                }
            )

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            recommendation = recommend_policy(
                SCENARIO, RESULT, GOALS, client=mock_client(handler)
            )

        validated = validate_recommendation(recommendation)
        self.assertEqual(
            validated.variables.signal_green_seconds,
            SIGNAL_GREEN_SECONDS_BOUNDS[1],
        )
        self.assertTrue(validated.notes)

    def test_http_error_status_becomes_service_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="unavailable")

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with self.assertRaises(GeminiServiceError):
                recommend_policy(
                    SCENARIO, RESULT, GOALS, client=mock_client(handler)
                )

    def test_non_json_structured_output_becomes_service_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {"content": {"parts": [{"text": "not json"}]}}
                    ]
                },
            )

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with self.assertRaises(GeminiServiceError):
                recommend_policy(
                    SCENARIO, RESULT, GOALS, client=mock_client(handler)
                )

    def test_unexpected_shape_becomes_service_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"candidates": []})

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with self.assertRaises(GeminiServiceError):
                recommend_policy(
                    SCENARIO, RESULT, GOALS, client=mock_client(handler)
                )


@unittest.skipUnless(
    os.environ.get("GEMINI_API_KEY", "").strip(),
    "Manual test: set GEMINI_API_KEY to call the real Gemini API",
)
class ManualGeminiIntegrationTests(unittest.TestCase):
    def test_real_api_returns_bounded_recommendation(self):
        recommendation = recommend_policy(SCENARIO, RESULT, GOALS)
        validated = validate_recommendation(recommendation)

        low, high = SIGNAL_GREEN_SECONDS_BOUNDS
        self.assertGreaterEqual(validated.variables.signal_green_seconds, low)
        self.assertLessEqual(validated.variables.signal_green_seconds, high)
        self.assertTrue(recommendation.reasoning)


if __name__ == "__main__":
    unittest.main()
