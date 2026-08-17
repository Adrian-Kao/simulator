"""Step 4: parking supply, availability, and deterministic choice model."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class ParkingFacility:
    facility_id: str
    capacity: int
    available_spaces: Optional[int]
    hourly_fee: float = 0.0
    walk_distance_m: float = 0.0

    def __post_init__(self):
        if self.capacity < 0:
            raise ValueError("capacity cannot be negative")
        if self.available_spaces is not None and not 0 <= self.available_spaces <= self.capacity:
            raise ValueError("available_spaces must be within capacity or None")

    @property
    def occupancy_rate(self) -> Optional[float]:
        if self.available_spaces is None or self.capacity == 0:
            return None
        return (self.capacity - self.available_spaces) / self.capacity

    def park(self, vehicles: int = 1) -> int:
        if vehicles < 0:
            raise ValueError("vehicles cannot be negative")
        if self.available_spaces is None:
            return 0
        admitted = min(vehicles, self.available_spaces)
        self.available_spaces -= admitted
        return admitted

    def leave(self, vehicles: int = 1) -> int:
        if vehicles < 0:
            raise ValueError("vehicles cannot be negative")
        if self.available_spaces is None:
            return 0
        released = min(vehicles, self.capacity - self.available_spaces)
        self.available_spaces += released
        return released

    def generalized_cost(self, price_weight: float, walk_minutes_per_m: float) -> float:
        if self.available_spaces in (None, 0):
            return float("inf")
        return self.hourly_fee * price_weight + self.walk_distance_m * walk_minutes_per_m


def choose_parking(facilities: Iterable[ParkingFacility], price_weight: float, walk_minutes_per_m: float) -> ParkingFacility:
    candidates = list(facilities)
    if not candidates:
        raise ValueError("At least one parking facility is required")
    choice = min(candidates, key=lambda facility: facility.generalized_cost(price_weight, walk_minutes_per_m))
    if choice.generalized_cost(price_weight, walk_minutes_per_m) == float("inf"):
        raise LookupError("No parking spaces are available")
    return choice


def load_taipei_parking(static_path: Path, dynamic_path: Path) -> List[ParkingFacility]:
    """Merge official Taipei static and dynamic snapshots by parking-facility ID.

    Negative availability values in the source mean unavailable/not supplied and are
    represented as None instead of as parking spaces.
    """
    with Path(static_path).open(encoding="utf-8") as file:
        static = json.load(file)["data"]["park"]
    with Path(dynamic_path).open(encoding="utf-8") as file:
        dynamic = {row["id"]: row for row in json.load(file)["data"]["park"]}

    facilities = []
    for row in static:
        capacity = _non_negative_int(row.get("totalcar"))
        live = dynamic.get(row["id"], {}).get("availablecar")
        available = live if isinstance(live, int) and 0 <= live <= capacity else None
        facilities.append(ParkingFacility(row["id"], capacity, available))
    return facilities


def _non_negative_int(value: object) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0
