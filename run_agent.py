"""Run a terminal demo of the simple Xinyi traffic-policy agent."""

from pathlib import Path

from simulation.agent import SimpleTrafficPolicyAgent
from simulation.baseline import ScenarioConfig
from simulation.live_data import assess_data_readiness, load_xinyi_signal_sites, load_xinyi_youbike_stations
from simulation.roads import load_road_segments


def main() -> None:
    scenario = ScenarioConfig(
        scenario_id="xinyi-demo-weekday",
        service_date="2026-08-17",
        random_seed=48219,
        demand_profile={"17:30": 1.0},
    )
    roads = load_road_segments(Path("data/GIS/xinyi_impact_road_network.geojson"))
    road = next((item for item in roads if item.properties.get("name:zh") == "市府路"), roads[0])
    outcome = SimpleTrafficPolicyAgent().run(scenario, road, arrivals_per_tick=80)

    print("信義商圈交通政策 Agent — 示範結果")
    print("=" * 42)
    print(f"情境：{outcome['scenario']['scenario_id']} | tick：{outcome['scenario']['tick_minutes']} 分鐘")
    print(f"代表路段：{outcome['road_name']}")
    print("注意：這是模型流程示範，尚未以真實分時車流與號誌資料校準。\n")
    for result in outcome["results"]:
        print(result.policy_name)
        print(f"  路口殘餘排隊：{result.queue_vehicles:.1f} 輛")
        print(f"  路段 Travel Time：{result.travel_time_minutes:.2f} 分鐘")
        print(f"  路段 Travel Speed：{result.travel_speed_kph:.1f} km/h")
        print(f"  壅塞程度 V/C：{result.congestion_vc:.2f}")
    recommended = outcome["recommended"]
    print("\nAgent 建議：" + recommended.policy_name)
    print("理由：在相同需求下，它的路口殘餘排隊最低；仍需以真實資料校準後才能作為政策建議。")
    _print_live_data_status()


def _print_live_data_status() -> None:
    snapshots = sorted(Path("data/live").glob("*"))
    if not snapshots:
        print("\n尚無即時資料快照。請先執行 python3 collect_live_data.py")
        return
    snapshot = snapshots[-1]
    readiness = assess_data_readiness(snapshot)
    youbike = load_xinyi_youbike_stations(snapshot / "youbike.json")
    signal_sites = load_xinyi_signal_sites(snapshot / "signal_timing.csv")
    print(f"\n真實資料快照：{snapshot.name}")
    print(f"  信義影響區 YouBike 站點：{len(youbike)}")
    print(f"  信義影響區號誌路口：{len(signal_sites)}")
    print("  可用資料：" + "、".join(readiness.available))
    print("  尚缺資料：" + "、".join(readiness.missing))


if __name__ == "__main__":
    main()
