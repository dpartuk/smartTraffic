"""
Phase 3: Exploratory Analysis, Regression Modeling, and Walkability Scoring.

Reads the 'features' layer from smarttraffic.gpkg and produces:
  1. Feature distributions (histograms)
  2. Correlation heatmap
  3. Variance Inflation Factor (VIF) for multicollinearity
  4. Stepwise multiple linear regression — municipal features → avg_speed
  5. Full OLS diagnostics (statsmodels)
  6. PCA-based walkability composite index
  7. Walkability map of Tel Aviv

All plots saved to data/processed/analysis/
"""

from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor
import statsmodels.api as sm
from bidi.algorithm import get_display

matplotlib.use("Agg")

BASE_DIR = Path(__file__).resolve().parent.parent
GPKG_PATH = BASE_DIR / "data" / "processed" / "smarttraffic.gpkg"
OUT_DIR = BASE_DIR / "data" / "processed" / "analysis"
OUT_DIR.mkdir(exist_ok=True)

ID_COLS = ["segment_id", "direction", "street_name", "street_code",
           "nh_code", "nh_name", "month", "geometry"]

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

# Feature sign expectations for walkability (positive = more walkable)
WALKABILITY_SIGNS = {
    "avg_speed": -1,
    "peak_speed_drop": -1,
    "speed_variance": -1,
    "dir_speed_diff": -1,
    "evening_speed_recovery": 1,
    "restaurant_count": 1,
    "total_businesses": 1,
    "biz_diversity_index": 1,
    "licensed_biz_ratio": 1,
    "evening_biz_count": 1,
    "event_frequency": 1,
    "event_diversity": 1,
    "light_rail_closures": -1,
    "parade_route_count": 1,
    "infra_closure_count": -1,
    "noise_complaints": -1,
    "infra_complaints": -1,
    "construction_starts": -1,
    "construction_completion_rate": 1,
    "female_pop_growth_yoy": 1,
    "young_adult_share": 1,
    "elderly_share": 0,
    "residential_density": 1,
    "commercial_to_residential_ratio": 0,
    "ses_cluster": 1,
    "cars_per_100_residents": -1,
    "avg_monthly_income_per_capita": 0,
}


def load_data():
    gdf = gpd.read_file(str(GPKG_PATH), layer="features")
    print(f"Loaded {len(gdf)} segments, {len(ALL_FEATS)} features")
    return gdf


# ---------------------------------------------------------------------------
# 1. Feature distributions
# ---------------------------------------------------------------------------

def plot_distributions(df):
    print("\n=== 1. Feature distributions ===")
    n = len(ALL_FEATS)
    ncols = 4
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(20, 3.5 * nrows))
    axes = axes.flat

    for i, feat in enumerate(ALL_FEATS):
        ax = axes[i]
        vals = df[feat].dropna()
        ax.hist(vals, bins=40, color="steelblue", edgecolor="white", alpha=0.8)
        ax.set_title(feat, fontsize=10)
        ax.axvline(vals.mean(), color="red", linestyle="--", linewidth=1)
        skew = vals.skew()
        ax.text(0.95, 0.9, f"n={len(vals)}\nskew={skew:.2f}",
                transform=ax.transAxes, fontsize=8, ha="right", va="top")

    for i in range(n, len(axes)):
        axes[i].set_visible(False)

    plt.suptitle("Feature Distributions", fontsize=14, y=1.01)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "01_distributions.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  Saved 01_distributions.png")


# ---------------------------------------------------------------------------
# 2. Correlation heatmap
# ---------------------------------------------------------------------------

def plot_correlation(df):
    print("\n=== 2. Correlation heatmap ===")
    corr = df[ALL_FEATS].corr()

    fig, ax = plt.subplots(figsize=(18, 15))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                center=0, vmin=-1, vmax=1, square=True, linewidths=0.5,
                ax=ax, annot_kws={"size": 7})
    ax.set_title("Feature Correlation Matrix", fontsize=14)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "02_correlation.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  Saved 02_correlation.png")

    # Flag high correlations
    high = []
    for i in range(len(corr)):
        for j in range(i + 1, len(corr)):
            r = corr.iloc[i, j]
            if abs(r) > 0.7:
                high.append((corr.index[i], corr.columns[j], r))
    if high:
        print("  Highly correlated pairs (|r| > 0.7):")
        for a, b, r in sorted(high, key=lambda x: -abs(x[2])):
            print(f"    {a} — {b}: {r:.3f}")
    return corr


# ---------------------------------------------------------------------------
# 3. VIF multicollinearity check
# ---------------------------------------------------------------------------

