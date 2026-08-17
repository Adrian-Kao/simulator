import unittest

from simulation.baseline import ScenarioConfig


class BaselineScenarioTests(unittest.TestCase):
    def test_ticks_and_seed_are_reproducible(self):
        config = ScenarioConfig("baseline-weekday", "2026-08-17", random_seed=7)
        self.assertEqual(config.ticks()[0], "08:00")
        self.assertEqual(config.ticks()[-1], "22:55")
        self.assertEqual(len(config.ticks()), 180)
        self.assertEqual(config.rng().random(), config.rng().random())

    def test_invalid_tick_is_rejected(self):
        with self.assertRaises(ValueError):
            ScenarioConfig("bad", "2026-08-17", tick_minutes=7).validate()


if __name__ == "__main__":
    unittest.main()
