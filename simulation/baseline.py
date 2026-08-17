"""Step 1: reproducible baseline-scenario configuration."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, time, timedelta
from random import Random
from typing import Dict, List


@dataclass(frozen=True)
class ScenarioConfig:
    scenario_id: str
    service_date: str
    tick_minutes: int = 5
    start_time: str = "08:00"
    end_time: str = "23:00"
    random_seed: int = 48219
    demand_profile: Dict[str, float] = field(default_factory=lambda: {"08:00": 1.0})

    def validate(self) -> None:
        if self.tick_minutes <= 0 or 60 % self.tick_minutes:
            raise ValueError("tick_minutes must be a positive divisor of 60")
        start = _parse_time(self.start_time)
        end = _parse_time(self.end_time)
        if start >= end:
            raise ValueError("start_time must be earlier than end_time")
        if not self.scenario_id:
            raise ValueError("scenario_id is required")
        if not self.demand_profile or any(value < 0 for value in self.demand_profile.values()):
            raise ValueError("demand_profile must contain non-negative values")

    def ticks(self) -> List[str]:
        self.validate()
        current = _parse_time(self.start_time)
        end = _parse_time(self.end_time)
        result = []
        while current < end:
            result.append(current.strftime("%H:%M"))
            current += timedelta(minutes=self.tick_minutes)
        return result

    def rng(self) -> Random:
        self.validate()
        return Random(self.random_seed)

    def manifest(self) -> dict:
        self.validate()
        return asdict(self)


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise ValueError(f"Invalid HH:MM time: {value}") from exc
    return parsed