def compute_vif(df, features):
    print("\n=== 3. Variance Inflation Factors ===")
    clean = df[features].dropna()
    scaler = StandardScaler()
    X = scaler.fit_transform(clean)
    vif_data = []
    for i, feat in enumerate(features):
        vif_val = variance_inflation_factor(X, i)
        vif_data.append((feat, vif_val))
    vif_df = pd.DataFrame(vif_data, columns=["feature", "VIF"]).sort_values("VIF", ascending=False)
    print(vif_df.to_string(index=False))
    return vif_df


# ---------------------------------------------------------------------------
# 4. Stepwise regression: municipal features → avg_speed
# ---------------------------------------------------------------------------

def stepwise_regression(df, target, candidates, p_enter=0.05, p_remove=0.10):
    """Forward stepwise selection by p-value."""
    clean = df[[target] + candidates].dropna()
    y = clean[target]
    selected = []
    remaining = list(candidates)

    while remaining:
        best_pval = 1.0
        best_feat = None
        for feat in remaining:
            trial = selected + [feat]
            X = sm.add_constant(clean[trial])
            try:
                model = sm.OLS(y, X).fit()
                pval = model.pvalues[feat]
                if pval < best_pval:
                    best_pval = pval
                    best_feat = feat
            except Exception:
                continue

        if best_pval < p_enter and best_feat:
            selected.append(best_feat)
            remaining.remove(best_feat)
        else:
            break

        # Backward check: remove features that became insignificant
        while True:
            X = sm.add_constant(clean[selected])
            model = sm.OLS(y, X).fit()
            pvals = model.pvalues.drop("const")
            worst_pval = pvals.max()
            if worst_pval > p_remove:
                drop = pvals.idxmax()
                selected.remove(drop)
                remaining.append(drop)
            else:
                break

    return selected


