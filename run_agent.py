"""Run Xinyi traffic agents from a historical typical-day baseline.

Supports two agent types via ``--agent``:
  - ``policy`` (default): SimpleTrafficPolicyAgent – compares signal-timing candidates.
  - ``commuter``: CommuterAgent – evaluates mode choice for a commuter population.
"""

import argparse
import csv
from pathlib import Path

from simulation.agent import SimpleTrafficPolicyAgent
from simulation.baseline import ScenarioConfig
from simulation.commuter import CommuterAgent, CommuterProfile
from simulation.historical import build_typical_day, load_historical_observations
from simulation.parking import ParkingFacility
from simulation.roads import RoadSegment, load_road_segments
from simulation.ubike import YouBikeStation


def main() -> None:
    args = _arguments()

    if args.agent == "commuter":
        _run_commuter(args)
    else:
        _run_policy(args)


# ── Policy agent ──────────────────────────────────────────────────────────

def _run_policy(args) -> None:
    if args.demo:
        scenario = ScenarioConfig("demo-only", "2026-08-17", demand_profile={"17:30": 1.0})
        road = RoadSegment("demo", 500, 1, 40, 900, {"name": "示範道路"})
        outcome = SimpleTrafficPolicyAgent().run(scenario, road, arrivals_per_tick=80)
        print("這是合成示範，並非歷史資料結果。")
        print("Agent 建議：" + outcome["recommended"].policy_name)
        return

    observations = load_historical_observations(args.historical)
    metrics = build_typical_day(observations, args.day_type, include_events=args.day_type == "event")
    baseline = next((item for item in metrics if item.time_slot == args.time_slot and item.segment_id == args.segment_id), None)
    if baseline is None:
        raise SystemExit("找不到指定的 day type、time slot、segment_id 組合。")
    road = _road_by_name(args.road_name)
    scenario = ScenarioConfig(
        scenario_id=f"historical-{args.day_type}-{args.time_slot}-{args.segment_id}",
        service_date="historical-typical-day",
        demand_profile={args.time_slot: 1.0},
    )
    outcome = SimpleTrafficPolicyAgent().run_historical(scenario, road, baseline)
    _print_outcome(outcome)


# ── Commuter agent ────────────────────────────────────────────────────────

def _run_commuter(args) -> None:
    if args.demo:
        _run_commuter_demo()
        return

    if not args.population:
        raise SystemExit("通勤者模式需要 --population 參數（通勤者母體 CSV）。")

    profiles = _load_commuter_population(args.population)
    observations = load_historical_observations(args.historical)
    metrics = build_typical_day(observations, args.day_type, include_events=args.day_type == "event")
    baseline = next((m for m in metrics if m.time_slot == args.time_slot and m.segment_id == args.segment_id), None)
    if baseline is None:
        raise SystemExit("找不到指定的 day type、time slot、segment_id 組合。")

    road = _road_by_name(args.road_name)
    scenario = ScenarioConfig(
        scenario_id=f"commuter-{args.day_type}-{args.time_slot}",
        service_date="historical-typical-day",
        demand_profile={args.time_slot: 1.0},
    )
    parking = [ParkingFacility("xinyi-garage", 500, 200, hourly_fee=40, walk_distance_m=150)]
    station = YouBikeStation("xinyi-ub", 30, 15)
    result = CommuterAgent().run_batch(
        profiles, scenario, road,
        flow_vph=baseline.traffic_volume_vph,
        parking_facilities=parking,
        youbike_station=station,
    )
    _print_commuter_outcome(result)


def _run_commuter_demo() -> None:
    scenario = ScenarioConfig(
        "commuter-demo", "2026-08-18",
        demand_profile={"08:00": 1.5, "08:05": 1.4, "08:10": 0.8, "08:15": 0.5, "17:30": 1.3},
    )
    # 5 km commute — YouBike 20 min, congested driving ~6.5 min, transit 20 min.
    road = RoadSegment("demo", 5000, 2, 50, 1800, {"name": "示範道路"})
    parking = [ParkingFacility("demo-garage", 200, 80, hourly_fee=60, walk_distance_m=300)]
    station = YouBikeStation("demo-ub", 30, 12)
    profiles = [
        # Low VOT, low price sensitivity → drive despite parking cost
        CommuterProfile("通勤者A_開車族", "seg_a", "seg_b", "08:00",
                        value_of_time=2.0, price_sensitivity=0.3, transit_preference=0.0),
        # Moderate VOT, high transit affinity → transit wins
        CommuterProfile("通勤者B_捷運族", "seg_c", "seg_d", "08:10",
                        value_of_time=3.0, price_sensitivity=1.0, transit_preference=0.6),
        # High VOT, high price sensitivity → YouBike (free, moderate time)
        CommuterProfile("通勤者C_單車族", "seg_e", "seg_f", "08:05",
                        value_of_time=3.0, price_sensitivity=2.5, transit_preference=0.0),
        # Moderate profile with transit lean → transit
        CommuterProfile("通勤者D_彈性族", "seg_a", "seg_d", "08:00",
                        flexibility_minutes=30, value_of_time=4.0, transit_preference=0.5),
        # Evening commuter → drive (lower congestion assumed via flow)
        CommuterProfile("通勤者E_晚峰族", "seg_b", "seg_e", "17:30",
                        value_of_time=5.0, transit_preference=0.0),
    ]
    result = CommuterAgent().run_batch(
        profiles, scenario, road, flow_vph=1600,
        parking_facilities=parking, youbike_station=station,
        transit_time_minutes=15.0, transit_fare=15.0, transit_walk_minutes=4.0,
    )
    print("這是合成示範，並非歷史資料結果。\n")
    _print_commuter_outcome(result)


