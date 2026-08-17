"""Generate a synthetic commuter population for the Xinyi district simulation.

Produces ``data/historical/xinyi_commuter_population.csv`` with one row per
commuter.  Origin / destination pairs are drawn from the 14 arterial segments
used in the historical observations.  Preferred departure times follow a
bimodal Gaussian centred on the AM (07:30–08:30) and PM (17:00–18:00) peaks.
"""

import csv
import math
import sys
from pathlib import Path
from random import Random

# Xinyi arterial segments (matches generate_historical_data.py).
SEGMENTS = [
    "city_hall_road_eastbound",
    "city_hall_road_westbound",
    "xinyi_rd_sec5_eastbound",
    "xinyi_rd_sec5_westbound",
    "songren_rd_northbound",
    "songren_rd_southbound",
    "songshou_rd_eastbound",
    "songshou_rd_westbound",
    "songgao_rd_northbound",
    "songgao_rd_southbound",
    "songzhi_rd_eastbound",
    "songzhi_rd_westbound",
    "zhongxiao_e_rd_sec5_eastbound",
    "keelung_rd_sec1_northbound",
]

HEADER = [
    "commuter_id",
    "origin_segment_id",
    "destination_segment_id",
    "preferred_departure",
    "flexibility_minutes",
    "value_of_time",
    "price_sensitivity",
    "transit_preference",
]


def _clamp_hhmm(minutes: int) -> str:
    """Clamp to [06:00, 22:55] and round to nearest 5-minute tick."""
    minutes = max(360, min(minutes, 1375))  # 06:00–22:55
    minutes = round(minutes / 5) * 5
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _gauss_int(rng: Random, mu: float, sigma: float) -> int:
    return int(round(rng.gauss(mu, sigma)))


def generate(population_size: int = 500, seed: int = 48219) -> list:
    """Return a list of dicts, one per commuter."""
    rng = Random(seed)
    rows = []
    for i in range(population_size):
        # AM peak (70 %) or PM peak (30 %)
        if rng.random() < 0.70:
            preferred_minutes = _gauss_int(rng, mu=8 * 60, sigma=20)
        else:
            preferred_minutes = _gauss_int(rng, mu=17 * 60 + 30, sigma=20)

        origin = rng.choice(SEGMENTS)
        dest = rng.choice([s for s in SEGMENTS if s != origin])

        rows.append({
            "commuter_id": f"commuter_{i:04d}",
            "origin_segment_id": origin,
            "destination_segment_id": dest,
            "preferred_departure": _clamp_hhmm(preferred_minutes),
            "flexibility_minutes": rng.choice([5, 10, 15, 15, 20, 30]),
            "value_of_time": round(rng.uniform(2.0, 10.0), 1),
            "price_sensitivity": round(rng.uniform(0.5, 2.0), 2),
            "transit_preference": round(rng.uniform(0.0, 0.6), 2),
        })
    return rows


def main() -> None:
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 48219
    out_path = Path("data/historical/xinyi_commuter_population.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = generate(size, seed)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)
    print(f"已產生 {len(rows)} 位通勤者 → {out_path}")


if __name__ == "__main__":
    main()