def run_regression(df):
    print("\n=== 4. Regression modeling ===")
    target = "avg_speed"

    # --- Model A: Traffic features only (excluding avg_speed itself) ---
    traffic_predictors = [f for f in TRAFFIC_FEATS if f != target]
    clean_a = df[[target] + traffic_predictors].dropna()
    X_a = sm.add_constant(clean_a[traffic_predictors])
    model_a = sm.OLS(clean_a[target], X_a).fit()
    print(f"\n  Model A — Traffic features only ({len(traffic_predictors)} predictors)")
    print(f"  R² = {model_a.rsquared:.4f}, Adj-R² = {model_a.rsquared_adj:.4f}, "
          f"n = {model_a.nobs:.0f}")

    # --- Model B: Municipal features only (stepwise selected) ---
    print(f"\n  Running stepwise selection on {len(MUNICIPAL_FEATS)} municipal features...")
    selected_muni = stepwise_regression(df, target, MUNICIPAL_FEATS)
    print(f"  Selected {len(selected_muni)} features: {selected_muni}")

    clean_b = df[[target] + selected_muni].dropna()
    X_b = sm.add_constant(clean_b[selected_muni])
    model_b = sm.OLS(clean_b[target], X_b).fit()
    print(f"\n  Model B — Municipal features (stepwise, {len(selected_muni)} predictors)")
    print(f"  R² = {model_b.rsquared:.4f}, Adj-R² = {model_b.rsquared_adj:.4f}, "
          f"n = {model_b.nobs:.0f}")

    # --- Model C: All features (stepwise from traffic + municipal) ---
    all_candidates = traffic_predictors + MUNICIPAL_FEATS
    selected_all = stepwise_regression(df, target, all_candidates)
    print(f"\n  Stepwise from all features selected {len(selected_all)}: {selected_all}")

    clean_c = df[[target] + selected_all].dropna()
    X_c = sm.add_constant(clean_c[selected_all])
    model_c = sm.OLS(clean_c[target], X_c).fit()
    print(f"\n  Model C — Combined (stepwise, {len(selected_all)} predictors)")
    print(f"  R² = {model_c.rsquared:.4f}, Adj-R² = {model_c.rsquared_adj:.4f}, "
          f"n = {model_c.nobs:.0f}")

    # --- Full summary of best model ---
    print("\n" + "=" * 70)
    print("  Model B (municipal features) — Full OLS Summary")
    print("=" * 70)
    print(model_b.summary())

    # --- Coefficient plot ---
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    for ax, model, title in [
        (axes[0], model_a, f"Model A: Traffic\nR²={model_a.rsquared_adj:.3f}"),
        (axes[1], model_b, f"Model B: Municipal\nR²={model_b.rsquared_adj:.3f}"),
        (axes[2], model_c, f"Model C: Combined\nR²={model_c.rsquared_adj:.3f}"),
    ]:
        coefs = model.params.drop("const")
        errs = model.bse.drop("const")
        pvals = model.pvalues.drop("const")
        colors = ["#2166ac" if p < 0.01 else "#67a9cf" if p < 0.05 else "#d1e5f0" for p in pvals]
        y_pos = range(len(coefs))
        ax.barh(y_pos, coefs, xerr=errs, color=colors, edgecolor="white", height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(coefs.index, fontsize=9)
        ax.axvline(0, color="black", linewidth=0.5)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Coefficient")

    plt.suptitle("Regression Coefficients: Predicting avg_speed", fontsize=13)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "03_regression_coefs.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("\n  Saved 03_regression_coefs.png")

    # --- Model comparison table ---
    comparison = pd.DataFrame({
        "Model": ["A: Traffic only", "B: Municipal (stepwise)", "C: Combined (stepwise)"],
        "Predictors": [len(traffic_predictors), len(selected_muni), len(selected_all)],
        "N": [int(model_a.nobs), int(model_b.nobs), int(model_c.nobs)],
        "R²": [model_a.rsquared, model_b.rsquared, model_c.rsquared],
        "Adj-R²": [model_a.rsquared_adj, model_b.rsquared_adj, model_c.rsquared_adj],
        "AIC": [model_a.aic, model_b.aic, model_c.aic],
        "BIC": [model_a.bic, model_b.bic, model_c.bic],
    })
    print("\n  Model Comparison:")
    print(comparison.to_string(index=False))

    return model_b, selected_muni


# ---------------------------------------------------------------------------
# 5. PCA walkability composite score
# ---------------------------------------------------------------------------

def compute_walkability_score(df):
    print("\n=== 5. Walkability composite score (PCA) ===")

    # Use features with known walkability direction
    scored_feats = [f for f in ALL_FEATS if WALKABILITY_SIGNS.get(f, 0) != 0]
    print(f"  Using {len(scored_feats)} directional features for PCA")

    clean = df[scored_feats].dropna()
    clean_idx = clean.index

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(clean)

    # Flip signs so positive = more walkable
    for i, feat in enumerate(scored_feats):
        X_scaled[:, i] *= WALKABILITY_SIGNS[feat]

    pca = PCA()
    pca.fit(X_scaled)
    explained = pca.explained_variance_ratio_

    print(f"  PC1 explains {explained[0]*100:.1f}% of variance")
    print(f"  PC1-3 explain {sum(explained[:3])*100:.1f}% of variance")
    print(f"  PC1-5 explain {sum(explained[:5])*100:.1f}% of variance")

    # Use PC1 as walkability score
    scores = pca.transform(X_scaled)[:, 0]

    # Normalize to 0–100 scale
    scores_norm = (scores - scores.min()) / (scores.max() - scores.min()) * 100

    df["walkability_score"] = np.nan
    df.loc[clean_idx, "walkability_score"] = scores_norm

    # PC1 loadings
    loadings = pd.DataFrame({
        "feature": scored_feats,
        "loading": pca.components_[0],
    }).sort_values("loading", key=abs, ascending=False)
    print("\n  PC1 loadings (top contributors):")
    print(loadings.head(15).to_string(index=False))

    # Scree plot + loadings
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    ax1.bar(range(1, len(explained) + 1), explained * 100, color="steelblue", edgecolor="white")
    ax1.plot(range(1, len(explained) + 1), np.cumsum(explained) * 100, "ro-", markersize=4)
    ax1.set_xlabel("Principal Component")
    ax1.set_ylabel("Variance Explained (%)")
    ax1.set_title("PCA Scree Plot")
    ax1.axhline(y=80, color="grey", linestyle="--", alpha=0.5)

    colors = ["#2166ac" if v > 0 else "#b2182b" for v in loadings["loading"]]
    ax2.barh(range(len(loadings)), loadings["loading"], color=colors, edgecolor="white")
    ax2.set_yticks(range(len(loadings)))
    ax2.set_yticklabels(loadings["feature"], fontsize=9)
    ax2.set_xlabel("PC1 Loading")
    ax2.set_title("PC1 Loadings (blue=+walkable, red=-walkable)")
    ax2.axvline(0, color="black", linewidth=0.5)
    ax2.invert_yaxis()

    plt.tight_layout()
    fig.savefig(OUT_DIR / "04_pca_walkability.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  Saved 04_pca_walkability.png")

    return df, loadings


# ---------------------------------------------------------------------------
# 5b. Weighted walkability index (Frank-style)
# ---------------------------------------------------------------------------

WEIGHTED_INDEX_FEATURES = [
    ("restaurant_count",       +1, 2.668),
    ("cars_per_100_residents", -1, 2.127),
    ("ses_cluster",            +1, 1.822),
    ("noise_complaints",       -1, 0.790),
    ("total_businesses",       +1, 0.400),
    ("elderly_share",          -1, 0.259),
    ("speed_variance",         -1, 0.152),
    ("dir_speed_diff",         -1, 0.130),
    ("young_adult_share",      +1, 0.111),
    ("female_pop_growth_yoy",  +1, 0.098),
]


def compute_weighted_walkability(df):
    """Compute a transparent weighted walkability index using z-scores."""
    print("\n=== 5b. Weighted Walkability Index ===")

    feat_names = [f for f, _, _ in WEIGHTED_INDEX_FEATURES]
    signs = {f: s for f, s, _ in WEIGHTED_INDEX_FEATURES}
    raw_weights = {f: w for f, _, w in WEIGHTED_INDEX_FEATURES}

    # Normalize weights to sum to 1
    total_w = sum(raw_weights.values())
    weights = {f: w / total_w for f, w in raw_weights.items()}

    clean = df[feat_names].dropna()
    clean_idx = clean.index

    scaler = StandardScaler()
    z_scores = pd.DataFrame(
        scaler.fit_transform(clean),
        columns=feat_names,
        index=clean_idx,
    )

    # Weighted sum: sign-flipped z-scores × normalized weight
    score = pd.Series(0.0, index=clean_idx)
    for feat in feat_names:
        score += signs[feat] * weights[feat] * z_scores[feat]

    # Normalize to 0–100
    score_norm = (score - score.min()) / (score.max() - score.min()) * 100

    df["walkability_weighted"] = np.nan
    df.loc[clean_idx, "walkability_weighted"] = score_norm

    # Print formula
    print("\n  Formula: Walkability = Σ (wᵢ × signᵢ × z_scoreᵢ), normalized to 0-100")
    print(f"  Features: {len(feat_names)}, Segments scored: {len(clean_idx)}")
    print("\n  Weights (from permutation importance of linear regression):")
    print(f"  {'Feature':<30s} {'Sign':>5s} {'Weight':>8s}")
    print(f"  {'-'*30} {'-'*5} {'-'*8}")
    for feat in feat_names:
        sign_str = "+" if signs[feat] > 0 else "-"
        print(f"  {feat:<30s} {sign_str:>5s} {weights[feat]:>8.3f}")

    # Correlation with PCA score
    if "walkability_score" in df.columns:
        both = df[["walkability_score", "walkability_weighted"]].dropna()
        corr = both.corr().iloc[0, 1]
        print(f"\n  Correlation with PCA score: r = {corr:.3f}")

    # Top / bottom neighborhoods
    scored = df[df["walkability_weighted"].notna()]
    nh_mean = scored.groupby("nh_name")["walkability_weighted"].mean().sort_values(ascending=False)
    print("\n  Top 5 neighborhoods:")
    for nh, sc in nh_mean.head(5).items():
        print(f"    {nh}: {sc:.1f}")
    print("  Bottom 5 neighborhoods:")
    for nh, sc in nh_mean.tail(5).items():
        print(f"    {nh}: {sc:.1f}")

    # Plot: weighted score bar chart
    fig, ax = plt.subplots(figsize=(10, 5))
    feat_labels = feat_names
    w_vals = [signs[f] * weights[f] for f in feat_names]
    colors = ["#27ae60" if v > 0 else "#c0392b" for v in w_vals]
    ax.barh(range(len(feat_labels)), w_vals, color=colors, edgecolor="white")
    ax.set_yticks(range(len(feat_labels)))
    ax.set_yticklabels(feat_labels, fontsize=10)
    ax.set_xlabel("Signed Weight (green = more walkable, red = less walkable)")
    ax.set_title("TLV Walkability Index — Feature Weights")
    ax.axvline(0, color="black", linewidth=0.5)
    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(OUT_DIR / "13_weighted_index_weights.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("\n  Saved 13_weighted_index_weights.png")

    # Save weights to JSON
    import json
    index_meta = {
        "method": "weighted_z_score",
        "weight_source": "permutation_importance_linear_regression",
        "features": [
            {"name": f, "sign": signs[f], "raw_importance": raw_weights[f],
             "normalized_weight": round(weights[f], 4)}
            for f in feat_names
        ],
        "segments_scored": len(clean_idx),
        "score_range": [0, 100],
    }
    with open(OUT_DIR / "weighted_index_meta.json", "w") as fh:
        json.dump(index_meta, fh, indent=2)
    print("  Saved weighted_index_meta.json")

    return df


# ---------------------------------------------------------------------------
# 6. Walkability map
# ---------------------------------------------------------------------------

def plot_walkability_map(gdf):
    print("\n=== 6. Walkability map ===")
    scored = gdf[gdf["walkability_score"].notna()]
    print(f"  Segments with scores: {len(scored)}")

    fig, axes = plt.subplots(1, 2, figsize=(20, 14))

    # Walkability score
    scored.plot(column="walkability_score", ax=axes[0], linewidth=1.2,
                cmap="RdYlGn", legend=True,
                legend_kwds={"label": "Walkability Score (0-100)", "shrink": 0.5})
    axes[0].set_title("Walkability Composite Score", fontsize=13)
    axes[0].set_axis_off()

    # Avg speed for comparison
    scored.plot(column="avg_speed", ax=axes[1], linewidth=1.2,
                cmap="RdYlGn_r", legend=True,
                legend_kwds={"label": "Avg Speed (kph)", "shrink": 0.5})
    axes[1].set_title("Average Traffic Speed", fontsize=13)
    axes[1].set_axis_off()

    plt.suptitle("Tel Aviv Walkability Analysis", fontsize=15, y=0.98)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "05_walkability_map.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved 05_walkability_map.png")

    # Top/bottom corridors
    top = scored.nlargest(10, "walkability_score")[["street_name", "nh_name", "walkability_score", "avg_speed"]]
    bottom = scored.nsmallest(10, "walkability_score")[["street_name", "nh_name", "walkability_score", "avg_speed"]]
    print("\n  Top 10 most walkable segments:")
    print(top.to_string(index=False))
    print("\n  Bottom 10 least walkable segments:")
    print(bottom.to_string(index=False))

    return scored


# ---------------------------------------------------------------------------
# 7. Walkability by neighborhood summary
# ---------------------------------------------------------------------------

def neighborhood_summary(gdf):
    print("\n=== 7. Walkability by neighborhood ===")
    scored = gdf[gdf["walkability_score"].notna()]
    nh_stats = scored.groupby("nh_name").agg(
        segments=("walkability_score", "count"),
        mean_walkability=("walkability_score", "mean"),
        std_walkability=("walkability_score", "std"),
        mean_speed=("avg_speed", "mean"),
    ).sort_values("mean_walkability", ascending=False)

    print(nh_stats.to_string())

    # Save as CSV
    nh_stats.to_csv(OUT_DIR / "neighborhood_walkability.csv")
    print(f"\n  Saved neighborhood_walkability.csv ({len(nh_stats)} neighborhoods)")

    # Bar chart — top and bottom 15
    fig, ax = plt.subplots(figsize=(12, 10))
    top_bottom = pd.concat([nh_stats.head(15), nh_stats.tail(15)]).drop_duplicates()
    top_bottom = top_bottom.sort_values("mean_walkability")
    colors = plt.cm.RdYlGn(top_bottom["mean_walkability"] / 100)
    ax.barh(range(len(top_bottom)), top_bottom["mean_walkability"], color=colors, edgecolor="white")
    ax.set_yticks(range(len(top_bottom)))
    ax.set_yticklabels([get_display(n) for n in top_bottom.index], fontsize=9)
    ax.set_xlabel("Mean Walkability Score")
    ax.set_title("Walkability Score by Neighborhood (top & bottom 15)")
    ax.axvline(50, color="grey", linestyle="--", alpha=0.5)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "06_neighborhood_ranking.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("  Saved 06_neighborhood_ranking.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    gdf = load_data()

    plot_distributions(gdf)
    corr = plot_correlation(gdf)
    vif_df = compute_vif(gdf, MUNICIPAL_FEATS)
    model_b, selected_muni = run_regression(gdf)
    gdf, loadings = compute_walkability_score(gdf)
    gdf = compute_weighted_walkability(gdf)
    plot_walkability_map(gdf)
    neighborhood_summary(gdf)

    # Save scored features back to GeoPackage
    gdf.to_file(str(GPKG_PATH), layer="features_scored", driver="GPKG")
    print(f"\n=== Saved 'features_scored' layer to GeoPackage ===")
    print(f"  All outputs in {OUT_DIR}/")


if __name__ == "__main__":
    main()
