"""Step 5: YouBike station capacity, borrowing, returns, and turnover KPI."""

from dataclasses import dataclass


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