def _load_commuter_population(csv_path: Path) -> list:
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as f:
        rows = csv.DictReader(f)
        return [
            CommuterProfile(
                commuter_id=row["commuter_id"],
                origin_segment_id=row["origin_segment_id"],
                destination_segment_id=row["destination_segment_id"],
                preferred_departure=row["preferred_departure"],
                flexibility_minutes=int(row["flexibility_minutes"]),
                value_of_time=float(row["value_of_time"]),
                price_sensitivity=float(row["price_sensitivity"]),
                transit_preference=float(row["transit_preference"]),
            )
            for row in rows
        ]


def _print_commuter_outcome(result: dict) -> None:
    print("信義商圈通勤者 Agent")
    print("=" * 42)
    print(f"道路：{result['road_name']} | 通勤者人數：{result['total_commuters']}")
    print(f"\n運具分擔率（Mode Share）")
    for mode, share in result["mode_share"].items():
        label = {"drive": "開車", "transit": "大眾運輸", "youbike": "YouBike"}.get(mode, mode)
        print(f"  {label}：{share:.1%}")
    print(f"\n平均 Generalized Cost：{result['average_generalized_cost']:.1f} NTD")
    print(f"\n出發時間分佈")
    for tick, count in result["departure_distribution"].items():
        print(f"  {tick}：{count} 人")
    print(f"\n個別決策")
    for d in result["decisions"]:
        print(f"  {d.commuter_id}：{d.chosen_mode}（出發 {d.departure_time}，GC={d.generalized_cost:.1f}）")


def _arguments():
    parser = argparse.ArgumentParser(description="Run a historical-baseline Xinyi traffic agent.")
    parser.add_argument("--agent", choices=["policy", "commuter"], default="policy",
                        help="Agent type: policy (signal comparison) or commuter (mode choice)")
    parser.add_argument("--historical", type=Path, help="Historical observations CSV")
    parser.add_argument("--day-type", choices=["weekday", "weekend", "event"])
    parser.add_argument("--time-slot", help="HH:MM, for example 17:30")
    parser.add_argument("--segment-id", help="ID from historical observations")
    parser.add_argument("--road-name", help="Matching OSM road name, for example 市府路")
    parser.add_argument("--population", type=Path, help="Commuter population CSV (commuter agent only)")
    parser.add_argument("--demo", action="store_true", help="Run the synthetic demonstration only")
    args = parser.parse_args()
    if not args.demo:
        required = ["historical", "day_type", "time_slot", "segment_id", "road_name"]
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            parser.error("歷史模式需要：" + ", ".join("--" + item.replace("_", "-") for item in missing))
    return args


def _road_by_name(road_name: str):
    roads = load_road_segments(Path("data/GIS/xinyi_impact_road_network.geojson"))
    road = next((item for item in roads if item.properties.get("name:zh") == road_name or item.properties.get("name") == road_name), None)
    if road is None:
        raise SystemExit(f"找不到道路：{road_name}。請使用 OSM 資料中的道路名稱。")
    return road


def _print_outcome(outcome: dict) -> None:
    history = outcome["historical_baseline"]
    print("信義商圈歷史典型日政策 Agent")
    print("=" * 42)
    print(f"典型日：{history['day_type']} | 時段：{history['time_slot']} | 樣本數：{history['observation_count']}")
    print(f"道路：{outcome['road_name']} | segment_id：{history['segment_id']}")
    print("\n歷史基準觀測")
    print(f"  Travel Time：{history['observed_travel_time_minutes']:.2f} 分鐘")
    print(f"  Travel Speed：{history['observed_travel_speed_kph']:.1f} km/h")
    print(f"  交通量：{history['observed_traffic_volume_vph']:.0f} vph")
    print(f"  人流：{history['observed_footfall_per_hour']:.0f} 人／小時")
    print(f"  停車使用率：{history['observed_parking_occupancy_rate']:.0%}")
    for result in outcome["results"]:
        print(f"\n{result.policy_name}")
        print(f"  模擬殘餘排隊：{result.queue_vehicles:.1f} 輛")
        print(f"  模擬 Travel Time：{result.travel_time_minutes:.2f} 分鐘")
        print(f"  模擬 Travel Speed：{result.travel_speed_kph:.1f} km/h")
        print(f"  模擬 V/C：{result.congestion_vc:.2f}")
    print("\nAgent 建議：" + outcome["recommended"].policy_name)


if __name__ == "__main__":
    main()
