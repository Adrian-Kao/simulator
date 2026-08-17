"""Collect public historical datasets for the Xinyi traffic-policy simulator."""

import csv
import hashlib
import json
import argparse
from pathlib import Path
from urllib.request import Request, urlopen


TRAFFIC_SURVEY_CATALOG = "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=e2311fce-e104-41cd-b8c7-57ad433fc49a"
MRT_OD_CATALOG = "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=eb481f58-1238-4cff-8caa-fa7bb20cb4f4"
TRAFFIC_SURVEY_COMPONENTS = {
    "taipei_traffic_survey_113_intersections.pdf": "https://online.bote.gov.taipei/botedata/%E4%BA%A4%E9%80%9A%E6%B5%81%E9%87%8F/113%E5%B9%B4%E5%BA%A6/113%E5%B9%B4%E5%BA%A6%E8%87%BA%E5%8C%97%E5%B8%82%E4%BA%A4%E9%80%9A%E6%B5%81%E9%87%8F%E5%8F%8A%E7%89%B9%E6%80%A7%E8%AA%BF%E6%9F%A5%E8%B7%AF%E5%8F%A3.pdf",
    "taipei_traffic_survey_113_segments.pdf": "https://online.bote.gov.taipei/botedata/%E4%BA%A4%E9%80%9A%E6%B5%81%E9%87%8F/113%E5%B9%B4%E5%BA%A6/113%E5%B9%B4%E5%BA%A6%E8%87%BA%E5%8C%97%E5%B8%82%E4%BA%A4%E9%80%9A%E6%B5%81%E9%87%8F%E5%8F%8A%E7%89%B9%E6%80%A7%E8%AA%BF%E6%9F%A5%E8%B7%AF%E6%AE%B5.pdf",
    "taipei_traffic_survey_113_pedestrians.pdf": "https://online.bote.gov.taipei/botedata/%E4%BA%A4%E9%80%9A%E6%B5%81%E9%87%8F/113%E5%B9%B4%E5%BA%A6/113%E5%B9%B4%E5%BA%A6%E8%87%BA%E5%8C%97%E5%B8%82%E4%BA%A4%E9%80%9A%E6%B5%81%E9%87%8F%E5%8F%8A%E7%89%B9%E6%80%A7%E8%AA%BF%E6%9F%A5%E8%A1%8C%E4%BA%BA.pdf",
}
YOUBIKE_202507 = {
    "youbike_od_weekday_202507.geojson": "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=bb00cae4-2f06-484d-9b97-26fc9221757d",
    "youbike_od_weekend_202507.geojson": "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=4b71676f-f52b-4125-ac2b-dd794d2e8501",
}


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "TaipeiXinyiSimulatorHistoricalCollector/1.0"})
    with urlopen(request, timeout=120) as response:
        return response.read()


def decode(payload: bytes) -> str:
    for encoding in ("utf-8-sig", "cp950", "big5", "utf-16"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unsupported text encoding")


def collect(output_root: Path = Path("data/historical"), year: int = 2025, include_mrt_raw: bool = False) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    manifest = {"year": year, "sources": {}}

    traffic_catalog = fetch(TRAFFIC_SURVEY_CATALOG)
    traffic_catalog_path = output_root / "taipei_traffic_flow_survey_catalog.csv"
    traffic_catalog_path.write_bytes(traffic_catalog)
    traffic_report_url = _taipei_url(decode(traffic_catalog), "網址")
    traffic_report = fetch(traffic_report_url)
    traffic_report_path = output_root / "taipei_traffic_flow_survey_latest_reference.pdf"
    traffic_report_path.write_bytes(traffic_report)
    manifest["sources"][traffic_report_path.name] = {"url": traffic_report_url, "sha256": _sha256(traffic_report)}
    for filename, url in TRAFFIC_SURVEY_COMPONENTS.items():
        payload = fetch(url)
        (output_root / filename).write_bytes(payload)
        manifest["sources"][filename] = {"url": url, "sha256": _sha256(payload)}

    mrt_catalog = fetch(MRT_OD_CATALOG)
    mrt_catalog_path = output_root / "taipei_mrt_hourly_od_catalog.csv"
    mrt_catalog_path.write_bytes(mrt_catalog)
    if include_mrt_raw:
        rows = list(csv.DictReader(decode(mrt_catalog).splitlines()))
        selected = [row for row in rows if int(row["西元年"]) == year]
        if not selected:
            raise ValueError(f"No MRT hourly OD files listed for {year}")
        mrt_dir = output_root / "mrt_hourly_od" / str(year)
        mrt_dir.mkdir(parents=True, exist_ok=True)
        for row in selected:
            payload = fetch(row["URL"])
            path = mrt_dir / f"{year}-{int(row['月']):02d}.csv"
            path.write_bytes(payload)
            manifest["sources"][str(path.relative_to(output_root))] = {"url": row["URL"], "sha256": _sha256(payload)}

    for filename, url in YOUBIKE_202507.items():
        payload = fetch(url)
        (output_root / filename).write_bytes(payload)
        manifest["sources"][filename] = {"url": url, "sha256": _sha256(payload)}

    manifest_path = output_root / f"collection_manifest_{year}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _taipei_url(text: str, url_column: str) -> str:
    for row in csv.DictReader(text.splitlines()):
        if "臺北" in " ".join(row.values()):
            return row[url_column]
    raise ValueError("Taipei source URL was not found")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--include-mrt-raw", action="store_true", help="Downloads ~300 MB per month of MRT OD data")
    args = parser.parse_args()
    result = collect(year=args.year, include_mrt_raw=args.include_mrt_raw)
    print(f"Collected {len(result['sources'])} historical source files for {result['year']}.")
