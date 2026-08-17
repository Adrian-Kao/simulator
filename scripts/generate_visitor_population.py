"""Generate a synthetic visitor population for the Xinyi district simulation.

Produces ``data/historical/xinyi_visitor_population.csv``.
Visitors have mid-day/afternoon/evening arrivals, variable group sizes,
and shorter stay durations compared to commuters.
"""

import csv
import sys
from pathlib import Path
from random import Random

SEGMENTS = [
    "city_hall_road_eastbound", "city_hall_road_westbound",
    "xinyi_rd_sec5_eastbound", "xinyi_rd_sec5_westbound",
    "songren_rd_northbound", "songren_rd_southbound",
    "songshou_rd_eastbound", "songshou_rd_westbound",
    "songgao_rd_northbound", "songgao_rd_southbound",
    "songzhi_rd_eastbound", "songzhi_rd_westbound",
    "zhongxiao_e_rd_sec5_eastbound", "keelung_rd_sec1_northbound",
]

HEADER = [
    "visitor_id", "origin_segment_id", "destination_segment_id",
    "preferred_departure", "group_size", "stay_duration_hours",
    "flexibility_minutes", "value_of_time", "price_sensitivity",
    "walk_penalty_multiplier", "transit_preference"
]

def _clamp_hhmm(minutes: int) -> str:
    minutes = max(600, min(minutes, 1260))  # 10:00–21:00
    minutes = round(minutes / 5) * 5
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

def _gauss_int(rng: Random, mu: float, sigma: float) -> int:
    return int(round(rng.gauss(mu, sigma)))

def generate(population_size: int = 500, seed: int = 48219) -> list:
    rng = Random(seed)
    rows = []
    for i in range(population_size):
        # Time distribution: Lunch (20%), Afternoon (50%), Dinner/Evening (30%)
        rand_t = rng.random()
        if rand_t < 0.2:
            pref_minutes = _gauss_int(rng, mu=11.5 * 60, sigma=30)
        elif rand_t < 0.7:
            pref_minutes = _gauss_int(rng, mu=14.5 * 60, sigma=60)
        else:
            pref_minutes = _gauss_int(rng, mu=18.5 * 60, sigma=45)

        # Group size: 40% 1 person, 40% 2 people, 20% 3-4 people
        rand_g = rng.random()
        if rand_g < 0.4:
            group_size = 1
        elif rand_g < 0.8:
            group_size = 2
        else:
            group_size = rng.choice([3, 4])

        origin = rng.choice(SEGMENTS)
        dest = rng.choice([s for s in SEGMENTS if s != origin])

        rows.append({
            "visitor_id": f"visitor_{i:04d}",
            "origin_segment_id": origin,
            "destination_segment_id": dest,
            "preferred_departure": _clamp_hhmm(pref_minutes),
            "group_size": group_size,
            "stay_duration_hours": round(rng.uniform(1.5, 5.0), 1),
            "flexibility_minutes": rng.choice([15, 30, 45, 60]),
            "value_of_time": round(rng.uniform(2.0, 8.0), 1),
            "price_sensitivity": round(rng.uniform(0.5, 2.0), 2),
            "walk_penalty_multiplier": round(rng.uniform(1.2, 3.0), 1),
            "transit_preference": round(rng.uniform(0.0, 0.4), 2),
        })
    return rows

def main() -> None:
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 48219
    out_path = Path("data/historical/xinyi_visitor_population.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = generate(size, seed)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)
    print(f"已產生 {len(rows)} 位訪客群體 → {out_path}")

if __name__ == "__main__":
    main()
