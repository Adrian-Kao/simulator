from fastapi.testclient import TestClient
import pytest

from api.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_simulation_response_shape():
    response = client.post(
        "/api/simulations",
        json={
            "scenario_id": "scenario-a",
            "day_type": "weekday",
            "time_slot": "17:30",
            "random_seed": 42,
            "road_id": "shifu-road",
            "road_name": "市府路",
            "policies": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "baseline" in body
    assert "scenario" in body
    assert "delta" in body
    assert "behavior" in body
    assert "development" in body
    assert sum(body["behavior"]["scenario_mode_share"].values()) == pytest.approx(1.0)


def test_signal_green_changes_queue():
    slow = client.post(
        "/api/simulations",
        json={
            "scenario_id": "slow",
            "day_type": "weekday",
            "time_slot": "17:30",
            "policies": [
                {
                    "type": "signal-timing",
                    "intersection_id": "i-1",
                    "phases": [
                        {
                            "name": "直行",
                            "seconds": 20,
                            "color": "green",
                        }
                    ],
                }
            ],
        },
    ).json()

    fast = client.post(
        "/api/simulations",
        json={
            "scenario_id": "fast",
            "day_type": "weekday",
            "time_slot": "17:30",
            "policies": [
                {
                    "type": "signal-timing",
                    "intersection_id": "i-1",
                    "phases": [
                        {
                            "name": "直行",
                            "seconds": 60,
                            "color": "green",
                        }
                    ],
                }
            ],
        },
    ).json()

    assert fast["scenario"]["queue_vehicles"] < slow["scenario"]["queue_vehicles"]


def test_invalid_payload_is_422():
    response = client.post(
        "/api/simulations",
        json={
            "scenario_id": "bad",
            "day_type": "not-valid",
            "time_slot": "17:30",
            "policies": [],
        },
    )
    assert response.status_code == 422


def test_policy_changes_agent_choices_and_downstream_demand():
    baseline = client.post(
        "/api/simulations",
        json={
            "scenario_id": "baseline-behavior",
            "day_type": "weekday",
            "time_slot": "17:30",
            "policies": [],
        },
    ).json()
    restricted = client.post(
        "/api/simulations",
        json={
            "scenario_id": "restricted-behavior",
            "day_type": "weekday",
            "time_slot": "17:30",
            "policies": [
                {
                    "type": "traffic-restriction",
                    "intersection_id": "i-1",
                    "restriction_type": "forbid-entry",
                    "target_road_id": "road-1",
                }
            ],
        },
    ).json()

    baseline_share = baseline["behavior"]["scenario_mode_share"]
    restricted_share = restricted["behavior"]["scenario_mode_share"]
    assert restricted_share["drive"] < baseline_share["drive"]
    assert restricted["development"]["parking_demand_percent"] < 0
    assert restricted["development"]["signals"]
    assert any(
        "direct road network capacity effect is not modelled" in warning
        for warning in restricted["warnings"]
    )
