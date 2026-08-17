from fastapi.testclient import TestClient

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
