"""Run Xinyi traffic agents from a historical typical-day baseline.

Supports three agent types via ``--agent``:
  - ``policy`` (default): SimpleTrafficPolicyAgent – compares signal-timing candidates.
  - ``commuter``: CommuterAgent – evaluates mode choice for a commuter population.
  - ``visitor``: VisitorAgent - evaluates mode choice for a visitor population.
"""

import argparse
import csv
from pathlib import Path

from simulation.agent import SimpleTrafficPolicyAgent
from simulation.baseline import ScenarioConfig
from simulation.commuter import CommuterAgent, CommuterProfile
from simulation.visitor import VisitorAgent, VisitorProfile
from simulation.historical import build_typical_day, load_historical_observations
from simulation.parking import ParkingFacility
from simulation.roads import RoadSegment, load_road_segments
from simulation.ubike import YouBikeStation


def main() -> None:
    args = _arguments()

    if args.agent == "commuter":
        _run_commuter(args)
    elif args.agent == "visitor":
        _run_visitor(args)
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
        args.population = Path("data/historical/xinyi_commuter_population.csv")
        if not args.population.exists():
            raise SystemExit(f"找不到預設母體檔案 {args.population}。請先執行 scripts/generate_commuter_population.py。")

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


# ── Visitor agent ─────────────────────────────────────────────────────────

def _run_visitor(args) -> None:
    if args.demo:
        _run_visitor_demo()
        return

    if not args.population:
        args.population = Path("data/historical/xinyi_visitor_population.csv")
        if not args.population.exists():
            raise SystemExit(f"找不到預設母體檔案 {args.population}。請先執行 scripts/generate_visitor_population.py。")

    profiles = _load_visitor_population(args.population)
    observations = load_historical_observations(args.historical)
    metrics = build_typical_day(observations, args.day_type, include_events=args.day_type == "event")
    baseline = next((m for m in metrics if m.time_slot == args.time_slot and m.segment_id == args.segment_id), None)
    if baseline is None:
        raise SystemExit("找不到指定的 day type、time slot、segment_id 組合。")

    road = _road_by_name(args.road_name)
    scenario = ScenarioConfig(
        scenario_id=f"visitor-{args.day_type}-{args.time_slot}",
        service_date="historical-typical-day",
        demand_profile={args.time_slot: 1.0},
    )
    parking = [ParkingFacility("xinyi-garage", 500, 200, hourly_fee=60, walk_distance_m=150)]
    station = YouBikeStation("xinyi-ub", 30, 15)
    result = VisitorAgent().run_batch(
        profiles, scenario, road,
        flow_vph=baseline.traffic_volume_vph,
        parking_facilities=parking,
        youbike_station=station,
    )
    _print_visitor_outcome(result)

def _run_visitor_demo() -> None:
    scenario = ScenarioConfig(
        "visitor-demo", "2026-08-18",
        start_time="10:00", end_time="15:00",
        demand_profile={"11:30": 1.2, "12:00": 1.5, "12:30": 1.1},
    )
    road = RoadSegment("demo", 5000, 2, 50, 1800, {"name": "示範道路"})
    # Parking fee is high, so stay duration matters.
    parking = [ParkingFacility("mall-garage", 500, 100, hourly_fee=80, walk_distance_m=50)]
    station = YouBikeStation("mall-ub", 30, 10)
    
    profiles = [
        VisitorProfile("單人快閃客", "seg_a", "seg_b", "11:30", 
                       group_size=1, stay_duration_hours=1.0, 
                       value_of_time=5.0, walk_penalty_multiplier=1.2),
        VisitorProfile("小家庭購物", "seg_c", "seg_d", "12:00", 
                       group_size=4, stay_duration_hours=4.0, 
                       value_of_time=4.0, walk_penalty_multiplier=2.5),
        VisitorProfile("情侶約會", "seg_e", "seg_f", "12:00", 
                       group_size=2, stay_duration_hours=3.0, 
                       value_of_time=3.0, walk_penalty_multiplier=1.5, transit_preference=0.4),
        VisitorProfile("朋友聚餐", "seg_a", "seg_d", "11:45", 
                       group_size=3, stay_duration_hours=2.0, 
                       value_of_time=6.0, walk_penalty_multiplier=1.8),
    ]
    
    result = VisitorAgent().run_batch(
        profiles, scenario, road, flow_vph=1000,  # Less congested at noon
        parking_facilities=parking, youbike_station=station,
        transit_time_minutes=25.0, transit_fare=20.0, transit_walk_minutes=10.0,
    )
    print("這是訪客合成示範，並非歷史資料結果。\n")
    _print_visitor_outcome(result)

def _load_visitor_population(csv_path: Path) -> list:
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as f:
        rows = csv.DictReader(f)
        return [
            VisitorProfile(
                visitor_id=row["visitor_id"],
                origin_segment_id=row["origin_segment_id"],
                destination_segment_id=row["destination_segment_id"],
                preferred_departure=row["preferred_departure"],
                group_size=int(row["group_size"]),
                stay_duration_hours=float(row["stay_duration_hours"]),
                flexibility_minutes=int(row["flexibility_minutes"]),
                value_of_time=float(row["value_of_time"]),
                price_sensitivity=float(row["price_sensitivity"]),
                walk_penalty_multiplier=float(row["walk_penalty_multiplier"]),
                transit_preference=float(row["transit_preference"]),
            )
            for row in rows
        ]

def _print_visitor_outcome(result: dict) -> None:
    print("信義商圈訪客 Agent")
    print("=" * 42)
    print(f"道路：{result['road_name']} | 訪客群體數：{result['total_visitors']}")
    print(f"\n運具分擔率（Mode Share）")
    for mode, share in result["mode_share"].items():
        label = {"drive": "開車", "transit": "大眾運輸", "youbike": "YouBike"}.get(mode, mode)
        print(f"  {label}：{share:.1%}")
    print(f"\n平均 Generalized Cost：{result['average_generalized_cost']:.1f} NTD")
    print(f"\n出發時間分佈")
    for tick, count in result["departure_distribution"].items():
        print(f"  {tick}：{count} 群體")
    print(f"\n個別決策")
    for d in result["decisions"]:
        print(f"  {d.visitor_id}：{d.chosen_mode}（出發 {d.departure_time}，GC={d.generalized_cost:.1f}）")

# ── General Arguments ─────────────────────────────────────────────────────

def _arguments():
    parser = argparse.ArgumentParser(description="Run a historical-baseline Xinyi traffic agent.")
    parser.add_argument("--agent", choices=["policy", "commuter", "visitor"], default="policy",
                        help="Agent type: policy, commuter, or visitor")
    parser.add_argument("--historical", type=Path, default=Path("data/historical/xinyi_historical_observations.csv"), help="Historical observations CSV")
    parser.add_argument("--day-type", choices=["weekday", "weekend", "event"], default="weekday")
    parser.add_argument("--time-slot", default="17:30", help="HH:MM, for example 17:30")
    parser.add_argument("--segment-id", default="city_hall_road_eastbound", help="ID from historical observations")
    parser.add_argument("--road-name", default="市府路", help="Matching OSM road name, for example 市府路")
    parser.add_argument("--population", type=Path, help="Population CSV (commuter or visitor agent only)")
    parser.add_argument("--demo", action="store_true", help="Run the synthetic demonstration only")
    args = parser.parse_args()
    
    # Check if we should fallback to demo if the default historical file doesn't exist
    if not args.demo and not args.historical.exists():
        print(f"找不到預設歷史資料 ({args.historical})，自動切換至 Demo 模式。")
        args.demo = True
        
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
