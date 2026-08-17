"""Download a timestamped public-data snapshot for the Xinyi traffic simulator.

Run this every five minutes through a scheduler to build a historical calibration
dataset. It only downloads official public endpoints; no credentials are stored.
"""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from simulation.live_data import XINYI_IMPACT_BBOX, load_xinyi_youbike_stations


SOURCES = {
    "youbike.json": "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json",
    "signal_timing.json": "https://tcgbusfs.blob.core.windows.net/dotapp/timing_plan.json",
    "signal_timing_table.json": "https://tcgbusfs.blob.core.windows.net/dotapp/timing_plan_table.json",
    "signal_timing.csv": "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=9522d9e8-131e-4890-9379-f17c523238a0",
    "parking_static.json": "https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json",
    "parking_dynamic.json": "https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json",
    "vd_static.xml": "https://tcgbusfs.blob.core.windows.net/blobtisv/VD.xml",
    "traffic_travel_time_catalog.csv": "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=1eecf5ff-4ab8-4c1f-8abe-4e3d404979e3",
}


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "TaipeiXinyiSimulatorDataCollector/1.0"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def save_snapshot(root: Path = Path("data/live")) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(root) / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {"captured_at_utc": timestamp, "sources": {}, "xinyi_impact_bbox": XINYI_IMPACT_BBOX}
    for filename, url in SOURCES.items():
        payload = fetch(url)
        (output_dir / filename).write_bytes(payload)
        manifest["sources"][filename] = {"url": url, "sha256": hashlib.sha256(payload).hexdigest()}

    traffic_url = _taipei_feed_url(output_dir / "traffic_travel_time_catalog.csv")
    if traffic_url:
        payload = fetch(traffic_url)
        (output_dir / "traffic_travel_time.json").write_bytes(payload)
        manifest["sources"]["traffic_travel_time.json"] = {"url": traffic_url, "sha256": hashlib.sha256(payload).hexdigest()}

    stations = load_xinyi_youbike_stations(output_dir / "youbike.json")
    manifest["xinyi_youbike_station_count"] = len(stations)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_dir


def _taipei_feed_url(catalog_path: Path):
    payload = Path(catalog_path).read_bytes()
    text = None
    for encoding in ("utf-8-sig", "utf-16", "cp950", "big5"):
        try:
            text = payload.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("Unsupported travel-time catalog encoding")
    rows = list(csv.DictReader(text.splitlines()))
    for row in rows:
        combined = " ".join(row.values())
        if "臺北" in combined or "台北" in combined or "Taipei" in combined:
            for key, value in row.items():
                if "網址" in key or "url" in key.lower():
                    return value.strip()
    return None


if __name__ == "__main__":
    path = save_snapshot()
    print(f"Saved live data snapshot: {path}")
