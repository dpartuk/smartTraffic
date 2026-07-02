"""
Verify the Phase 1 pipeline output: check file sizes, row counts,
plot traffic segments, verify UTF-8 encoding.
"""

import sqlite3
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
GPKG_PATH = PROC_DIR / "smarttraffic.gpkg"


def check_raw_files():
    print("=== Raw files ===")
    total = 0
    for f in sorted(RAW_DIR.rglob("*")):
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            label = f"  {f.relative_to(RAW_DIR)}"
            if size_kb > 1024:
                print(f"{label}: {size_kb/1024:.1f} MB")
            else:
                print(f"{label}: {size_kb:.0f} KB")
            total += 1
    print(f"  Total raw files: {total}")


def check_processed_csvs():
    print("\n=== Processed CSVs (UTF-8 validation) ===")
    for f in sorted(PROC_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(f, encoding="utf-8", nrows=5)
            full = pd.read_csv(f, encoding="utf-8", low_memory=False)
            sample_vals = []
            for col in full.select_dtypes(include=["object", "string"]).columns[:3]:
                v = full[col].dropna().iloc[0] if len(full[col].dropna()) > 0 else ""
                sample_vals.append(f"{col}={v[:40]}")
            print(f"  {f.name}: {len(full)} rows, {len(full.columns)} cols — OK")
            if sample_vals:
                print(f"    sample: {'; '.join(sample_vals)}")
        except UnicodeDecodeError as e:
            print(f"  {f.name}: ENCODING ERROR — {e}")
        except Exception as e:
            print(f"  {f.name}: ERROR — {e}")


def check_geopackage():
    print("\n=== GeoPackage layers ===")
    import fiona
    layers = fiona.listlayers(str(GPKG_PATH))
    print(f"  Total layers: {len(layers)}")

    conn = sqlite3.connect(str(GPKG_PATH))
    for layer in layers:
        try:
            count = conn.execute(f'SELECT COUNT(*) FROM "{layer}"').fetchone()[0]
            print(f"  {layer}: {count} rows")
        except Exception as e:
            print(f"  {layer}: ERROR — {e}")
    conn.close()


def plot_traffic():
    print("\n=== Plotting traffic segments ===")
    gdf = gpd.read_file(str(GPKG_PATH), layer="traffic_segments_latest")
    print(f"  Latest month segments: {len(gdf)} rows")
    print(f"  CRS: {gdf.crs}")
    print(f"  Bounds: {gdf.total_bounds}")

    fig, ax = plt.subplots(1, 1, figsize=(10, 12))
    gdf.plot(ax=ax, linewidth=0.5, color="steelblue")
    ax.set_title(f"Tel Aviv Traffic Segments — Latest Month ({gdf['month'].iloc[0]})")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    out_path = PROC_DIR / "traffic_segments_map.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  Map saved to {out_path}")
    plt.close()


def main():
    check_raw_files()
    check_processed_csvs()
    check_geopackage()
    plot_traffic()
    print("\n=== Verification complete ===")


if __name__ == "__main__":
    main()
