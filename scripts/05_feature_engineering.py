"""
Phase 2: Feature Engineering

Computes 22 municipal features + 5 traffic features per traffic segment.
Unit of analysis: segment_id + direction (latest month, May 2026).

Join strategy:
  - Segments → neighborhoods via spatial join (centroid within boundary polygon)
  - Businesses, hotline, dwelling → neighborhood_code
  - Closed streets → street_code
  - Construction → sub_district_code (mapped to neighborhoods)
  - Population → neighborhood_name (normalized)
  - SES → neighborhood_code

Output: 'features' layer in smarttraffic.gpkg — one row per segment-direction
with geometry + all computed features.
"""

import sqlite3
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
GPKG_PATH = BASE_DIR / "data" / "processed" / "smarttraffic.gpkg"
NH_GEOJSON = BASE_DIR / "data" / "raw" / "neighborhoods.geojson"

SPEED_COLS = [f"weekday_{h}" for h in range(6, 21)]


def normalize_name(s):
    """Normalize Hebrew neighborhood names for fuzzy matching."""
    if not isinstance(s, str):
        return ""
    s = s.replace("-", " ").replace("–", " ")
    s = s.replace(",", " ").replace("(", "").replace(")", "")
    s = s.replace("'", "").replace("׳", "")
    s = s.replace("העלייה", "עליה").replace("חיסכון", "חסכון")
    s = s.replace("התקווה", "התקוה").replace("עזרה", "עזרא")
    import re
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# 1. Load base data and build segment → neighborhood mapping
# ---------------------------------------------------------------------------

def load_base():
    """Load latest-month segments and spatial-join to neighborhoods."""
    print("=== Loading base data ===")
    segments = gpd.read_file(str(GPKG_PATH), layer="traffic_segments_latest")
    nh = gpd.read_file(str(NH_GEOJSON))
    nh = nh.rename(columns={"ms_shchuna": "nh_code", "shem_shchuna": "nh_name"})
    nh = nh[["nh_code", "nh_name", "geometry"]]

    # Spatial join: segment centroids → neighborhood polygons
    seg_proj = segments.to_crs(epsg=2039)
    centroids = seg_proj.copy()
    centroids["geometry"] = centroids.geometry.centroid
    centroids = centroids.to_crs(epsg=4326)

    joined = gpd.sjoin(centroids, nh, how="left", predicate="within")
    seg_nh = joined[["segment_id", "direction", "nh_code", "nh_name"]].copy()
    seg_nh = seg_nh.drop_duplicates(subset=["segment_id", "direction"], keep="first")

    segments = segments.merge(
        seg_nh[["segment_id", "direction", "nh_code", "nh_name"]],
        on=["segment_id", "direction"],
        how="left",
    )
    print(f"  Segments: {len(segments)}, matched to neighborhoods: {segments['nh_code'].notna().sum()}")
    return segments, nh


# ---------------------------------------------------------------------------
# 2. Traffic-derived features (5 features)
# ---------------------------------------------------------------------------

def compute_traffic_features(segments):
    """Compute 5 traffic features from hourly speed columns."""
    print("\n=== Traffic features ===")
    df = segments.copy()

    speeds = df[SPEED_COLS].apply(pd.to_numeric, errors="coerce")

    # F1: Average speed (all hours)
    df["avg_speed"] = speeds.mean(axis=1)

    # F2: Peak-hour speed drop (weekday_8 / weekday_6)
    df["peak_speed_drop"] = (
        speeds["weekday_8"].astype(float) / speeds["weekday_6"].astype(float).replace(0, np.nan)
    )

    # F3: Speed variance across hours
    df["speed_variance"] = speeds.var(axis=1)

    # F4: Directional speed differential (need both directions of same segment)
    seg_avg = df.groupby(["segment_id", "direction"])["avg_speed"].first()
    seg_pivot = seg_avg.unstack("direction")
    if seg_pivot.shape[1] >= 2:
        cols = seg_pivot.columns.tolist()
        seg_pivot["dir_speed_diff"] = (seg_pivot[cols[0]] - seg_pivot[cols[1]]).abs()
        dir_diff = seg_pivot["dir_speed_diff"].reset_index()
        dir_diff = dir_diff.rename(columns={"dir_speed_diff": "dir_speed_diff"})
        df = df.merge(dir_diff[["segment_id", "dir_speed_diff"]], on="segment_id", how="left")
    else:
        df["dir_speed_diff"] = np.nan

    # F5: Evening speed recovery (weekday_19 / weekday_17)
    df["evening_speed_recovery"] = (
        speeds["weekday_19"].astype(float) / speeds["weekday_17"].astype(float).replace(0, np.nan)
    )

    traffic_cols = ["avg_speed", "peak_speed_drop", "speed_variance", "dir_speed_diff", "evening_speed_recovery"]
    print(f"  Computed: {traffic_cols}")
    for c in traffic_cols:
        print(f"    {c}: mean={df[c].mean():.3f}, null={df[c].isna().sum()}")
    return df


