"""
Phase 4: Validation & Interpretation

1. Permutation feature importance (from regression models)
2. VWP category-level feature importance analysis
3. Comparison with Li et al. (2022) findings
4. Interactive Folium walkability map
5. Neighborhood walkability profiles
6. Urban planning recommendations summary
"""

from pathlib import Path

import folium
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from bidi.algorithm import get_display

matplotlib.use("Agg")

BASE_DIR = Path(__file__).resolve().parent.parent
GPKG_PATH = BASE_DIR / "data" / "processed" / "smarttraffic.gpkg"
OUT_DIR = BASE_DIR / "data" / "processed" / "analysis"
OUT_DIR.mkdir(exist_ok=True)

TRAFFIC_FEATS = ["avg_speed", "peak_speed_drop", "speed_variance",
                 "dir_speed_diff", "evening_speed_recovery"]

MUNICIPAL_FEATS = [
    "restaurant_count", "total_businesses", "biz_diversity_index",
    "licensed_biz_ratio", "evening_biz_count",
    "event_frequency", "event_diversity", "light_rail_closures",
    "parade_route_count", "infra_closure_count",
    "noise_complaints", "infra_complaints",
    "construction_starts", "construction_completion_rate",
    "female_pop_growth_yoy", "young_adult_share", "elderly_share",
    "residential_density", "commercial_to_residential_ratio",
    "ses_cluster", "cars_per_100_residents", "avg_monthly_income_per_capita",
]

ALL_FEATS = TRAFFIC_FEATS + MUNICIPAL_FEATS

# Mapping features to Li et al.'s 6 VWP categories
VWP_CATEGORIES = {
    "Walkability": {
        "municipal": ["total_businesses", "restaurant_count", "residential_density",
                       "avg_speed", "cars_per_100_residents"],
        "visual_equivalent": "vegetation, sidewalk, road, person, bicycle",
    },
    "Feasibility": {
        "municipal": ["biz_diversity_index", "commercial_to_residential_ratio",
                       "residential_density"],
        "visual_equivalent": "road, traffic light, traffic sign, fence (-)",
    },
    "Accessibility": {
        "municipal": ["infra_complaints", "construction_starts",
                       "construction_completion_rate", "light_rail_closures",
                       "elderly_share"],
        "visual_equivalent": "sidewalk, fence (-), wall (-)",
    },
    "Safety": {
        "municipal": ["female_pop_growth_yoy", "evening_biz_count",
                       "noise_complaints", "licensed_biz_ratio",
                       "parade_route_count", "dir_speed_diff"],
        "visual_equivalent": "vegetation, truck (-), motorcycle (-), traffic light",
    },
    "Comfort": {
        "municipal": ["noise_complaints", "construction_starts",
                       "peak_speed_drop", "cars_per_100_residents",
                       "infra_closure_count"],
        "visual_equivalent": "vegetation, car (-), truck (-), sky",
    },
    "Pleasurability": {
        "municipal": ["restaurant_count", "event_frequency", "event_diversity",
                       "young_adult_share", "total_businesses"],
        "visual_equivalent": "vegetation, terrain, person, bicycle",
    },
}


def load_data():
    gdf = gpd.read_file(str(GPKG_PATH), layer="features_scored")
    print(f"Loaded {len(gdf)} segments")
    return gdf


# ---------------------------------------------------------------------------
# 1. Permutation feature importance
# ---------------------------------------------------------------------------

