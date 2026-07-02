"""
Build a GeoPackage (smarttraffic.gpkg) from all processed data.

Spatial layers:
  - traffic_segments: all months combined, reprojected to EPSG:4326
  - traffic_segments_latest: most recent month only (base geometry)
  - closed_streets: joined to traffic segments via street_code

Attribute-only tables:
  - businesses, hotline_106, construction, population, pop_growth,
    pop_migration, dwelling, ses, digitel, budget_capital
"""

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
TRAFFIC_DIR = RAW_DIR / "traffic"
GPKG_PATH = PROC_DIR / "smarttraffic.gpkg"


def extract_month_from_filename(fname: str) -> str:
    """Extract a sortable YYYY-MM string from a traffic layer filename."""
    month_map = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "June": "06", "Jul": "07",
        "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    }
    m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun(?:e)?|Jul|Aug|Sep|Oct|Nov|Dec)(\d{4})", fname)
    if m:
        return f"{m.group(2)}-{month_map[m.group(1)]}"
    return "unknown"


def build_traffic_layers():
    """Load all traffic GeoJSON files, combine, reproject to EPSG:4326."""
    print("=== Building traffic layers ===")
    gdfs = []
    for f in sorted(TRAFFIC_DIR.glob("*.geojson")):
        gdf = gpd.read_file(f)
        if len(gdf) == 0:
            continue
        month = extract_month_from_filename(f.stem)
        gdf["month"] = month
        # Standardize column names
        rename = {
            "t_rechov": "street_name",
            "k_rechov": "street_code",
            "UniqueId": "segment_id",
            "dir_text": "direction_text",
            "Shape_Length": "shape_length",
        }
        gdf = gdf.rename(columns={k: v for k, v in rename.items() if k in gdf.columns})
        gdfs.append(gdf)

    combined = pd.concat(gdfs, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry")

    # Reproject from EPSG:3857 to EPSG:4326
    if combined.crs and combined.crs.to_epsg() != 4326:
        combined = combined.to_crs(epsg=4326)

    print(f"  Combined: {len(combined)} rows, {combined['month'].nunique()} months")

    # Write combined layer
    combined.to_file(GPKG_PATH, layer="traffic_segments", driver="GPKG")
    print("  [done] traffic_segments layer written")

    # Write latest month only
    latest_month = combined["month"].max()
    latest = combined[combined["month"] == latest_month].copy()
    latest.to_file(GPKG_PATH, layer="traffic_segments_latest", driver="GPKG")
    print(f"  [done] traffic_segments_latest layer written ({latest_month}, {len(latest)} segments)")

    # Extract unique neighborhoods from traffic data for reference
    return combined


def build_neighborhoods_lookup(traffic_gdf):
    """Build a neighborhoods lookup from the traffic + other datasets."""
    print("\n=== Building neighborhoods lookup ===")
    pop = pd.read_csv(PROC_DIR / "population.csv")
    neighborhoods = pop[["neighborhood_name", "district_code", "sub_district_code"]].drop_duplicates()
    neighborhoods = neighborhoods.dropna(subset=["neighborhood_name"])
    neighborhoods = neighborhoods[neighborhoods["neighborhood_name"] != "אין ערך"]
    write_df_to_gpkg(neighborhoods, "neighborhoods")
    print(f"  [done] neighborhoods: {len(neighborhoods)} entries")


def write_df_to_gpkg(df: pd.DataFrame, layer_name: str):
    """Write a plain DataFrame as a non-spatial table in GeoPackage using sqlite."""
    import sqlite3
    conn = sqlite3.connect(str(GPKG_PATH))
    df.to_sql(layer_name, conn, if_exists="replace", index=False)
    conn.close()


def write_attribute_table(name: str, filename: str = None):
    """Write a processed CSV as an attribute-only table in the GeoPackage."""
    if filename is None:
        filename = name
    csv_path = PROC_DIR / f"{filename}.csv"
    if not csv_path.exists():
        print(f"  [skip] {filename}.csv not found")
        return

    df = pd.read_csv(csv_path, low_memory=False)
    for col in df.columns:
        if df[col].dtype == "datetime64[ns]" or "date" in col.lower() or "year" == col:
            df[col] = df[col].astype(str)

    write_df_to_gpkg(df, name)
    print(f"  [done] {name}: {len(df)} rows")


def main():
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    # Remove existing GeoPackage to rebuild fresh
    if GPKG_PATH.exists():
        GPKG_PATH.unlink()

    traffic_gdf = build_traffic_layers()
    build_neighborhoods_lookup(traffic_gdf)

    print("\n=== Writing attribute tables ===")
    for table in [
        "businesses",
        "hotline_106",
        "construction",
        "population",
        "pop_growth",
        "pop_migration",
        "dwelling",
        "ses",
        "digitel",
        "budget_capital",
        "closed_streets",
    ]:
        write_attribute_table(table)

    print(f"\n=== GeoPackage complete ===")
    size_mb = GPKG_PATH.stat().st_size / 1024 / 1024
    print(f"  {GPKG_PATH}: {size_mb:.1f} MB")

    # List all layers
    import fiona
    layers = fiona.listlayers(str(GPKG_PATH))
    print(f"  Layers ({len(layers)}): {layers}")


if __name__ == "__main__":
    main()