# ---------------------------------------------------------------------------
# 3. Business features (5 features) — by neighborhood
# ---------------------------------------------------------------------------

def compute_business_features(conn):
    """Compute per-neighborhood business features."""
    print("\n=== Business features ===")
    biz = pd.read_sql("SELECT * FROM businesses", conn)
    biz["neighborhood_code"] = pd.to_numeric(biz["neighborhood_code"], errors="coerce")

    # F4: Restaurant/cafe density (category_name = הסעדה ומלונאות)
    restaurant_count = (
        biz[biz["category_name"] == "הסעדה ומלונאות"]
        .groupby("neighborhood_code")
        .size()
        .rename("restaurant_count")
    )
    total_biz = biz.groupby("neighborhood_code").size().rename("total_businesses")

    # F6: Business diversity index (Shannon entropy of category_name)
    def shannon_entropy(group):
        counts = group["category_name"].value_counts()
        probs = counts / counts.sum()
        return -(probs * np.log(probs + 1e-10)).sum()

    diversity = biz.groupby("neighborhood_code").apply(shannon_entropy, include_groups=False).rename("biz_diversity_index")

    # F7: Licensed vs unlicensed ratio
    licensed = biz[biz["license_status"] == "טעון רישוי"].groupby("neighborhood_code").size()
    not_licensed = biz[biz["license_status"] == "לא טעון רישוי"].groupby("neighborhood_code").size()
    license_ratio = (licensed / (licensed + not_licensed).replace(0, np.nan)).rename("licensed_biz_ratio")

    # F8: Evening business density (restaurants + entertainment)
    evening_cats = {"הסעדה ומלונאות", "אמנות, בידור ופנאי"}
    evening_count = (
        biz[biz["category_name"].isin(evening_cats)]
        .groupby("neighborhood_code")
        .size()
        .rename("evening_biz_count")
    )

    features = pd.DataFrame({
        "restaurant_count": restaurant_count,
        "total_businesses": total_biz,
        "biz_diversity_index": diversity,
        "licensed_biz_ratio": license_ratio,
        "evening_biz_count": evening_count,
    })
    features.index.name = "nh_code"
    print(f"  Neighborhoods with business data: {len(features)}")
    return features.reset_index()


# ---------------------------------------------------------------------------
# 4. Closed streets features (3 features) — by street_code
# ---------------------------------------------------------------------------