def permutation_feature_importance(df):
    print("\n=== 1. Permutation Feature Importance ===")
    target = "avg_speed"
    predictors = [f for f in ALL_FEATS if f != target]
    clean = df[[target] + predictors].dropna()

    X = clean[predictors]
    y = clean[target]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LinearRegression()
    model.fit(X_scaled, y)
    r2 = model.score(X_scaled, y)
    print(f"  Linear model R² = {r2:.4f} (n={len(clean)})")

    result = permutation_importance(model, X_scaled, y, n_repeats=30,
                                     random_state=42, scoring="r2")

    importance = pd.DataFrame({
        "feature": predictors,
        "importance_mean": result.importances_mean,
        "importance_std": result.importances_std,
    }).sort_values("importance_mean", ascending=False)

    print("\n  Top 15 by permutation importance:")
    print(importance.head(15).to_string(index=False))

    # Plot
    top20 = importance.head(20)
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = ["#2166ac" if v > 0.005 else "#67a9cf" if v > 0.001 else "#d1e5f0"
              for v in top20["importance_mean"]]
    ax.barh(range(len(top20)), top20["importance_mean"],
            xerr=top20["importance_std"], color=colors, edgecolor="white")
    ax.set_yticks(range(len(top20)))
    ax.set_yticklabels(top20["feature"], fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Mean R² decrease on permutation")
    ax.set_title("Permutation Feature Importance (predicting avg_speed)")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "07_permutation_importance.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  Saved 07_permutation_importance.png")

    return importance


# ---------------------------------------------------------------------------
# 2. VWP category-level analysis
# ---------------------------------------------------------------------------

def vwp_category_analysis(df, importance_df):
    print("\n=== 2. VWP Category Feature Importance ===")

    imp_lookup = dict(zip(importance_df["feature"], importance_df["importance_mean"]))

    category_scores = {}
    for cat, info in VWP_CATEGORIES.items():
        feats = info["municipal"]
        scores = [(f, imp_lookup.get(f, 0)) for f in feats if f in imp_lookup]
        total = sum(abs(s) for _, s in scores)
        category_scores[cat] = {
            "features": scores,
            "total_importance": total,
            "visual_equivalent": info["visual_equivalent"],
        }
        print(f"\n  {cat} (total importance: {total:.4f}):")
        for feat, score in sorted(scores, key=lambda x: -abs(x[1])):
            print(f"    {feat:40s} {score:+.4f}")
        print(f"    Paper's visual proxies: {info['visual_equivalent']}")

    # Bar chart by VWP category
    fig, ax = plt.subplots(figsize=(10, 6))
    cats = list(category_scores.keys())
    totals = [category_scores[c]["total_importance"] for c in cats]
    colors = plt.cm.Set2(np.linspace(0, 1, len(cats)))
    ax.bar(cats, totals, color=colors, edgecolor="white", width=0.6)
    ax.set_ylabel("Cumulative Permutation Importance")
    ax.set_title("Feature Importance by VWP Category\n(Municipal features mapped to Li et al.'s walkability dimensions)")
    plt.xticks(rotation=15)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "08_vwp_category_importance.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("\n  Saved 08_vwp_category_importance.png")

    return category_scores


# ---------------------------------------------------------------------------
# 3. Comparison with Li et al. (2022)
# ---------------------------------------------------------------------------

