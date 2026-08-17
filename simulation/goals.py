"""Goal engine: declarative KPI targets and per-metric attainment status.

A goal is expressed as a required percentage change of a KPI relative to the
baseline scenario. The sign carries the direction:

    travel_time_percent: -10   -> travel time must fall by at least 10%
    travel_speed_percent:  8   -> travel speed must rise by at least 8%
    queue_percent:       -15   -> queue must fall by at least 15%

This lives in ``simulation/`` (not the UI) so the same rule decides attainment
for the API response, the optimisation loop and the dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Optional, Sequence, Tuple, Union

from .policy_effects import KpiDelta


# Percentage-point tolerance when comparing against a target.
GOAL_TOLERANCE_PERCENT = 1e-9

GOAL_METRICS: Tuple[str, ...] = (
    "travel_time_percent",
    "travel_speed_percent",
    "congestion_vc_percent",
    "queue_percent",
)

GOAL_METRIC_LABELS = {
    "travel_time_percent": "Travel Time",
    "travel_speed_percent": "Travel Speed",
    "congestion_vc_percent": "V/C",
    "queue_percent": "Queue",
}


@dataclass(frozen=True)
class GoalConfig:
    travel_time_percent: Optional[float] = None
    travel_speed_percent: Optional[float] = None
    congestion_vc_percent: Optional[float] = None
    queue_percent: Optional[float] = None

    def is_empty(self) -> bool:
        return not self.items()

    def items(self) -> List[Tuple[str, float]]:
        result: List[Tuple[str, float]] = []
        for metric in GOAL_METRICS:
            target = getattr(self, metric)
            if target is not None:
                result.append((metric, float(target)))
        return result

    def to_dict(self) -> dict:
        return {metric: target for metric, target in self.items()}


@dataclass(frozen=True)
class GoalStatus:
    metric: str
    label: str
    direction: str  # "decrease" | "increase"
    target_percent: float
    current_percent: float
    gap_percent: float
    met: bool

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "label": self.label,
            "direction": self.direction,
            "target_percent": self.target_percent,
            "current_percent": self.current_percent,
            "gap_percent": self.gap_percent,
            "met": self.met,
        }


DeltaLike = Union[KpiDelta, Mapping[str, float]]


def _delta_value(delta: DeltaLike, metric: str) -> float:
    if isinstance(delta, Mapping):
        if metric not in delta:
            raise KeyError(f"delta is missing metric {metric!r}")
        return float(delta[metric])
    return float(getattr(delta, metric))


def goal_status(metric: str, target_percent: float, current_percent: float) -> GoalStatus:
    """Attainment of one metric.

    ``gap_percent`` is the remaining percentage points still required; it is 0
    once the target is reached or exceeded.
    """
    if metric not in GOAL_METRICS:
        raise ValueError(f"Unsupported goal metric: {metric!r}")

    if target_percent < 0:
        direction = "decrease"
        gap = max(0.0, current_percent - target_percent)
    else:
        direction = "increase"
        gap = max(0.0, target_percent - current_percent)

    return GoalStatus(
        metric=metric,
        label=GOAL_METRIC_LABELS[metric],
        direction=direction,
        target_percent=target_percent,
        current_percent=current_percent,
        gap_percent=gap,
        met=gap <= GOAL_TOLERANCE_PERCENT,
    )


def evaluate_goals(delta: DeltaLike, goals: Optional[GoalConfig]) -> List[GoalStatus]:
    if goals is None:
        return []
    return [
        goal_status(metric, target, _delta_value(delta, metric))
        for metric, target in goals.items()
    ]


def goals_met(delta: DeltaLike, goals: Optional[GoalConfig]) -> bool:
    """True only when at least one goal is configured and every goal is met."""
    statuses = evaluate_goals(delta, goals)
    if not statuses:
        return False
    return all(status.met for status in statuses)


def worst_gap(statuses: Sequence[GoalStatus]) -> Optional[GoalStatus]:
    """The goal furthest from being met, useful for prompting and diagnostics."""
    unmet = [status for status in statuses if not status.met]
    if not unmet:
        return None
    return max(unmet, key=lambda status: status.gap_percent)