def compute_closed_streets_features(conn):
    """Compute per-street event/closure features."""
    print("\n=== Closed streets features ===")
    cs = pd.read_sql("SELECT * FROM closed_streets", conn)
    cs["street_code"] = pd.to_numeric(cs["street_code"], errors="coerce")

    # F9: Street event frequency (closure_type_name contains 'ארוע')
    events = cs[cs["closure_type_name"].str.contains("ארוע", na=False)]
    event_freq = events.groupby("street_code").size().rename("event_frequency")

    # F10: Event diversity (distinct closure_type_name for event types)
    event_diversity = events.groupby("street_code")["closure_type_name"].nunique().rename("event_diversity")

    # F3: Light rail construction proximity (closure_type_name contains 'נת"ע')
    light_rail = cs[cs["closure_type_name"].str.contains('נת"ע', na=False)]
    light_rail_flag = light_rail.groupby("street_code").size().rename("light_rail_closures")

    # F11: Parade/marathon route flag
    marathon = cs[cs["closure_type_name"].str.contains("מרתון", na=False)]
    parade_flag = marathon.groupby("street_code").size().rename("parade_route_count")

    # Infrastructure closures (non-event closures = construction disruption proxy)
    infra_types = {"שיפור תשתיות", "שיפור תשתיות מדרכות וכביש", "קרצוף וסלילה",
                   "שיקום מדרכה", "הרחבת כביש", "שביל אופניים"}
    infra = cs[cs["closure_type_name"].isin(infra_types)]
    infra_closures = infra.groupby("street_code").size().rename("infra_closure_count")

    features = pd.DataFrame({
        "event_frequency": event_freq,
        "event_diversity": event_diversity,
        "light_rail_closures": light_rail_flag,
        "parade_route_count": parade_flag,
        "infra_closure_count": infra_closures,
    })
    features.index.name = "street_code"
    print(f"  Streets with closure data: {len(features)}")
    return features.reset_index()


# ---------------------------------------------------------------------------
# 5. Hotline 106 features (2 features) — by neighborhood
# ---------------------------------------------------------------------------

def compute_hotline_features(conn):
    """Compute noise and infrastructure complaint densities."""
    print("\n=== Hotline 106 features ===")
    h = pd.read_sql("SELECT * FROM hotline_106", conn)
    h["neighborhood_code"] = pd.to_numeric(h["neighborhood_code"], errors="coerce")
    h["incident_count"] = pd.to_numeric(h["incident_count"], errors="coerce")

    # F12: Noise complaint density
    noise = h[h["category_l2"].str.contains("רעש", na=False)]
    noise_count = noise.groupby("neighborhood_code")["incident_count"].sum().rename("noise_complaints")

    # F13: Infrastructure complaint density (sidewalk, road, lighting related)
    infra_keywords = ["מדרכ", "כביש", "תאור", "תשתי", "מפגע"]
    mask = h["category_l2"].apply(lambda x: any(kw in str(x) for kw in infra_keywords))
    infra = h[mask]
    infra_count = infra.groupby("neighborhood_code")["incident_count"].sum().rename("infra_complaints")

    features = pd.DataFrame({
        "noise_complaints": noise_count,
        "infra_complaints": infra_count,
    })
    features.index.name = "nh_code"
    print(f"  Neighborhoods with complaint data: {len(features)}")
    return features.reset_index()


# ---------------------------------------------------------------------------
# 6. Construction features (2 features) — by sub_district → neighborhood
# ---------------------------------------------------------------------------

def compute_construction_features(conn, nh_to_subdistrict):
    """Compute construction count and completion rate (number of buildings)."""
    print("\n=== Construction features ===")
    c = pd.read_sql("SELECT * FROM construction", conn)
    c["sub_district"] = pd.to_numeric(c["sub_district"], errors="coerce")
    c["value"] = pd.to_numeric(c["value"], errors="coerce")

    latest_year = c["year"].max()
    recent = c[c["year"] == latest_year]

    # Use "buildings by floors" topic at municipality level, sum all floor categories
    # to get total building count per sub_district
    bldg_topic = "בניינים לפי קומות"
    bldg_data = recent[(recent["topic_name"] == bldg_topic) & (recent["subtopic_name"] == "יישוב")]

    starts = bldg_data[bldg_data["type_name"] == "התחלת בנייה"]
    start_count = starts.groupby("sub_district")["value"].sum().rename("construction_starts")

    completions = bldg_data[bldg_data["type_name"] == "גמר בנייה"]
    comp_count = completions.groupby("sub_district")["value"].sum().rename("construction_completions")

    both = pd.DataFrame({"starts": start_count, "completions": comp_count}).fillna(0)
    both["construction_completion_rate"] = both["completions"] / both["starts"].replace(0, np.nan)

    features = pd.DataFrame({
        "construction_starts": start_count,
        "construction_completion_rate": both["construction_completion_rate"],
    })
    features.index.name = "sub_district"

    if nh_to_subdistrict is not None and len(nh_to_subdistrict) > 0:
        features = features.reset_index()
        mapped = features.merge(nh_to_subdistrict, on="sub_district", how="left")
        mapped = mapped.groupby("nh_code").agg({
            "construction_starts": "mean",
            "construction_completion_rate": "mean",
        }).reset_index()
        print(f"  Neighborhoods with construction data: {len(mapped)}")
        return mapped

    print(f"  Sub-districts with construction data: {len(features)}")
    return features.reset_index()


