import unittest

from simulation.ubike import YouBikeStation


class YouBikeModelTests(unittest.TestCase):
    def test_borrow_is_limited_by_bikes(self):
        station = YouBikeStation("xinyi-test", capacity=10, bikes=2)
        self.assertEqual(station.borrow(5), 2)
        self.assertEqual(station.bikes, 0)

    def test_return_is_limited_by_empty_docks(self):
        station = YouBikeStation("xinyi-test", capacity=10, bikes=9)
        self.assertEqual(station.return_bikes(5), 1)
        self.assertEqual(station.bikes, 10)

    def test_turnover_rate_counts_borrows_and_returns(self):
        station = YouBikeStation("xinyi-test", capacity=10, bikes=5)
        station.borrow(3)
        station.return_bikes(2)
        self.assertEqual(station.turnover_rate, 0.5)


if __name__ == "__main__":
    unittest.main()
