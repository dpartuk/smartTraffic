"""
Download all Tel Aviv open data datasets to data/raw/.
Idempotent: skips files that already exist with non-zero size.
"""

import json
import os
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
TRAFFIC_DIR = RAW_DIR / "traffic"

TRAFFIC_LAYERS = [
    "segs_kph_monthly_Apr2024_WM",
    "segs_kph_monthly_May2024_WM",
    "segs_kph_monthly_June2024_wm",
    "segs_kph_monthly_Jul2025_wm",
    "segs_kph_monthly_Aug2024",
    "segs_kph_monthly_Sep2024_wm",
    "segs_kph_monthly_Oct2024_wm",
    "segs_kph_monthly_Nov2024_wm",
    "segs_kph_monthly_Dec2024_wm",
    "segs_kph_monthly_Jan2025_wm",
    "segs_kph_monthly_Feb2025_wm",
    "segs_kph_monthly_Mar2025_wm",
    "segs_kph_monthly_Apr2025_wm",
    "segs_kph_monthly_May2025_wm",
    "segs_kph_monthly_Jun2025_wm",
    "segs_kph_monthly_Jul2025_wm",
    "segs_kph_monthly_Aug2025_wm",
    "segs_kph_monthly_Sep2025_wm",
    "segs_kph_monthly_Oct2025_wm",
    "segs_kph_monthly_Nov2025_wm",
    "segs_kph_monthly_Dec2025_wm",
    "segs_kph_monthly_Feb2026_wm",
    "segs_kph_monthly_Mar2026_wm",
    "segs_kph_monthly_Apr2026_wm",
    "segs_kph_monthly_May2026_wm",
]

ARCGIS_BASE = "https://gisn.tel-aviv.gov.il/arcgis/rest/services/OpenData"

CSV_DATASETS = {
    "businesses.csv": {
        "url": "https://saopendata.blob.core.windows.net/open-data-public-site/maagar_asakim.csv",
        "encoding": "utf-16-le",
        "delimiter": ";",
    },
    "construction.csv": {
        "url": "https://saopendata.blob.core.windows.net/open-data-public-site/binyanimLamas.csv",
        "encoding": "windows-1255",
        "delimiter": ",",
    },
    "hotline_106.csv": {
        "url": "https://saopendata.blob.core.windows.net/open-data-public-site/PniyotKriyot106.csv",
        "encoding": "utf-16-le",
        "delimiter": ";",
    },
    "closed_streets.csv": {
        "url": "https://saopendata.blob.core.windows.net/open-data-public-site/rechov_sagur.csv",
        "encoding": "utf-16-le",
        "delimiter": ",",
    },
    "digitel.csv": {
        "url": "https://saopendata.blob.core.windows.net/open-data-public-site/divurim_open_click_new.csv",
        "encoding": "utf-16-le",
        "delimiter": ";",
    },
    "budget_capital.csv": {
        "url": "https://saopendata.blob.core.windows.net/open-data-public-site/hoshen_od_tabar.csv",
        "encoding": "utf-16-le",
        "delimiter": ";",
    },
    "population.csv": {
        "url": "https://opendatasource.tel-aviv.gov.il/OpenData_Ducaments/Uchlusiya_KvutzatUchlusiya.csv",
        "encoding": "windows-1255",
        "delimiter": "|",
    },
    "pop_growth.csv": {
        "url": "https://opendatasource.tel-aviv.gov.il/OpenData_Ducaments/MarkiveyGidul.csv",
        "encoding": "windows-1255",
        "delimiter": "|",
    },
    "pop_migration.csv": {
        "url": "https://opendatasource.tel-aviv.gov.il/OpenData_Ducaments/Nayadut_Uchlusiya_Min_Gil.csv",
        "encoding": "windows-1255",
        "delimiter": "|",
    },
    "dwelling.csv": {
        "url": "https://saopendata.blob.core.windows.net/open-data-public-site/yehidot_diyur.csv",
        "encoding": "windows-1255",
        "delimiter": ",",
    },
}

SES_URL = "https://opendatasource.tel-aviv.gov.il/OpenData_Ducaments/Accessible/ses%20open%20data2017-2019%2020240617.xlsx"


def download_traffic_layer(layer_name: str):
    """Download a single ArcGIS traffic layer as GeoJSON with pagination."""
    out_file = TRAFFIC_DIR / f"{layer_name}.geojson"
    if out_file.exists() and out_file.stat().st_size > 0:
        print(f"  [skip] {layer_name} already exists")
        return

    url = f"{ARCGIS_BASE}/{layer_name}/MapServer/1/query"
    all_features = []
    offset = 0

    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "geojson",
            "resultRecordCount": 2000,
            "resultOffset": offset,
        }
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if not features:
            break

        all_features.extend(features)
        offset += len(features)

        if not data.get("properties", {}).get("exceededTransferLimit", False) \
           and "exceededTransferLimit" not in resp.text:
            break

    geojson = {
        "type": "FeatureCollection",
        "features": all_features,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

    print(f"  [done] {layer_name}: {len(all_features)} features")


def download_csv(filename: str, config: dict):
    """Download a CSV, decode from original encoding, save as UTF-8."""
    out_file = RAW_DIR / filename
    if out_file.exists() and out_file.stat().st_size > 0:
        print(f"  [skip] {filename} already exists")
        return

    resp = requests.get(config["url"], timeout=120)
    resp.raise_for_status()

    text = resp.content.decode(config["encoding"])
    # Remove BOM if present
    if text.startswith("﻿"):
        text = text[1:]

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(text)

    line_count = text.count("\n")
    print(f"  [done] {filename}: ~{line_count} lines")


def download_ses():
    """Download the SES Excel file."""
    out_file = RAW_DIR / "ses.xlsx"
    if out_file.exists() and out_file.stat().st_size > 0:
        print("  [skip] ses.xlsx already exists")
        return

    resp = requests.get(SES_URL, timeout=60)
    resp.raise_for_status()

    with open(out_file, "wb") as f:
        f.write(resp.content)

    print(f"  [done] ses.xlsx: {len(resp.content)} bytes")


def main():
    TRAFFIC_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Downloading traffic speed layers ===")
    for layer in TRAFFIC_LAYERS:
        try:
            download_traffic_layer(layer)
        except Exception as e:
            print(f"  [ERROR] {layer}: {e}")
        time.sleep(0.5)

    print("\n=== Downloading CSV datasets ===")
    for filename, config in CSV_DATASETS.items():
        try:
            download_csv(filename, config)
        except Exception as e:
            print(f"  [ERROR] {filename}: {e}")

    print("\n=== Downloading SES Excel ===")
    try:
        download_ses()
    except Exception as e:
        print(f"  [ERROR] ses.xlsx: {e}")

    print("\n=== Download summary ===")
    total_files = 0
    total_size = 0
    for f in RAW_DIR.rglob("*"):
        if f.is_file():
            total_files += 1
            total_size += f.stat().st_size
    print(f"Total files: {total_files}")
    print(f"Total size: {total_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
