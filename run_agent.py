"""Run a terminal demo of the simple Xinyi traffic-policy agent."""

from pathlib import Path

from simulation.agent import SimpleTrafficPolicyAgent
from simulation.baseline import ScenarioConfig
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


if __name__ == "__main__":
    main()
