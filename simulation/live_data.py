"""Load and quality-check live public data for the Xinyi simulation area."""

import json
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from .ubike import YouBikeStation


# Download envelope for the policy impact area; the street polygon remains the
# authoritative policy boundary described in SIMULATION_SCOPE.md.
XINYI_IMPACT_BBOX = (121.553, 25.031, 121.580, 25.044)  # min_lon, min_lat, max_lon, max_lat


@dataclass(frozen=True)
class DataReadiness:
    available: Tuple[str, ...]
    missing: Tuple[str, ...]

    @property
    def ready_for_calibration(self) -> bool:
        return not self.missing


@dataclass(frozen=True)
class SignalSite:
    intersection_id: str
    name: str
    longitude: float
    latitude: float
    timing_plan_url: str


def load_xinyi_youbike_stations(snapshot_path: Path) -> List[YouBikeStation]:
    with Path(snapshot_path).open(encoding="utf-8") as file:
        rows = json.load(file)
    min_lon, min_lat, max_lon, max_lat = XINYI_IMPACT_BBOX
    stations = []
    for row in rows:
        lon = float(row["longitude"])
        lat = float(row["latitude"])
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            capacity = int(row.get("Quantity", row.get("quantity", 0)))
            bikes = int(row.get("available_rent_bikes", 0))
            if capacity >= bikes >= 0:
                stations.append(YouBikeStation(str(row["sno"]), capacity, bikes))
    return stations


def load_xinyi_signal_sites(csv_path: Path) -> List[SignalSite]:
    min_lon, min_lat, max_lon, max_lat = XINYI_IMPACT_BBOX
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as file:
        rows = csv.reader(file)
        next(rows, None)  # header contains duplicate blank column names in the official file
        sites = []
        for row in rows:
            longitude, latitude = _coordinates_from_row(row)
            if min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat:
                sites.append(SignalSite(
                    intersection_id=row[0],
                    name=row[2].strip(),
                    longitude=longitude,
                    latitude=latitude,
                    timing_plan_url=next((value.strip() for value in row if value and value.startswith("http")), ""),
                ))
    return sites


def _coordinates_from_row(row: list) -> Tuple[float, float]:
    """The official CSV has occasional shifted columns; locate a valid lon/lat pair."""
    for first, second in zip(row, row[1:]):
        try:
            longitude, latitude = float(first), float(second)
        except (TypeError, ValueError):
            continue
        if 120 <= longitude <= 123 and 24 <= latitude <= 26:
            return longitude, latitude
    raise ValueError(f"No valid Taipei lon/lat pair for signal {row[0] if row else '<unknown>'}")


def assess_data_readiness(snapshot_dir: Path) -> DataReadiness:
    """Checks the minimum files required before statistical calibration."""
    required = {
        "youbike": "YouBike 即時快照",
        "signal_timing": "號誌時制計畫",
        "traffic_travel_time": "路段旅行時間",
        "vd_live": "VD 即時交通量",
        "parking_dynamic": "停車即時可用車位",
        "parking_static": "停車靜態資料",
        "vd_static": "VD 偵測器位置",
    }
    available, missing = [], []
    for filename, label in required.items():
        files = [item for item in Path(snapshot_dir).glob(f"{filename}.*") if _is_usable(item, filename)]
        if files:
            available.append(label)
        else:
            missing.append(label)
    return DataReadiness(tuple(available), tuple(missing))


def _is_usable(path: Path, filename: str) -> bool:
    if path.stat().st_size == 0:
        return False
    # Taipei's travel-time endpoint can return a valid but empty XML document;
    # an empty feed cannot calibrate or drive the simulator.
    if filename == "traffic_travel_time":
        return b"<ETagPairLive>" in path.read_bytes()
    return True