# ---------------------------------------------------------------------------
# 7. Population/demographic features (3 features) — by neighborhood name
# ---------------------------------------------------------------------------

def compute_population_features(conn, nh_names):
    """Compute female growth, young adult concentration, elderly share."""
    print("\n=== Population features ===")
    pop = pd.read_sql("SELECT * FROM population", conn)
    pop["population_count"] = pd.to_numeric(pop["population_count"], errors="coerce")
    pop["year"] = pd.to_datetime(pop["year"], errors="coerce")
    pop["neighborhood_name_norm"] = pop["neighborhood_name"].apply(normalize_name)

    # Build name → nh_code mapping
    name_to_code = nh_names.copy()

    latest_year = pop["year"].max()
    prev_year = latest_year - pd.DateOffset(years=1)
    latest = pop[pop["year"] == latest_year]
    previous = pop[pop["year"] == prev_year]

    # F15: Female population growth YoY
    female_latest = latest[latest["gender"] == "נשים"].groupby("neighborhood_name_norm")["population_count"].sum()
    female_prev = previous[previous["gender"] == "נשים"].groupby("neighborhood_name_norm")["population_count"].sum()
    female_growth = ((female_latest - female_prev) / female_prev.replace(0, np.nan)).rename("female_pop_growth_yoy")

    # F16: Young adult concentration (20-34 age groups)
    young_groups = {"20-24", "25-29", "30-34"}
    total_by_nh = latest.groupby("neighborhood_name_norm")["population_count"].sum()
    young = latest[latest["age_group"].isin(young_groups)]
    young_by_nh = young.groupby("neighborhood_name_norm")["population_count"].sum()
    young_share = (young_by_nh / total_by_nh.replace(0, np.nan)).rename("young_adult_share")

    # F17: Elderly share (65+)
    elderly_groups = {"65-69", "70-74", "75-79", "80-84", "85+"}
    elderly = latest[latest["age_group"].isin(elderly_groups)]
    elderly_by_nh = elderly.groupby("neighborhood_name_norm")["population_count"].sum()
    elderly_share = (elderly_by_nh / total_by_nh.replace(0, np.nan)).rename("elderly_share")

    features = pd.DataFrame({
        "female_pop_growth_yoy": female_growth,
        "young_adult_share": young_share,
        "elderly_share": elderly_share,
    })
    features.index.name = "neighborhood_name_norm"

    # Map to nh_code
    features = features.reset_index()
    features = features.merge(name_to_code, on="neighborhood_name_norm", how="left")
    features = features.drop(columns=["neighborhood_name_norm"])
    features = features.dropna(subset=["nh_code"])
    print(f"  Neighborhoods with pop data: {len(features)}")
    return features


# ---------------------------------------------------------------------------
# 8. Dwelling features (2 features) — by neighborhood
# ---------------------------------------------------------------------------

def compute_dwelling_features(conn):
    """Compute residential density and commercial-to-residential ratio."""
    print("\n=== Dwelling features ===")
    dw = pd.read_sql("SELECT * FROM dwelling", conn)
    dw["neighborhood_code"] = pd.to_numeric(dw["neighborhood_code"], errors="coerce")
    dw["dwelling_units"] = pd.to_numeric(dw["dwelling_units"], errors="coerce")
    dw["billed_area"] = pd.to_numeric(dw["billed_area"], errors="coerce")

    latest_year = dw["billing_year"].max()
    recent = dw[dw["billing_year"] == latest_year]

    # F18: Residential density (units per area)
    residential = recent[recent["use_type"] == "מגורים"]
    res_by_nh = residential.groupby("neighborhood_code").agg(
        res_units=("dwelling_units", "sum"),
        res_area=("billed_area", "sum"),
    )
    res_by_nh["residential_density"] = res_by_nh["res_units"] / res_by_nh["res_area"].replace(0, np.nan)

    # F19: Commercial-to-residential ratio
    commercial = recent[recent["use_type"] == "עסקים"]
    com_units = commercial.groupby("neighborhood_code")["dwelling_units"].sum().rename("com_units")
    ratio = (com_units / res_by_nh["res_units"].replace(0, np.nan)).rename("commercial_to_residential_ratio")

    features = pd.DataFrame({
        "residential_density": res_by_nh["residential_density"],
        "commercial_to_residential_ratio": ratio,
    })
    features.index.name = "nh_code"
    print(f"  Neighborhoods with dwelling data: {len(features)}")
    return features.reset_index()


