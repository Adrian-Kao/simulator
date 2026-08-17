"""Closed optimisation loop: simulate -> check goals -> reason -> validate -> patch -> simulate.

Stop conditions
---------------
    goal_reached    every configured goal is met
    max_iterations  the iteration budget ran out first
    ai_unavailable  no Gemini API key, so no patch can be proposed

``max_iterations`` counts simulation rounds, including the initial scenario, so
``max_iterations=5`` performs at most five simulations and at most four patches.

The recommender is injected, so tests exercise the loop without touching the
Gemini API. Whatever it returns is passed through
``simulation.scenario.validate_recommendation`` before it can influence a
simulation: the loop can only ever move the three published variables, within
their published bounds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from simulation.goals import GoalConfig
from simulation.orchestrator import (
    HISTORICAL_OBSERVATIONS_PATH,
    ROAD_NETWORK_PATH,
    SimulationOutcome,
    run_simulation,
)
from simulation.scenario import (
    ScenarioDiff,
    apply_variables,
    bounds_manifest,
    validate_recommendation,
)

from .gemini_service import (
    GeminiRecommendation,
    GeminiServiceError,
    GeminiUnavailableError,
    recommend_policy,
)


DEFAULT_MAX_ITERATIONS = 5
MAX_ITERATIONS_LIMIT = 10

STATUS_GOAL_REACHED = "goal_reached"
STATUS_MAX_ITERATIONS = "max_iterations"
STATUS_AI_UNAVAILABLE = "ai_unavailable"
STATUS_AI_ERROR = "ai_error"


Recommender = Callable[[Dict, Dict, Dict], GeminiRecommendation]


@dataclass
class OptimizationIteration:
    iteration: int
    scenario: Dict
    result: Dict
    goal_status: List[Dict]
    goals_met: bool
    # Reasoning for the patch that produced the NEXT iteration. The final
    # iteration has no reasoning because no further patch was applied.
    reasoning: Optional[str] = None
    recommendation: Optional[Dict] = None
    validation_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "scenario": self.scenario,
            "result": self.result,
            "goal_status": self.goal_status,
            "goals_met": self.goals_met,
            "reasoning": self.reasoning,
            "recommendation": self.recommendation,
            "validation_notes": self.validation_notes,
        }


@dataclass
class OptimizationRun:
    status: str
    iterations: List[OptimizationIteration]
    final_scenario: Dict
    final_result: Dict
    message: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "iterations": [item.to_dict() for item in self.iterations],
            "final_scenario": self.final_scenario,
            "final_result": self.final_result,
            "message": self.message,
            "metadata": self.metadata,
        }


def _default_recommender(
    scenario: Dict, result: Dict, goals: Dict
) -> GeminiRecommendation:
    return recommend_policy(scenario, result, goals)


def run_optimization(
    initial_diff: ScenarioDiff,
    goals: GoalConfig,
    *,
    day_type: str = "weekday",
    time_slot: str = "17:30",
    random_seed: int = 42,
    tick_minutes: int = 5,
    road_id: Optional[str] = None,
    road_name: Optional[str] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    recommender: Optional[Recommender] = None,
    historical_path: Path = HISTORICAL_OBSERVATIONS_PATH,
    road_network_path: Path = ROAD_NETWORK_PATH,
) -> OptimizationRun:
    if goals is None or goals.is_empty():
        raise ValueError("At least one goal is required to run an optimisation")

    budget = max(1, min(MAX_ITERATIONS_LIMIT, int(max_iterations)))
    reason = recommender or _default_recommender

    diff = initial_diff
    iterations: List[OptimizationIteration] = []
    status = STATUS_MAX_ITERATIONS
    message: Optional[str] = None
    last_outcome: Optional[SimulationOutcome] = None

    for index in range(1, budget + 1):
        outcome = run_simulation(
            diff,
            day_type=day_type,
            time_slot=time_slot,
            random_seed=random_seed,
            tick_minutes=tick_minutes,
            road_id=road_id,
            road_name=road_name,
            goals=goals,
            historical_path=historical_path,
            road_network_path=road_network_path,
        )
        last_outcome = outcome

        record = OptimizationIteration(
            iteration=index,
            scenario=diff.to_dict(),
            result=outcome.to_dict(),
            goal_status=[status_.to_dict() for status_ in outcome.goal_status],
            goals_met=outcome.goals_met,
        )
        iterations.append(record)

        if outcome.goals_met:
            status = STATUS_GOAL_REACHED
            break

        if index == budget:
            status = STATUS_MAX_ITERATIONS
            message = (
                f"Reached max_iterations={budget} without meeting every goal."
            )
            break

        try:
            recommendation = reason(
                diff.to_dict(),
                outcome.to_dict(),
                goals.to_dict(),
            )
        except GeminiUnavailableError as error:
            status = STATUS_AI_UNAVAILABLE
            message = str(error)
            break
        except GeminiServiceError as error:
            status = STATUS_AI_ERROR
            message = str(error)
            break

        validated = validate_recommendation(recommendation)
        record.recommendation = validated.variables.to_dict()
        record.validation_notes = list(validated.notes)
        record.reasoning = getattr(recommendation, "reasoning", None)

        next_diff = apply_variables(
            diff,
            validated.variables,
            road_id=road_id,
        )

        if next_diff.to_dict() == diff.to_dict():
            status = STATUS_MAX_ITERATIONS
            message = (
                "Reasoning proposed no change to the policy variables; stopped early."
            )
            break

        diff = next_diff

    final_result = last_outcome.to_dict() if last_outcome else {}

    return OptimizationRun(
        status=status,
        iterations=iterations,
        final_scenario=diff.to_dict(),
        final_result=final_result,
        message=message,
        metadata={
            "max_iterations": budget,
            "iterations_run": len(iterations),
            "goals": goals.to_dict(),
            "bounds": bounds_manifest(),
        },
    )
