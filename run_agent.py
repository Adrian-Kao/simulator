"""Run the Xinyi policy agent from a historical typical-day baseline."""

import argparse
from pathlib import Path

from simulation.agent import SimpleTrafficPolicyAgent
from simulation.baseline import ScenarioConfig
from simulation.historical import build_typical_day, load_historical_observations
from simulation.roads import RoadSegment, load_road_segments


def main() -> None:
    args = _arguments()
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


def _arguments():
    parser = argparse.ArgumentParser(description="Run a historical-baseline Xinyi traffic policy comparison.")
    parser.add_argument("--historical", type=Path, help="Historical observations CSV")
    parser.add_argument("--day-type", choices=["weekday", "weekend", "event"])
    parser.add_argument("--time-slot", help="HH:MM, for example 17:30")
    parser.add_argument("--segment-id", help="ID from historical observations")
    parser.add_argument("--road-name", help="Matching OSM road name, for example 市府路")
    parser.add_argument("--demo", action="store_true", help="Run the synthetic demonstration only")
    args = parser.parse_args()
    if not args.demo:
        missing = [name for name in ("historical", "day_type", "time_slot", "segment_id", "road_name") if getattr(args, name) is None]
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