# ---------------------------------------------------------------------------
# 9. SES features (3 features) — by neighborhood
# ---------------------------------------------------------------------------

SES_TO_BOUNDARY_NAMES = {
    "גלילות, צוקי אביב- אזור שדה דב": ["גלילות", "צוקי אביב", "אזור שדה דב"],
    "תל ברוך צפון, תל ברוך, מעוז אביב": ["תל ברוך צפון", "תל ברוך", "מעוז אביב"],
    "תל-כביר, נוה עופר, יפו ב'": ["נוה עופר"],
    "עזרה והארגזים וחלק מפארק דרום": ["עזרא והארגזים"],
    "לבנה וידידיה וחלק מפארק דרום": ["לבנה וידידיה"],
}


def compute_ses_features(conn, nh_names):
    """Extract SES cluster, cars per 100 residents, avg income. Matched by name."""
    print("\n=== SES features ===")
    ses = pd.read_sql("SELECT * FROM ses", conn)

    latest_year = ses["year"].max()
    recent = ses[ses["year"] == latest_year].copy()
    recent = recent[recent["neighborhood_name"] != "כלל העיר"]
    recent["ses_cluster"] = pd.to_numeric(recent["ses_cluster"], errors="coerce")
    recent["cars_per_100_residents"] = pd.to_numeric(recent["cars_per_100_residents"], errors="coerce")
    recent["avg_monthly_income_per_capita"] = pd.to_numeric(recent["avg_monthly_income_per_capita"], errors="coerce")

    value_cols = ["ses_cluster", "cars_per_100_residents", "avg_monthly_income_per_capita"]

    # Expand combined SES neighborhoods into individual boundary names
    rows = []
    for _, row in recent.iterrows():
        ses_name = row["neighborhood_name"]
        if ses_name in SES_TO_BOUNDARY_NAMES:
            for bname in SES_TO_BOUNDARY_NAMES[ses_name]:
                new_row = row.copy()
                new_row["neighborhood_name_norm"] = normalize_name(bname)
                rows.append(new_row)
        else:
            row_copy = row.copy()
            row_copy["neighborhood_name_norm"] = normalize_name(ses_name)
            rows.append(row_copy)

    expanded = pd.DataFrame(rows)
    features = expanded[["neighborhood_name_norm"] + value_cols].copy()
    features = features.merge(nh_names, on="neighborhood_name_norm", how="left")
    features = features.drop(columns=["neighborhood_name_norm"])
    features = features.dropna(subset=["nh_code"])
    print(f"  Neighborhoods with SES data: {len(features)}")
    return features


# ---------------------------------------------------------------------------
# Main: merge everything
# ---------------------------------------------------------------------------

def build_nh_to_subdistrict(conn, nh_gdf):
    """Map sub_district codes to neighborhood codes using population data."""
    pop = pd.read_sql("""
        SELECT DISTINCT CAST(sub_district_code AS INTEGER) as sub_district,
               neighborhood_name
        FROM population
        WHERE neighborhood_name IS NOT NULL AND neighborhood_name != 'אין ערך'
    """, conn)
    pop["neighborhood_name_norm"] = pop["neighborhood_name"].apply(normalize_name)

    nh_lookup = nh_gdf[["nh_code", "nh_name"]].copy()
    nh_lookup["neighborhood_name_norm"] = nh_lookup["nh_name"].apply(normalize_name)

    merged = pop.merge(nh_lookup[["nh_code", "neighborhood_name_norm"]], on="neighborhood_name_norm", how="inner")
    return merged[["sub_district", "nh_code"]].drop_duplicates()


