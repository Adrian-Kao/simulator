from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from simulation.scenario import (
    PARKING_SPACES_BOUNDS,
    RED_LINE_METERS_BOUNDS,
    SIGNAL_GREEN_SECONDS_BOUNDS,
)


class SignalPhasePayload(BaseModel):
    name: str
    seconds: int = Field(ge=1)
    color: Literal["green", "yellow", "red"]


class PolicyPayload(BaseModel):
    """One entry of a ScenarioDiff as sent by the frontend.

    Only the three demo variables influence the simulation:
    ``signal-timing`` (X1), ``red-line`` (X2) and ``parking`` (X3).
    ``traffic-restriction`` is still accepted so existing clients keep working,
    but it is reported as an unmodelled policy in the response warnings.
    """

    type: Literal[
        "red-line",
        "parking",
        "signal-timing",
        "traffic-restriction",
    ]

    # common / red-line
    road_id: Optional[str] = None
    side: Optional[Literal["left", "right"]] = None
    start_offset: Optional[float] = Field(default=None, ge=0, le=1)
    end_offset: Optional[float] = Field(default=None, ge=0, le=1)
    length_meters: Optional[float] = Field(default=None, ge=0)
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    # parking
    parking_id: Optional[str] = None
    name: Optional[str] = None
    spaces: Optional[int] = None

    # signal / restriction
    intersection_id: Optional[str] = None
    phases: Optional[List[SignalPhasePayload]] = None
    baseline_seconds: Optional[int] = Field(default=None, ge=1)
    scenario_seconds: Optional[int] = Field(default=None, ge=1)
    restriction_type: Optional[
        Literal["forbid-right-turn", "forbid-left-turn", "forbid-entry"]
    ] = None
    target_road_id: Optional[str] = None


class GoalConfigPayload(BaseModel):
    """Required percentage change versus baseline; sign carries the direction."""

    travel_time_percent: Optional[float] = None
    travel_speed_percent: Optional[float] = None
    congestion_vc_percent: Optional[float] = None
    queue_percent: Optional[float] = None


class SimulationRequest(BaseModel):
    scenario_id: str
    day_type: Literal["weekday", "weekend", "event"]
    time_slot: str
    random_seed: int = 42
    road_id: Optional[str] = None
    road_name: Optional[str] = None
    policies: List[PolicyPayload] = Field(default_factory=list)
    goals: Optional[GoalConfigPayload] = None


class SimulationKpi(BaseModel):
    travel_time_minutes: float
    travel_speed_kph: float
    congestion_vc: float
    queue_vehicles: float


class SimulationDelta(BaseModel):
    travel_time_percent: float
    travel_speed_percent: float
    congestion_vc_percent: float
    queue_percent: float


class PolicyVariablesPayload(BaseModel):
    signal_green_seconds: int
    red_line_meters: float
    parking_spaces: int


class GoalStatusPayload(BaseModel):
    metric: str
    label: str
    direction: Literal["decrease", "increase"]
    target_percent: float
    current_percent: float
    gap_percent: float
    met: bool


class SimulationResponse(BaseModel):
    scenario_id: str
    baseline: SimulationKpi
    scenario: SimulationKpi
    delta: SimulationDelta
    recommended: str
    baseline_variables: PolicyVariablesPayload
    scenario_variables: PolicyVariablesPayload
    goal_status: List[GoalStatusPayload] = Field(default_factory=list)
    goals_met: bool = False
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyRecommendation(BaseModel):
    """Structured Gemini output. Bounds are enforced again in simulation.scenario."""

    signal_green_seconds: int = Field(
        ge=SIGNAL_GREEN_SECONDS_BOUNDS[0], le=SIGNAL_GREEN_SECONDS_BOUNDS[1]
    )
    red_line_meters: float = Field(
        ge=RED_LINE_METERS_BOUNDS[0], le=RED_LINE_METERS_BOUNDS[1]
    )
    parking_spaces: int = Field(
        ge=PARKING_SPACES_BOUNDS[0], le=PARKING_SPACES_BOUNDS[1]
    )
    reasoning: str = ""


class ReasonRequest(BaseModel):
    scenario: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    goals: GoalConfigPayload


class ReasonResponse(BaseModel):
    status: Literal["ok", "ai_unavailable", "ai_error"]
    recommendation: Optional[PolicyRecommendation] = None
    reasoning: Optional[str] = None
    validation_notes: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    bounds: Dict[str, Any] = Field(default_factory=dict)


class OptimizeRequest(BaseModel):
    initial_scenario: SimulationRequest
    goals: GoalConfigPayload
    max_iterations: int = Field(default=5, ge=1, le=10)


class OptimizationIterationPayload(BaseModel):
    iteration: int
    scenario: Dict[str, Any]
    result: Dict[str, Any]
    goal_status: List[GoalStatusPayload] = Field(default_factory=list)
    goals_met: bool = False
    reasoning: Optional[str] = None
    recommendation: Optional[PolicyVariablesPayload] = None
    validation_notes: List[str] = Field(default_factory=list)


class OptimizeResponse(BaseModel):
    status: Literal["goal_reached", "max_iterations", "ai_unavailable", "ai_error"]
    iterations: List[OptimizationIterationPayload] = Field(default_factory=list)
    final_scenario: Dict[str, Any] = Field(default_factory=dict)
    final_result: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
