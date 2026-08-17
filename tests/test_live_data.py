import json
import tempfile
import unittest
from pathlib import Path

from simulation.live_data import assess_data_readiness, load_xinyi_signal_sites, load_xinyi_youbike_stations
from collect_live_data import _taipei_feed_url


class LiveDataTests(unittest.TestCase):
    def test_filters_youbike_to_xinyi_bbox(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "youbike.json"
            path.write_text(json.dumps([
                {"sno": "in", "longitude": 121.56, "latitude": 25.04, "Quantity": 10, "available_rent_bikes": 3},
                {"sno": "out", "longitude": 121.50, "latitude": 25.04, "Quantity": 10, "available_rent_bikes": 3},
            ]), encoding="utf-8")
            stations = load_xinyi_youbike_stations(path)
        self.assertEqual([station.station_id for station in stations], ["in"])

    def test_readiness_reports_missing_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "youbike.json").write_text("[]", encoding="utf-8")
            readiness = assess_data_readiness(root)
        self.assertIn("YouBike 即時快照", readiness.available)
        self.assertIn("路段旅行時間", readiness.missing)

    def test_reads_big5_traffic_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.csv"
            path.write_bytes("縣市,介接網址\n臺北市,https://example.test/feed\n".encode("cp950"))
            url = _taipei_feed_url(path)
        self.assertEqual(url, "https://example.test/feed")

    def test_empty_travel_time_feed_is_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "traffic_travel_time.xml").write_text("<ETagPairLives/>", encoding="utf-8")
            readiness = assess_data_readiness(root)
        self.assertIn("路段旅行時間", readiness.missing)

    def test_filters_signal_sites_to_xinyi_bbox(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "signals.csv"
            path.write_text(
                "icid,路口名稱,經度,緯度,三合一報表連結（網址）\n"
                "in,測試路口,121.56,25.04,https://example.test/in\n"
                "out,外圍路口,121.50,25.04,https://example.test/out\n"
                "shifted,欄位位移,,,GA0001,121.57,25.041,https://example.test/shifted\n",
                encoding="utf-8",
            )
            sites = load_xinyi_signal_sites(path)
        self.assertEqual([site.intersection_id for site in sites], ["in", "shifted"])


if __name__ == "__main__":
    unittest.main()