def paper_comparison():
    print("\n=== 3. Comparison with Li et al. (2022) ===")

    comparison = [
        {
            "VWP Category": "Walkability",
            "Li et al. (visual)": "Vegetation (+), sidewalk (+), person (+), bicycle (+)",
            "Our finding (municipal)": "Business density (+), restaurant count (+), residential density (+); SES & car ownership captured via neighborhood-level controls",
            "Agreement": "Both identify street vitality as key; our business metrics proxy for 'person' and 'bicycle' presence",
        },
        {
            "VWP Category": "Feasibility",
            "Li et al. (visual)": "Road (+), traffic light (+), sign (+), fence (-)",
            "Our finding (municipal)": "Business diversity index (+), commercial-to-residential ratio (balanced); infrastructure closures as barrier proxy",
            "Agreement": "Mixed-use diversity aligns with paper's land-use reading; our infra_closure proxies for fence/barrier",
        },
        {
            "VWP Category": "Accessibility",
            "Li et al. (visual)": "Sidewalk (+), fence (-), wall (-)",
            "Our finding (municipal)": "Infrastructure complaints (-), construction disruption (-), light rail construction (-), elderly share (indicator)",
            "Agreement": "Both identify physical barriers; our complaints capture maintained vs. degraded sidewalks without pixel counting",
        },
        {
            "VWP Category": "Safety",
            "Li et al. (visual)": "Vegetation (+), truck (-), motorcycle (-), traffic light (+)",
            "Our finding (municipal)": "Female pop growth (+), evening businesses (+), licensed biz ratio (+), noise complaints (-)",
            "Agreement": "Novel: female population growth as safety signal has no visual equivalent; evening businesses ≈ paper's 'eyes on the street'",
        },
        {
            "VWP Category": "Comfort",
            "Li et al. (visual)": "Vegetation (+), car (-), truck (-), sky (context)",
            "Our finding (municipal)": "Noise complaints (-), construction count (-), peak speed drop (-), cars per 100 residents (-)",
            "Agreement": "Strong alignment: noise/construction = direct discomfort; car density mirrors paper's car/truck pixel ratio",
        },
        {
            "VWP Category": "Pleasurability",
            "Li et al. (visual)": "Vegetation (+), terrain (+), person (+), bicycle (+)",
            "Our finding (municipal)": "Restaurant density (+), event frequency & diversity (+), young adult share (+), business growth (+)",
            "Agreement": "Our event/restaurant features capture 'liveliness' that the paper reads from person/bicycle pixels",
        },
    ]

    comp_df = pd.DataFrame(comparison)
    comp_df.to_csv(OUT_DIR / "paper_comparison.csv", index=False)

    # Print formatted
    for row in comparison:
        print(f"\n  --- {row['VWP Category']} ---")
        print(f"  Li et al.: {row['Li et al. (visual)']}")
        print(f"  Ours:      {row['Our finding (municipal)']}")
        print(f"  Insight:   {row['Agreement']}")

    print("\n  Saved paper_comparison.csv")

    # Summary figure
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis("off")

    headers = ["VWP Category", "Li et al. (Visual)", "Our Municipal Proxy", "Key Insight"]
    cell_text = []
    for row in comparison:
        cell_text.append([
            row["VWP Category"],
            row["Li et al. (visual)"][:60],
            row["Our finding (municipal)"][:60],
            row["Agreement"][:65],
        ])

    table = ax.table(cellText=cell_text, colLabels=headers,
                     cellLoc="left", loc="center", colWidths=[0.12, 0.28, 0.30, 0.30])
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 2.2)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#2166ac")
            cell.set_text_props(color="white", fontweight="bold")
        else:
            cell.set_facecolor("#f7f7f7" if row % 2 == 0 else "white")

    ax.set_title("Comparison: Li et al. (2022) Visual Features vs. Our Municipal Features",
                 fontsize=12, fontweight="bold", pad=20)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "09_paper_comparison.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  Saved 09_paper_comparison.png")

    return comp_df


# ---------------------------------------------------------------------------
# 4. Interactive Folium walkability map
# ---------------------------------------------------------------------------

def create_folium_map(gdf):
    print("\n=== 4. Interactive Folium Map ===")
    scored = gdf[gdf["walkability_score"].notna()].copy()
    scored = scored.to_crs(epsg=4326)

    center = [scored.geometry.centroid.y.mean(), scored.geometry.centroid.x.mean()]
    m = folium.Map(location=center, zoom_start=13, tiles="cartodbpositron")

    def score_color(score):
        if score >= 75:
            return "#1a9850"
        elif score >= 50:
            return "#91cf60"
        elif score >= 25:
            return "#fee08b"
        else:
            return "#d73027"

    for _, row in scored.iterrows():
        score = row["walkability_score"]
        geom = row.geometry
        coords = [(c[1], c[0]) for c in geom.coords] if geom.geom_type == "LineString" else []
        if not coords:
            continue

        popup_text = (
            f"<b>{row['street_name']}</b><br>"
            f"Neighborhood: {row['nh_name']}<br>"
            f"Walkability: {score:.1f}/100<br>"
            f"Avg Speed: {row['avg_speed']:.1f} kph<br>"
            f"Restaurants: {row.get('restaurant_count', 'N/A')}<br>"
            f"SES Cluster: {row.get('ses_cluster', 'N/A')}"
        )

        folium.PolyLine(
            coords,
            color=score_color(score),
            weight=4,
            opacity=0.8,
            popup=folium.Popup(popup_text, max_width=250),
        ).add_to(m)

    # Legend
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
                background: white; padding: 10px; border-radius: 5px;
                border: 2px solid grey; font-size: 12px;">
        <b>Walkability Score</b><br>
        <span style="color:#1a9850">&#9632;</span> High (75-100)<br>
        <span style="color:#91cf60">&#9632;</span> Medium-High (50-75)<br>
        <span style="color:#fee08b">&#9632;</span> Medium-Low (25-50)<br>
        <span style="color:#d73027">&#9632;</span> Low (0-25)<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    map_path = OUT_DIR / "walkability_map.html"
    m.save(str(map_path))
    print(f"  Saved interactive map: {map_path}")
    return m