def build_name_to_code(nh_gdf):
    """Build a normalized neighborhood name → code mapping."""
    lookup = nh_gdf[["nh_code", "nh_name"]].copy()
    lookup["neighborhood_name_norm"] = lookup["nh_name"].apply(normalize_name)
    return lookup[["nh_code", "neighborhood_name_norm"]]


def main():
    conn = sqlite3.connect(str(GPKG_PATH))

    # Load base
    segments, nh = load_base()
    nh_to_subdistrict = build_nh_to_subdistrict(conn, nh)
    nh_name_to_code = build_name_to_code(nh)

    # Traffic features
    segments = compute_traffic_features(segments)

    # Neighborhood-level features
    biz_features = compute_business_features(conn)
    hotline_features = compute_hotline_features(conn)
    construction_features = compute_construction_features(conn, nh_to_subdistrict)
    pop_features = compute_population_features(conn, nh_name_to_code)
    dwelling_features = compute_dwelling_features(conn)
    ses_features = compute_ses_features(conn, nh_name_to_code)

    # Street-level features
    street_features = compute_closed_streets_features(conn)

    conn.close()

    # --- Merge all features onto segments ---
    print("\n=== Merging features ===")

    # Join neighborhood-level features via nh_code
    for feat_df in [biz_features, hotline_features, construction_features,
                    pop_features, dwelling_features, ses_features]:
        segments = segments.merge(feat_df, on="nh_code", how="left")

    # Join street-level features via street_code
    segments["street_code"] = pd.to_numeric(segments["street_code"], errors="coerce")
    street_features["street_code"] = pd.to_numeric(street_features["street_code"], errors="coerce")
    segments = segments.merge(street_features, on="street_code", how="left")

    # Fill street-level NaN with 0 (no events = 0 count)
    street_fill_cols = ["event_frequency", "event_diversity", "light_rail_closures",
                        "parade_route_count", "infra_closure_count"]
    for c in street_fill_cols:
        if c in segments.columns:
            segments[c] = segments[c].fillna(0)

    # Select final columns
    id_cols = ["segment_id", "direction", "street_name", "street_code", "nh_code", "nh_name", "month"]
    traffic_feats = ["avg_speed", "peak_speed_drop", "speed_variance", "dir_speed_diff", "evening_speed_recovery"]
    biz_feats = ["restaurant_count", "total_businesses", "biz_diversity_index", "licensed_biz_ratio", "evening_biz_count"]
    street_feats = ["event_frequency", "event_diversity", "light_rail_closures", "parade_route_count", "infra_closure_count"]
    complaint_feats = ["noise_complaints", "infra_complaints"]
    construction_feats = ["construction_starts", "construction_completion_rate"]
    pop_feats = ["female_pop_growth_yoy", "young_adult_share", "elderly_share"]
    dwelling_feats = ["residential_density", "commercial_to_residential_ratio"]
    ses_feats = ["ses_cluster", "cars_per_100_residents", "avg_monthly_income_per_capita"]

    all_feature_cols = (traffic_feats + biz_feats + street_feats + complaint_feats +
                        construction_feats + pop_feats + dwelling_feats + ses_feats)

    keep_cols = id_cols + all_feature_cols + ["geometry"]
    keep_cols = [c for c in keep_cols if c in segments.columns]
    result = segments[keep_cols].copy()
    result = gpd.GeoDataFrame(result, geometry="geometry")

    # --- Summary ---
    print(f"\n=== Feature table summary ===")
    print(f"  Rows: {len(result)}")
    print(f"  Feature columns: {len(all_feature_cols)}")
    print(f"\n  Feature coverage (non-null %):")
    for c in all_feature_cols:
        if c in result.columns:
            pct = result[c].notna().mean() * 100
            print(f"    {c:40s} {pct:5.1f}%  mean={result[c].mean():>10.3f}" if result[c].notna().any() else f"    {c:40s} {pct:5.1f}%")

    # Save to GeoPackage
    result.to_file(str(GPKG_PATH), layer="features", driver="GPKG")
    print(f"\n  Saved 'features' layer to {GPKG_PATH}")


if __name__ == "__main__":
    main()
