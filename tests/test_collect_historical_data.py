import unittest

from collect_historical_data import _taipei_url


class HistoricalCollectorTests(unittest.TestCase):
    def test_finds_taipei_source_url(self):
        text = "項目,縣市別,網址\n交通流量調查資料,臺北市,https://example.test/taipei.pdf\n"
        self.assertEqual(_taipei_url(text, "網址"), "https://example.test/taipei.pdf")


if __name__ == "__main__":
    unittest.main()
