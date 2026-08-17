import unittest

from simulation.scenario import (
    DEFAULT_BASELINE_GREEN_SECONDS,
    PARKING_SPACES_BOUNDS,
    RED_LINE_METERS_BOUNDS,
    SIGNAL_GREEN_SECONDS_BOUNDS,
    ParkingPolicy,
    PolicyVariables,
    RedLinePolicy,
    ScenarioDiff,
    SignalTimingPolicy,
    apply_variables,
    baseline_variables,
    scenario_variables,
    validate_recommendation,
    variable_warnings,
)


class ScenarioDiffTests(unittest.TestCase):
    def test_unchanged_policies_are_dropped(self):
        diff = ScenarioDiff(
            scenario_id="scenario-a",
            policies=(
                SignalTimingPolicy("i-1", baseline_seconds=40, scenario_seconds=40),
                RedLinePolicy("shifu-road", length_meters=0.0),
                ParkingPolicy("parking-1", spaces=0),
            ),
        ).changed_only()

        self.assertEqual(diff.policies, ())
        self.assertTrue(diff.is_empty())

    def test_only_real_changes_survive(self):
        diff = ScenarioDiff(
            scenario_id="scenario-a",
            policies=(
                SignalTimingPolicy("i-1", baseline_seconds=40, scenario_seconds=55),
                RedLinePolicy("shifu-road", length_meters=120.0),
                ParkingPolicy("parking-1", spaces=0),
            ),
        ).changed_only()

        self.assertEqual(len(diff.policies), 2)
        self.assertFalse(diff.is_empty())

    def test_baseline_and_scenario_variables(self):
        diff = ScenarioDiff(
            scenario_id="scenario-a",
            policies=(
                SignalTimingPolicy("i-1", baseline_seconds=45, scenario_seconds=55),
                RedLinePolicy("shifu-road", length_meters=120.0),
                RedLinePolicy("songgao-road", length_meters=30.0),
                ParkingPolicy("parking-1", spaces=80),
            ),
        )

        base = baseline_variables(diff)
        self.assertEqual(base.signal_green_seconds, 45)
        self.assertEqual(base.red_line_meters, 0.0)
        self.assertEqual(base.parking_spaces, 0)

        scenario = scenario_variables(diff)
        self.assertEqual(scenario.signal_green_seconds, 55)
        self.assertEqual(scenario.red_line_meters, 150.0)
        self.assertEqual(scenario.parking_spaces, 80)

    def test_empty_diff_uses_default_baseline_green(self):
        diff = ScenarioDiff(scenario_id="scenario-a")
        self.assertEqual(
            baseline_variables(diff).signal_green_seconds,
            DEFAULT_BASELINE_GREEN_SECONDS,
        )
        self.assertEqual(
            scenario_variables(diff).signal_green_seconds,
            DEFAULT_BASELINE_GREEN_SECONDS,
        )

    def test_multiple_signal_policies_warn(self):
        diff = ScenarioDiff(
            scenario_id="scenario-a",
            policies=(
                SignalTimingPolicy("i-1", 40, 55),
                SignalTimingPolicy("i-2", 40, 60),
            ),
        )
        warnings = variable_warnings(diff)
        self.assertTrue(any("i-1" in warning for warning in warnings))

    def test_validate_rejects_unsupported_policy(self):
        diff = ScenarioDiff(scenario_id="scenario-a", policies=("not-a-policy",))
        with self.assertRaises(ValueError):
            diff.validate()

    def test_validate_requires_scenario_id(self):
        with self.assertRaises(ValueError):
            ScenarioDiff(scenario_id="").validate()


class RecommendationValidationTests(unittest.TestCase):
    def test_in_bounds_recommendation_passes_through(self):
        validated = validate_recommendation(
            {
                "signal_green_seconds": 55,
                "red_line_meters": 150.0,
                "parking_spaces": 80,
                "reasoning": "test",
            }
        )

        self.assertEqual(validated.variables.signal_green_seconds, 55)
        self.assertEqual(validated.variables.red_line_meters, 150.0)
        self.assertEqual(validated.variables.parking_spaces, 80)
        self.assertEqual(validated.notes, ())

    def test_out_of_bounds_values_are_clamped_and_reported(self):
        validated = validate_recommendation(
            {
                "signal_green_seconds": 900,
                "red_line_meters": -50.0,
                "parking_spaces": 10_000,
            }
        )

        self.assertEqual(
            validated.variables.signal_green_seconds, SIGNAL_GREEN_SECONDS_BOUNDS[1]
        )
        self.assertEqual(validated.variables.red_line_meters, RED_LINE_METERS_BOUNDS[0])
        self.assertEqual(validated.variables.parking_spaces, PARKING_SPACES_BOUNDS[1])
        self.assertEqual(len(validated.notes), 3)

    def test_disallowed_fields_are_ignored(self):
        validated = validate_recommendation(
            {
                "signal_green_seconds": 50,
                "red_line_meters": 10.0,
                "parking_spaces": 5,
                "capacity_vph": 9_999,
                "baseline_travel_time_minutes": 0.1,
            }
        )

        self.assertTrue(
            any("Ignored fields" in note for note in validated.notes),
            validated.notes,
        )

    def test_non_numeric_values_fall_back(self):
        validated = validate_recommendation(
            {
                "signal_green_seconds": "sixty",
                "red_line_meters": None,
                "parking_spaces": 20,
            }
        )

        self.assertEqual(
            validated.variables.signal_green_seconds, DEFAULT_BASELINE_GREEN_SECONDS
        )
        self.assertEqual(validated.variables.parking_spaces, 20)


class ApplyVariablesTests(unittest.TestCase):
    def test_patch_preserves_anchors_and_baseline(self):
        diff = ScenarioDiff(
            scenario_id="scenario-a",
            policies=(
                SignalTimingPolicy("i-7", baseline_seconds=45, scenario_seconds=50),
                RedLinePolicy("shifu-road", length_meters=100.0),
                ParkingPolicy("parking-new-1", spaces=30),
            ),
        )

        patched = apply_variables(
            diff,
            PolicyVariables(
                signal_green_seconds=60,
                red_line_meters=200.0,
                parking_spaces=90,
            ),
        )

        signal = patched.signal_policies[0]
        self.assertEqual(signal.intersection_id, "i-7")
        self.assertEqual(signal.baseline_seconds, 45)
        self.assertEqual(signal.scenario_seconds, 60)
        self.assertEqual(patched.red_line_policies[0].road_id, "shifu-road")
        self.assertEqual(patched.red_line_policies[0].length_meters, 200.0)
        self.assertEqual(patched.parking_policies[0].parking_id, "parking-new-1")
        self.assertEqual(patched.parking_policies[0].spaces, 90)

    def test_patch_clamps_out_of_bounds_variables(self):
        patched = apply_variables(
            ScenarioDiff(scenario_id="scenario-a"),
            PolicyVariables(
                signal_green_seconds=1_000,
                red_line_meters=10_000.0,
                parking_spaces=-5,
            ),
            road_id="shifu-road",
        )

        self.assertEqual(
            patched.signal_policies[0].scenario_seconds,
            SIGNAL_GREEN_SECONDS_BOUNDS[1],
        )
        self.assertEqual(
            patched.red_line_policies[0].length_meters, RED_LINE_METERS_BOUNDS[1]
        )
        self.assertEqual(patched.parking_policies[0].spaces, PARKING_SPACES_BOUNDS[0])
        self.assertEqual(patched.red_line_policies[0].road_id, "shifu-road")


if __name__ == "__main__":
    unittest.main()
