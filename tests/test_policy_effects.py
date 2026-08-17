import unittest

from simulation.policy_effects import (
    RED_LINE_MAX_CAPACITY_GAIN,
    Kpi,
    build_delta,
    effective_demand_vph,
    effective_road,
    evaluate,
    parking_cruising_relief_vph,
    red_line_capacity_gain,
)
from simulation.roads import RoadSegment
from simulation.scenario import PolicyVariables


def road() -> RoadSegment:
    return RoadSegment(
        segment_id="test-corridor",
        length_m=500.0,
        lanes=2,
        speed_limit_kph=40.0,
        capacity_vph=1_800.0,
        properties={"name:zh": "測試路段"},
    )


def variables(green=40, red_line=0.0, parking=0) -> PolicyVariables:
    return PolicyVariables(
        signal_green_seconds=green,
        red_line_meters=red_line,
        parking_spaces=parking,
    )


DEMAND_VPH = 1_800.0
TICK_MINUTES = 5


class RedLineEffectTests(unittest.TestCase):
    def test_no_red_line_means_no_capacity_change(self):
        self.assertEqual(red_line_capacity_gain(0.0), 0.0)

        original = road()
        self.assertEqual(
            effective_road(original, 0.0).capacity_vph,
            original.capacity_vph,
        )

    def test_red_line_raises_capacity(self):
        original = road()
        adjusted = effective_road(original, 200.0)
        self.assertAlmostEqual(
            adjusted.capacity_vph,
            original.capacity_vph * 1.08,
        )

    def test_capacity_gain_is_capped(self):
        self.assertAlmostEqual(red_line_capacity_gain(100.0), 0.04)
        self.assertAlmostEqual(red_line_capacity_gain(10_000.0), RED_LINE_MAX_CAPACITY_GAIN)

    def test_red_line_lowers_travel_time_and_vc(self):
        without = evaluate(road(), DEMAND_VPH, TICK_MINUTES, variables())
        with_red_line = evaluate(
            road(), DEMAND_VPH, TICK_MINUTES, variables(red_line=300.0)
        )

        self.assertLess(with_red_line.travel_time_minutes, without.travel_time_minutes)
        self.assertGreater(with_red_line.travel_speed_kph, without.travel_speed_kph)
        self.assertLess(with_red_line.congestion_vc, without.congestion_vc)

    def test_red_line_does_not_change_queue(self):
        without = evaluate(road(), DEMAND_VPH, TICK_MINUTES, variables())
        with_red_line = evaluate(
            road(), DEMAND_VPH, TICK_MINUTES, variables(red_line=300.0)
        )
        self.assertAlmostEqual(
            without.queue_vehicles, with_red_line.queue_vehicles, places=9
        )


class ParkingEffectTests(unittest.TestCase):
    def test_relief_is_capped_as_share_of_demand(self):
        relief = parking_cruising_relief_vph(DEMAND_VPH, 100_000)
        self.assertAlmostEqual(relief, DEMAND_VPH * 0.15)

    def test_added_spaces_reduce_effective_demand(self):
        self.assertLess(
            effective_demand_vph(DEMAND_VPH, 100),
            DEMAND_VPH,
        )
        self.assertEqual(effective_demand_vph(DEMAND_VPH, 0), DEMAND_VPH)

    def test_parking_lowers_travel_time_and_queue(self):
        without = evaluate(road(), DEMAND_VPH, TICK_MINUTES, variables())
        with_parking = evaluate(
            road(), DEMAND_VPH, TICK_MINUTES, variables(parking=200)
        )

        self.assertLess(with_parking.travel_time_minutes, without.travel_time_minutes)
        self.assertLess(with_parking.congestion_vc, without.congestion_vc)
        self.assertLess(with_parking.queue_vehicles, without.queue_vehicles)


class SignalEffectTests(unittest.TestCase):
    def test_more_green_reduces_queue(self):
        short = evaluate(road(), DEMAND_VPH, TICK_MINUTES, variables(green=20))
        long = evaluate(road(), DEMAND_VPH, TICK_MINUTES, variables(green=68))
        self.assertLess(long.queue_vehicles, short.queue_vehicles)

    def test_green_does_not_change_link_travel_time(self):
        short = evaluate(road(), DEMAND_VPH, TICK_MINUTES, variables(green=20))
        long = evaluate(road(), DEMAND_VPH, TICK_MINUTES, variables(green=68))
        self.assertAlmostEqual(
            short.travel_time_minutes, long.travel_time_minutes, places=9
        )


class DeterminismTests(unittest.TestCase):
    def test_identical_inputs_give_identical_kpis(self):
        first = evaluate(
            road(), DEMAND_VPH, TICK_MINUTES, variables(55, 150.0, 80)
        )
        second = evaluate(
            road(), DEMAND_VPH, TICK_MINUTES, variables(55, 150.0, 80)
        )
        self.assertEqual(first, second)

    def test_all_three_variables_move_at_least_one_kpi(self):
        base = evaluate(road(), DEMAND_VPH, TICK_MINUTES, variables())

        signal = evaluate(road(), DEMAND_VPH, TICK_MINUTES, variables(green=68))
        red_line = evaluate(
            road(), DEMAND_VPH, TICK_MINUTES, variables(red_line=400.0)
        )
        parking = evaluate(road(), DEMAND_VPH, TICK_MINUTES, variables(parking=150))

        self.assertNotEqual(signal, base)
        self.assertNotEqual(red_line, base)
        self.assertNotEqual(parking, base)


class DeltaTests(unittest.TestCase):
    def test_percent_change_signs(self):
        baseline = Kpi(
            travel_time_minutes=4.0,
            travel_speed_kph=20.0,
            congestion_vc=1.0,
            queue_vehicles=100.0,
        )
        scenario = Kpi(
            travel_time_minutes=3.6,
            travel_speed_kph=22.0,
            congestion_vc=0.9,
            queue_vehicles=80.0,
        )

        delta = build_delta(baseline, scenario)

        self.assertAlmostEqual(delta.travel_time_percent, -10.0)
        self.assertAlmostEqual(delta.travel_speed_percent, 10.0)
        self.assertAlmostEqual(delta.congestion_vc_percent, -10.0)
        self.assertAlmostEqual(delta.queue_percent, -20.0)

    def test_zero_baseline_is_reported_as_no_change(self):
        zero = Kpi(0.0, 0.0, 0.0, 0.0)
        delta = build_delta(zero, Kpi(1.0, 1.0, 1.0, 1.0))
        self.assertEqual(delta.travel_time_percent, 0.0)
        self.assertEqual(delta.queue_percent, 0.0)


class InputValidationTests(unittest.TestCase):
    def test_negative_demand_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(road(), -1.0, TICK_MINUTES, variables())

    def test_non_positive_tick_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(road(), DEMAND_VPH, 0, variables())


if __name__ == "__main__":
    unittest.main()
