from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SignalPhasePayload(BaseModel):
    name: str
    seconds: int = Field(ge=1)
    color: Literal["green", "yellow", "red"]


class PolicyPayload(BaseModel):
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
    spaces: Optional[int] = Field(default=None, ge=1)

    # signal / restriction
    intersection_id: Optional[str] = None
    phases: Optional[List[SignalPhasePayload]] = None
    restriction_type: Optional[
        Literal["forbid-right-turn", "forbid-left-turn", "forbid-entry"]
    ] = None
    target_road_id: Optional[str] = None


class SimulationRequest(BaseModel):
    scenario_id: str
    day_type: Literal["weekday", "weekend", "event"]
    time_slot: str
    random_seed: int = 42
    road_id: Optional[str] = None
    road_name: Optional[str] = None
    policies: List[PolicyPayload] = Field(default_factory=list)


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


class SimulationResponse(BaseModel):
    scenario_id: str
    baseline: SimulationKpi
    scenario: SimulationKpi
    delta: SimulationDelta
    recommended: str
    warnings: List[str] = Field(default_factory=list)
