"""Gemini reasoning client.

Responsibilities and hard limits:

* Gemini reads the scenario, the simulation result and the goals, and proposes
  the next values for the three allowed policy variables.
* Gemini never produces KPIs. Every KPI in this project comes from the Python
  simulation in ``simulation/``.
* Output is requested as structured JSON against a fixed schema, so no free-text
  parsing or regex extraction is involved.
* The returned values are still untrusted: ``simulation.scenario.validate_recommendation``
  clamps them to the published bounds before they can reach the model.

If ``GEMINI_API_KEY`` is unset the module raises ``GeminiUnavailableError``. It
never raises at import time, so plain simulation keeps working without a key.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

import httpx

from simulation.scenario import (
    PARKING_SPACES_BOUNDS,
    RED_LINE_METERS_BOUNDS,
    SIGNAL_GREEN_SECONDS_BOUNDS,
)


try:  # optional convenience only; python-dotenv is not a hard requirement
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv()
except Exception:  # pragma: no cover - absence of dotenv must never break import
    pass


GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GEMINI_MODEL_ENV = "GEMINI_MODEL"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
GEMINI_TIMEOUT_SECONDS = 30.0

AI_UNAVAILABLE_MESSAGE = (
    "AI unavailable: GEMINI_API_KEY is not configured. Simulation endpoints are "
    "unaffected; set the key in .env to enable reasoning."
)

# Structured-output contract. Mirrors PolicyRecommendation in api/schemas.py.
RECOMMENDATION_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "signal_green_seconds": {"type": "integer"},
        "red_line_meters": {"type": "number"},
        "parking_spaces": {"type": "integer"},
        "reasoning": {"type": "string"},
    },
    "required": [
        "signal_green_seconds",
        "red_line_meters",
        "parking_spaces",
        "reasoning",
    ],
}


class GeminiUnavailableError(RuntimeError):
    """No API key configured."""


class GeminiServiceError(RuntimeError):
    """The API key exists but the call or the response was unusable."""


@dataclass(frozen=True)
class GeminiRecommendation:
    signal_green_seconds: int
    red_line_meters: float
    parking_spaces: int
    reasoning: str

    def to_dict(self) -> dict:
        return {
            "signal_green_seconds": self.signal_green_seconds,
            "red_line_meters": self.red_line_meters,
            "parking_spaces": self.parking_spaces,
            "reasoning": self.reasoning,
        }


def api_key() -> str:
    return (os.environ.get(GEMINI_API_KEY_ENV) or "").strip()


def model_name() -> str:
    return (os.environ.get(GEMINI_MODEL_ENV) or "").strip() or DEFAULT_GEMINI_MODEL


def is_configured() -> bool:
    return bool(api_key())


def build_prompt(
    scenario: Mapping[str, Any],
    result: Mapping[str, Any],
    goals: Mapping[str, Any],
) -> str:
    signal_low, signal_high = SIGNAL_GREEN_SECONDS_BOUNDS
    red_low, red_high = RED_LINE_METERS_BOUNDS
    parking_low, parking_high = PARKING_SPACES_BOUNDS

    return (
        "You are a transport-policy analyst tuning a traffic microsimulation of "
        "the Xinyi shopping district in Taipei.\n\n"
        "You may ONLY propose new values for these three variables:\n"
        f"  signal_green_seconds: integer, {signal_low}..{signal_high}\n"
        f"  red_line_meters: number, {red_low:g}..{red_high:g}\n"
        f"  parking_spaces: integer, {parking_low}..{parking_high}\n\n"
        "How the simulation responds (proxy model, uncalibrated):\n"
        "  - More green seconds raise signal capacity and cut the queue.\n"
        "  - More red-line metres raise effective road capacity, cutting travel "
        "time and V/C.\n"
        "  - More parking spaces cut cruising-for-parking demand, cutting travel "
        "time, V/C and queue.\n\n"
        "Do NOT output KPIs, predictions or percentages as facts; the Python "
        "simulator computes all KPIs. Explain your reasoning briefly in "
        "Traditional Chinese.\n\n"
        f"Current scenario diff:\n{json.dumps(scenario, ensure_ascii=False, indent=2)}\n\n"
        f"Latest simulation result:\n{json.dumps(result, ensure_ascii=False, indent=2)}\n\n"
        f"Goals (percentage change versus baseline that must be reached):\n"
        f"{json.dumps(goals, ensure_ascii=False, indent=2)}\n\n"
        "Propose the next values for the three variables so that more goals are met."
    )


def _extract_json_text(payload: Mapping[str, Any]) -> str:
    try:
        parts = payload["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as error:
        raise GeminiServiceError(
            f"Unexpected Gemini response shape: {error}"
        ) from error

    for part in parts:
        text = part.get("text")
        if text:
            return text

    raise GeminiServiceError("Gemini response contained no text part")


def recommend_policy(
    scenario: Mapping[str, Any],
    result: Mapping[str, Any],
    goals: Mapping[str, Any],
    *,
    timeout: float = GEMINI_TIMEOUT_SECONDS,
    client: Optional[httpx.Client] = None,
) -> GeminiRecommendation:
    key = api_key()
    if not key:
        raise GeminiUnavailableError(AI_UNAVAILABLE_MESSAGE)

    request_body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": build_prompt(scenario, result, goals)}],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RECOMMENDATION_RESPONSE_SCHEMA,
            "temperature": 0.2,
        },
    }

    url = GEMINI_ENDPOINT_TEMPLATE.format(model=model_name())
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}

    owns_client = client is None
    http_client = client or httpx.Client(timeout=timeout)

    try:
        response = http_client.post(url, json=request_body, headers=headers)
    except httpx.HTTPError as error:
        raise GeminiServiceError(f"Gemini request failed: {error}") from error
    finally:
        if owns_client:
            http_client.close()

    if response.status_code != 200:
        raise GeminiServiceError(
            f"Gemini returned {response.status_code}: {response.text[:500]}"
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise GeminiServiceError("Gemini response was not JSON") from error

    text = _extract_json_text(payload)

    try:
        parsed = json.loads(text)
    except ValueError as error:
        raise GeminiServiceError(
            "Gemini structured output was not valid JSON"
        ) from error

    if not isinstance(parsed, dict):
        raise GeminiServiceError("Gemini structured output was not a JSON object")

    return GeminiRecommendation(
        signal_green_seconds=int(parsed.get("signal_green_seconds", 0)),
        red_line_meters=float(parsed.get("red_line_meters", 0.0)),
        parking_spaces=int(parsed.get("parking_spaces", 0)),
        reasoning=str(parsed.get("reasoning", "")),
    )
