"""Step 3: signal timing, turn restrictions, and deterministic queue updates."""

from dataclasses import dataclass, field
from typing import Dict, Iterable, Set


@dataclass(frozen=True)
class SignalPhase:
    name: str
    green_seconds: int
    movements: Set[str]


@dataclass
class SignalPlan:
    intersection_id: str
    cycle_seconds: int
    phases: list
    prohibited_movements: Dict[str, Set[str]] = field(default_factory=dict)
    saturation_flow_vph: float = 1_800.0

    def validate(self) -> None:
        if self.cycle_seconds <= 0 or self.saturation_flow_vph <= 0:
            raise ValueError("cycle_seconds and saturation_flow_vph must be positive")
        if not self.phases or any(phase.green_seconds <= 0 for phase in self.phases):
            raise ValueError("At least one positive-green phase is required")
        if sum(phase.green_seconds for phase in self.phases) > self.cycle_seconds:
            raise ValueError("Total green seconds cannot exceed cycle_seconds")

    def can_move(self, movement: str, tick: str) -> bool:
        return movement not in self.prohibited_movements.get(tick, set())

    def effective_capacity_vph(self, movement: str, tick: str = "all") -> float:
        self.validate()
        if not self.can_move(movement, tick):
            return 0.0
        green_seconds = sum(phase.green_seconds for phase in self.phases if movement in phase.movements)
        return self.saturation_flow_vph * green_seconds / self.cycle_seconds

    def update_queue(self, movement: str, arrivals: float, queued: float, tick_minutes: int, tick: str = "all") -> dict:
        if arrivals < 0 or queued < 0 or tick_minutes <= 0:
            raise ValueError("arrivals, queued, and tick_minutes must be non-negative/positive")
        capacity = self.effective_capacity_vph(movement, tick) * tick_minutes / 60
        discharged = min(queued + arrivals, capacity)
        return {"departures": discharged, "queue": queued + arrivals - discharged}