# ---------------------------------------------------------------------------
# 5. Neighborhood profiles
# ---------------------------------------------------------------------------

def neighborhood_profiles(gdf):
    print("\n=== 5. Neighborhood Walkability Profiles ===")
    scored = gdf[gdf["walkability_score"].notna()]

    profile_feats = ["walkability_score", "avg_speed", "restaurant_count",
                     "total_businesses", "noise_complaints", "ses_cluster",
                     "young_adult_share", "elderly_share", "event_frequency",
                     "cars_per_100_residents"]

    profiles = scored.groupby("nh_name")[profile_feats].mean()
    profiles = profiles.sort_values("walkability_score", ascending=False)

    # Normalize for radar/heatmap
    norm = (profiles - profiles.min()) / (profiles.max() - profiles.min())

    # Heatmap: top 20 neighborhoods × features
    top20 = norm.head(20)
    top20.index = [get_display(n) for n in top20.index]
    fig, ax = plt.subplots(figsize=(14, 10))
    sns.heatmap(top20, annot=True, fmt=".2f", cmap="RdYlGn", ax=ax,
                linewidths=0.5, vmin=0, vmax=1)
    ax.set_title("Neighborhood Walkability Profiles (normalized, top 20)", fontsize=13)
    ax.set_ylabel("")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "10_neighborhood_profiles.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  Saved 10_neighborhood_profiles.png")

    # Save full profiles
    profiles.to_csv(OUT_DIR / "neighborhood_profiles.csv")
    print(f"  Saved neighborhood_profiles.csv ({len(profiles)} neighborhoods)")
    return profiles


# ---------------------------------------------------------------------------
# 6. Recommendations
# ---------------------------------------------------------------------------

