"""Step 2: road-network loading and travel-time calibration."""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


DEFAULT_SPEED_KPH = 30.0
DEFAULT_CAPACITY_VPH_PER_LANE = 900.0


@dataclass(frozen=True)
class RoadSegment:
    segment_id: str
    length_m: float
    lanes: int
    speed_limit_kph: float
    capacity_vph: float
    properties: dict

    @property
    def free_flow_minutes(self) -> float:
        return self.length_m / (self.speed_limit_kph * 1000 / 60)

    def travel_time_minutes(self, flow_vph: float, alpha: float = 0.15, beta: float = 4.0) -> float:
        if flow_vph < 0:
            raise ValueError("flow_vph cannot be negative")
        if self.capacity_vph <= 0:
            raise ValueError("capacity_vph must be positive")
        return self.free_flow_minutes * (1 + alpha * (flow_vph / self.capacity_vph) ** beta)

    def travel_speed_kph(self, flow_vph: float) -> float:
        return self.length_m / 1000 / (self.travel_time_minutes(flow_vph) / 60)


def load_road_segments(geojson_path: Path) -> List[RoadSegment]:
    with Path(geojson_path).open(encoding="utf-8") as file:
        document = json.load(file)
    if document.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection")

    segments = []
    for index, feature in enumerate(document.get("features", [])):
        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates", [])
        if geometry.get("type") != "LineString" or len(coordinates) < 2:
            continue
        properties = feature.get("properties") or {}
        lanes = _positive_int(properties.get("lanes"), default=1)
        speed = _speed_limit(properties.get("maxspeed"))
        length_m = _line_length_m(coordinates)
        if length_m <= 0:
            continue
        segments.append(
            RoadSegment(
                segment_id=str(properties.get("@id") or properties.get("id") or index),
                length_m=length_m,
                lanes=lanes,
                speed_limit_kph=speed,
                capacity_vph=lanes * DEFAULT_CAPACITY_VPH_PER_LANE,
                properties=properties,
            )
        )
    if not segments:
        raise ValueError("No usable LineString road segments found")
    return segments


def calibrate_free_flow_speed(segment: RoadSegment, observed_speed_kph: Iterable[float]) -> RoadSegment:
    """Calibrate from observations known to be free-flow; ignores invalid values."""
    values = [value for value in observed_speed_kph if value > 0]
    if not values:
        raise ValueError("At least one positive observed speed is required")
    calibrated = sum(values) / len(values)
    return RoadSegment(
        segment_id=segment.segment_id,
        length_m=segment.length_m,
        lanes=segment.lanes,
        speed_limit_kph=calibrated,
        capacity_vph=segment.capacity_vph,
        properties=segment.properties,
    )


def _positive_int(value: object, default: int) -> int:
    try:
        parsed = int(str(value).split(";")[0])
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _speed_limit(value: object) -> float:
    try:
        parsed = float(str(value).split(";")[0].replace(" km/h", ""))
        return parsed if parsed > 0 else DEFAULT_SPEED_KPH
    except (TypeError, ValueError):
        return DEFAULT_SPEED_KPH


def _line_length_m(coordinates: list) -> float:
    return sum(_distance_m(first, second) for first, second in zip(coordinates, coordinates[1:]))


def _distance_m(first: list, second: list) -> float:
    lon1, lat1 = map(math.radians, first)
    lon2, lat2 = map(math.radians, second)
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
