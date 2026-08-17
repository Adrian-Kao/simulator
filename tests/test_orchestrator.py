import tempfile
import unittest
from pathlib import Path

from simulation.goals import GoalConfig
from simulation.orchestrator import (
    FALLBACK_DEMAND_VPH,
    load_baseline_context,
    run_simulation,
)
from simulation.scenario import (
    ParkingPolicy,
    RedLinePolicy,
    ScenarioDiff,
    SignalTimingPolicy,
)


MISSING_HISTORICAL = Path("tests/does-not-exist/historical.csv")
MISSING_ROADS = Path("tests/does-not-exist/roads.geojson")


HISTORICAL_CSV = """timestamp,day_type,segment_id,travel_time_minutes,travel_speed_kph,traffic_volume_vph,footfall_per_hour,parking_occupancy_rate,youbike_borrows,youbike_returns,event_flag
2025-08-04T17:30:00,weekday,city_hall_road_eastbound,3.40,18.2,1500.0,4200.0,0.93,35.0,110.0,false
2025-08-05T17:30:00,weekday,city_hall_road_eastbound,3.60,17.4,1600.0,4400.0,0.95,33.0,115.0,false
2025-08-04T17:30:00,weekday,songgao_road_eastbound,2.10,21.0,900.0,5200.0,0.90,40.0,44.0,false
"""


def diff(green=55, red_line=120.0, parking=80) -> ScenarioDiff:
    return ScenarioDiff(
        scenario_id="scenario-a",
        policies=(
            SignalTimingPolicy("i-7", baseline_seconds=40, scenario_seconds=green),
            RedLinePolicy("shifu-road", length_meters=red_line),
            ParkingPolicy("parking-new-1", spaces=parking),
        ),
    )


def simulate(scenario_diff=None, **kwargs):
    kwargs.setdefault("historical_path", MISSING_HISTORICAL)
    kwargs.setdefault("road_network_path", MISSING_ROADS)
    kwargs.setdefault("road_id", "shifu-road")
    return run_simulation(scenario_diff or diff(), **kwargs)


class FallbackBaselineTests(unittest.TestCase):
    def test_missing_data_uses_named_fallbacks_and_warns(self):
        context = load_baseline_context(
            day_type="weekday",
            time_slot="17:30",
            road_id="shifu-road",
            historical_path=MISSING_HISTORICAL,
            road_network_path=MISSING_ROADS,
        )

        self.assertEqual(context.demand_vph, FALLBACK_DEMAND_VPH)
        self.assertEqual(context.sources["demand"], "fallback-default")
        self.assertEqual(context.sources["road_geometry"], "fallback-default")
        self.assertTrue(context.uses_fallback)
        self.assertEqual(context.observation_count, 0)
        self.assertEqual(context.observed, {})
        self.assertTrue(
            any("FALLBACK_DEMAND_VPH" in warning for warning in context.warnings),
            context.warnings,
        )

    def test_response_metadata_marks_the_fallback(self):
        outcome = simulate()

        self.assertTrue(outcome.metadata["uses_fallback"])
        self.assertEqual(outcome.metadata["sources"]["demand"], "fallback-default")
        self.assertFalse(outcome.metadata["assumptions"]["calibrated"])
        self.assertTrue(
            any("mvp-proxy-v1" in warning for warning in outcome.warnings),
            outcome.warnings,
        )


class HistoricalBaselineTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.csv_path = Path(self._temp.name) / "xinyi_historical_observations.csv"
        self.csv_path.write_text(HISTORICAL_CSV, encoding="utf-8")

    def tearDown(self):
        self._temp.cleanup()

    def test_historical_demand_is_preferred_over_fallback(self):
        context = load_baseline_context(
            day_type="weekday",
            time_slot="17:30",
            road_id="shifu-road",
            historical_path=self.csv_path,
            road_network_path=MISSING_ROADS,
        )

        # Mean of 1500 and 1600 for the mapped segment.
        self.assertAlmostEqual(context.demand_vph, 1_550.0)
        self.assertEqual(context.segment_id, "city_hall_road_eastbound")
        self.assertEqual(context.observation_count, 2)
        self.assertEqual(
            context.sources["demand"],
            "data/historical/xinyi_historical_observations.csv",
        )
        self.assertAlmostEqual(context.observed["travel_time_minutes"], 3.5)

    def test_unmapped_road_falls_back_to_a_representative_segment_with_warning(self):
        context = load_baseline_context(
            day_type="weekday",
            time_slot="17:30",
            road_id="not-a-known-road",
            historical_path=self.csv_path,
            road_network_path=MISSING_ROADS,
        )

        self.assertGreater(context.demand_vph, 0)
        self.assertEqual(
            context.sources["demand"],
            "data/historical/xinyi_historical_observations.csv",
        )

    def test_missing_time_slot_falls_back_and_warns(self):
        context = load_baseline_context(
            day_type="weekday",
            time_slot="03:05",
            road_id="shifu-road",
            historical_path=self.csv_path,
            road_network_path=MISSING_ROADS,
        )

        self.assertEqual(context.demand_vph, FALLBACK_DEMAND_VPH)
        self.assertTrue(
            any("time_slot=03:05" in warning for warning in context.warnings),
            context.warnings,
        )

    def test_historical_run_reports_observed_baseline(self):
        outcome = simulate(historical_path=self.csv_path)

        self.assertEqual(
            outcome.metadata["sources"]["demand"],
            "data/historical/xinyi_historical_observations.csv",
        )
        self.assertAlmostEqual(outcome.metadata["baseline_demand_vph"], 1_550.0)
        self.assertAlmostEqual(
            outcome.metadata["observed_baseline"]["travel_time_minutes"], 3.5
        )


class OutcomeTests(unittest.TestCase):
    def test_empty_diff_produces_identical_baseline_and_scenario(self):
        outcome = simulate(ScenarioDiff(scenario_id="scenario-a"))

        self.assertEqual(outcome.baseline, outcome.scenario)
        self.assertEqual(outcome.delta.travel_time_percent, 0.0)
        self.assertEqual(outcome.recommended, "tie")
        self.assertTrue(
            any("no change versus baseline" in warning for warning in outcome.warnings),
            outcome.warnings,
        )

    def test_scenario_improves_every_headline_kpi(self):
        outcome = simulate(diff(green=68, red_line=400.0, parking=250))

        self.assertLess(
            outcome.scenario.travel_time_minutes, outcome.baseline.travel_time_minutes
        )
        self.assertGreater(
            outcome.scenario.travel_speed_kph, outcome.baseline.travel_speed_kph
        )
        self.assertLess(outcome.scenario.congestion_vc, outcome.baseline.congestion_vc)
        self.assertLess(
            outcome.scenario.queue_vehicles, outcome.baseline.queue_vehicles
        )
        self.assertEqual(outcome.recommended, "scenario")

    def test_goal_status_is_returned_when_goals_are_supplied(self):
        outcome = simulate(goals=GoalConfig(queue_percent=-15, travel_speed_percent=1))

        self.assertEqual(len(outcome.goal_status), 2)
        self.assertEqual(
            {status.metric for status in outcome.goal_status},
            {"queue_percent", "travel_speed_percent"},
        )

    def test_no_goals_means_not_met(self):
        outcome = simulate()
        self.assertEqual(outcome.goal_status, ())
        self.assertFalse(outcome.goals_met)

    def test_variables_are_reported_for_baseline_and_scenario(self):
        outcome = simulate(diff(green=55, red_line=120.0, parking=80))

        self.assertEqual(outcome.baseline_variables.signal_green_seconds, 40)
        self.assertEqual(outcome.baseline_variables.red_line_meters, 0.0)
        self.assertEqual(outcome.baseline_variables.parking_spaces, 0)

        self.assertEqual(outcome.scenario_variables.signal_green_seconds, 55)
        self.assertEqual(outcome.scenario_variables.red_line_meters, 120.0)
        self.assertEqual(outcome.scenario_variables.parking_spaces, 80)

    def test_determinism_for_same_input_and_seed(self):
        first = simulate(diff()).to_dict()
        second = simulate(diff()).to_dict()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
