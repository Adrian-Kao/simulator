import unittest
from datetime import datetime

from simulation.historical import HistoricalObservation, build_typical_day


class HistoricalBaselineTests(unittest.TestCase):
    def test_builds_typical_weekday_and_excludes_events_by_default(self):
        observations = [
            HistoricalObservation(datetime(2026, 8, 3, 17, 30), "weekday", "city-hall", 5, 12, 900, 8000, .8, 20, 18),
            HistoricalObservation(datetime(2026, 8, 10, 17, 30), "weekday", "city-hall", 7, 10, 1100, 9000, .9, 24, 20),
            HistoricalObservation(datetime(2026, 8, 17, 17, 30), "weekday", "city-hall", 20, 4, 2000, 20000, 1, 40, 35, True),
        ]
        baseline = build_typical_day(observations, "weekday")
        self.assertEqual(len(baseline), 1)
        self.assertEqual(baseline[0].observation_count, 2)
        self.assertEqual(baseline[0].travel_time_minutes, 6)
        self.assertEqual(baseline[0].footfall_per_hour, 8500)

    def test_can_build_event_day(self):
        observation = HistoricalObservation(datetime(2026, 8, 17, 17, 30), "event", "city-hall", 20, 4, 2000, 20000, 1, 40, 35, True)
        baseline = build_typical_day([observation], "event", include_events=True)
        self.assertEqual(baseline[0].traffic_volume_vph, 2000)


if __name__ == "__main__":
    unittest.main()
