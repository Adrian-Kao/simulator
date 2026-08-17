"""Historical observations and typical-day baselines for policy comparison."""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable, List


@dataclass(frozen=True)
class HistoricalObservation:
    timestamp: datetime
    day_type: str
    segment_id: str
    travel_time_minutes: float
    travel_speed_kph: float
    traffic_volume_vph: float
    footfall_per_hour: float
    parking_occupancy_rate: float
    youbike_borrows: float
    youbike_returns: float
    event_flag: bool = False

    @property
    def time_slot(self) -> str:
        return self.timestamp.strftime("%H:%M")


@dataclass(frozen=True)
class TypicalDayMetric:
    day_type: str
    time_slot: str
    segment_id: str
    observation_count: int
    travel_time_minutes: float
    travel_speed_kph: float
    traffic_volume_vph: float
    footfall_per_hour: float
    parking_occupancy_rate: float
    youbike_borrows: float
    youbike_returns: float


def load_historical_observations(csv_path: Path) -> List[HistoricalObservation]:
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as file:
        rows = csv.DictReader(file)
        observations = []
        for row in rows:
            observations.append(HistoricalObservation(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                day_type=row["day_type"],
                segment_id=row["segment_id"],
                travel_time_minutes=float(row["travel_time_minutes"]),
                travel_speed_kph=float(row["travel_speed_kph"]),
                traffic_volume_vph=float(row["traffic_volume_vph"]),
                footfall_per_hour=float(row["footfall_per_hour"]),
                parking_occupancy_rate=float(row["parking_occupancy_rate"]),
                youbike_borrows=float(row["youbike_borrows"]),
                youbike_returns=float(row["youbike_returns"]),
                event_flag=row.get("event_flag", "false").strip().lower() == "true",
            ))
    return observations


def build_typical_day(observations: Iterable[HistoricalObservation], day_type: str, include_events: bool = False) -> List[TypicalDayMetric]:
    groups = {}
    for observation in observations:
        if observation.day_type != day_type or (observation.event_flag and not include_events):
            continue
        groups.setdefault((observation.time_slot, observation.segment_id), []).append(observation)
    if not groups:
        raise ValueError(f"No observations available for day_type={day_type!r}")
    metrics = []
    for (time_slot, segment_id), rows in sorted(groups.items()):
        metrics.append(TypicalDayMetric(
            day_type=day_type,
            time_slot=time_slot,
            segment_id=segment_id,
            observation_count=len(rows),
            travel_time_minutes=mean(row.travel_time_minutes for row in rows),
            travel_speed_kph=mean(row.travel_speed_kph for row in rows),
            traffic_volume_vph=mean(row.traffic_volume_vph for row in rows),
            footfall_per_hour=mean(row.footfall_per_hour for row in rows),
            parking_occupancy_rate=mean(row.parking_occupancy_rate for row in rows),
            youbike_borrows=mean(row.youbike_borrows for row in rows),
            youbike_returns=mean(row.youbike_returns for row in rows),
        ))
    return metrics
