"""Step 5: YouBike station capacity, borrowing, returns, and turnover KPI."""

from dataclasses import dataclass
from math import ceil


MAX_YOUBIKE_TRIP_DISTANCE_M = 5_000
MIN_DEPARTURE_RESERVE_RATIO = 0.15


@dataclass
class YouBikeStation:
    station_id: str
    capacity: int
    bikes: int
    borrows: int = 0
    returns: int = 0

    def __post_init__(self):
        if self.capacity < 0 or not 0 <= self.bikes <= self.capacity:
            raise ValueError("bikes must be between zero and capacity")

    @property
    def empty_docks(self) -> int:
        return self.capacity - self.bikes

    @property
    def turnover_rate(self) -> float:
        """Borrow + return events per dock in the reported time window."""
        return 0.0 if self.capacity == 0 else (self.borrows + self.returns) / self.capacity

    def can_support_departure(
        self,
        requested: int = 1,
        min_reserve_ratio: float = MIN_DEPARTURE_RESERVE_RATIO,
    ) -> bool:
        """Return whether bikes can be borrowed without draining station stock.

        Availability is deliberately stricter than ``bikes >= requested``: after
        the departure, the station must retain a small capacity-based reserve so
        a nearly empty station is not presented as a reliable trip option.
        """
        if requested < 1:
            raise ValueError("requested must be at least one")
        if not 0.0 <= min_reserve_ratio <= 1.0:
            raise ValueError("min_reserve_ratio must be between zero and one")
        reserve = ceil(self.capacity * min_reserve_ratio)
        return self.bikes - requested >= reserve

    def borrow(self, requested: int = 1) -> int:
        if requested < 0:
            raise ValueError("requested cannot be negative")
        completed = min(requested, self.bikes)
        self.bikes -= completed
        self.borrows += completed
        return completed

    def return_bikes(self, requested: int = 1) -> int:
        if requested < 0:
            raise ValueError("requested cannot be negative")
        completed = min(requested, self.empty_docks)
        self.bikes += completed
        self.returns += completed
        return completed

    def rebalance(self, bike_change: int) -> None:
        """Apply an operator move; never exceed the station's physical capacity."""
        next_bikes = self.bikes + bike_change
        if not 0 <= next_bikes <= self.capacity:
            raise ValueError("Rebalancing exceeds station capacity")
        self.bikes = next_bikes


def is_youbike_trip_available(
    station: YouBikeStation,
    trip_distance_m: float,
    riders: int = 1,
) -> bool:
    """Apply the shared distance and origin-inventory eligibility rules."""
    if trip_distance_m < 0:
        raise ValueError("trip_distance_m cannot be negative")
    return (
        trip_distance_m <= MAX_YOUBIKE_TRIP_DISTANCE_M
        and station.can_support_departure(riders)
    )