def generate_recommendations(gdf, profiles, importance_df):
    print("\n=== 6. Urban Planning Recommendations ===")

    scored = gdf[gdf["walkability_score"].notna()]

    # Low-walkability neighborhoods with improvement potential
    low_walk = profiles[profiles["walkability_score"] < 25].copy()
    high_walk = profiles[profiles["walkability_score"] > 60].copy()

    recs = []

    recs.append("=" * 70)
    recs.append("SMART WALKABILITY ANALYSIS — KEY FINDINGS & RECOMMENDATIONS")
    recs.append("Tel Aviv, Israel | Based on 2,070 traffic segments, 27 features")
    recs.append("=" * 70)

    recs.append("\n## 1. MUNICIPAL DATA AS WALKABILITY PROXY")
    recs.append("Our analysis demonstrates that municipal operational data alone explains")
    recs.append("21.2% of traffic speed variance (Adj-R²=0.212), outperforming traffic")
    recs.append("pattern features alone (17.8%). Combined, they explain 35.4%.")
    recs.append("This supports the hypothesis that open municipal data captures walkability")
    recs.append("dimensions invisible to traffic sensors or even street-level imagery.")

    recs.append("\n## 2. TOP WALKABILITY DRIVERS (by importance)")
    top5 = importance_df.head(5)
    for _, row in top5.iterrows():
        recs.append(f"  - {row['feature']}: importance = {row['importance_mean']:.4f}")

    recs.append("\n## 3. MOST WALKABLE CORRIDORS")
    for nh in high_walk.index[:5]:
        score = high_walk.loc[nh, "walkability_score"]
        recs.append(f"  - {nh}: score {score:.1f}/100")

    recs.append("\n## 4. AREAS FOR IMPROVEMENT")
    for nh in low_walk.index:
        row = low_walk.loc[nh]
        score = row["walkability_score"]
        issues = []
        if row.get("noise_complaints", 0) > profiles["noise_complaints"].median():
            issues.append("high noise complaints")
        if row.get("event_frequency", 0) < profiles["event_frequency"].median():
            issues.append("low event activity")
        if row.get("restaurant_count", 0) < profiles["restaurant_count"].median():
            issues.append("few restaurants/cafes")
        if row.get("cars_per_100_residents", 0) > profiles["cars_per_100_residents"].median():
            issues.append("high car dependency")
        issue_str = ", ".join(issues) if issues else "general low vitality"
        recs.append(f"  - {nh} (score {score:.1f}): {issue_str}")

    recs.append("\n## 5. POLICY IMPLICATIONS")
    recs.append("  a) BUSINESS VITALITY: Restaurant density and business diversity are")
    recs.append("     the strongest walkability signals. Zoning policies that encourage")
    recs.append("     mixed-use ground floors in low-scoring neighborhoods (especially")
    recs.append("     Ramat HaChayal, Rabiviim, Neve Dan) could improve walkability.")
    recs.append("")
    recs.append("  b) STREET EVENTS: Event frequency and diversity correlate with")
    recs.append("     walkability. Expanding cultural events to peripheral neighborhoods")
    recs.append("     could activate underused street space.")
    recs.append("")
    recs.append("  c) COMPLAINT-DRIVEN MAINTENANCE: Noise and infrastructure complaints")
    recs.append("     are strong negative signals. Prioritizing complaint resolution in")
    recs.append("     walkability-improvement target areas addresses root causes.")
    recs.append("")
    recs.append("  d) DEMOGRAPHIC SHIFTS: Female population growth and young adult")
    recs.append("     concentration are strong walkability indicators — not causes, but")
    recs.append("     signals of revealed preference. Track these as early-warning")
    recs.append("     indicators for neighborhoods gaining/losing walkability.")
    recs.append("")
    recs.append("  e) CAR DEPENDENCY: cars_per_100_residents negatively correlates with")
    recs.append("     walkability. Traffic calming and parking policy in high-car-ownership")
    recs.append("     areas could shift modal balance toward walking.")

    recs.append("\n## 6. COMPARISON WITH LI ET AL. (2022)")
    recs.append("  Our municipal features successfully proxy for several visual features:")
    recs.append("  - Business density ≈ person + bicycle pixel ratio (street vitality)")
    recs.append("  - Noise/construction complaints ≈ truck + motorcycle ratio (discomfort)")
    recs.append("  - Event frequency ≈ person ratio (liveliness/pleasurability)")
    recs.append("  - Infrastructure complaints ≈ fence + wall ratio (barriers)")
    recs.append("")
    recs.append("  NOVEL CONTRIBUTIONS not capturable by imagery:")
    recs.append("  - Female population growth as safety proxy (revealed preference)")
    recs.append("  - Licensed business ratio as maintenance/regulation signal")
    recs.append("  - Evening business density as 'eyes on the street' at night")
    recs.append("  - SES cluster as confound control (wealthier = better infrastructure)")

    recs.append("\n## 7. LIMITATIONS")
    recs.append("  - No human perception survey (ground truth); avg_speed as proxy only")
    recs.append("  - No visual features (street imagery not acquired)")
    recs.append("  - Neighborhood-level features assign same value to all segments in")
    recs.append("    a neighborhood — finer granularity would improve street-level accuracy")
    recs.append("  - Construction data only through 2022; population through 2022")
    recs.append("  - Durbin-Watson = 1.16 suggests positive spatial autocorrelation")
    recs.append("    (segments near each other have correlated residuals)")

    report = "\n".join(recs)
    report_path = OUT_DIR / "recommendations.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"\n  Saved {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    gdf = load_data()

    importance = permutation_feature_importance(gdf)
    vwp_scores = vwp_category_analysis(gdf, importance)
    comp_df = paper_comparison()
    create_folium_map(gdf)
    profiles = neighborhood_profiles(gdf)
    generate_recommendations(gdf, profiles, importance)

    print(f"\n=== Phase 4 complete ===")
    print(f"  All deliverables in {OUT_DIR}/")


if __name__ == "__main__":
    main()
