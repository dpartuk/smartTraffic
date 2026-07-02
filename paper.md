# Measuring Street Walkability Perception in Tel Aviv Using Municipal Open Data

**Doron Peleg**
Tel Aviv University | 2026

---

## Abstract

This project investigates whether municipal open data — business registries, complaint logs, demographics, and traffic speeds — can proxy for visual walkability perception, traditionally measured through street-level imagery and human surveys. Using Tel Aviv as a case study, we integrate 8 datasets (370,000+ records, plus 50,947 traffic segments across 24 months), engineer 27 features across 8 categories, and model their relationship to traffic speed as a walkability proxy. Stepwise OLS regression shows that municipal features alone (Adj-R² = 0.212) explain more speed variance than traffic patterns alone (Adj-R² = 0.178); combined, they reach 0.354. A Random Forest achieves R² = 0.489 under 5-fold cross-validation — within the range Li et al. (2022) achieved with deep learning on street imagery (0.41–0.59). Two walkability scores are developed — a PCA composite and a transparent weighted formula — with r = 0.950 correlation. Mapping our features to Li et al.'s six VWP categories shows strong alignment in four dimensions and reveals novel insights (e.g., female population growth as a safety proxy) invisible to cameras.

---

## 1. Introduction

Walkability — the degree to which a street supports and encourages walking — is central to urban planning, public health, and transportation policy (Speck, 2012; Southworth, 2005). Measuring it remains challenging: survey-based methods require trained auditors; image-based methods require deep learning on street-view photographs (Li et al., 2022; Dubey et al., 2016). Both are expensive and difficult to scale.

This project asks: **can a city's operational data — business registrations, complaint logs, demographics, and traffic speeds — reveal how walkable its streets feel, without photographs or surveys?**

Our goals are: (1) integrate 8 heterogeneous municipal datasets into a unified spatial database; (2) compute 27 features per traffic segment across 8 categories; (3) compare traffic-only, municipal-only, and combined models; (4) develop two walkability scoring systems (PCA and formula-based); and (5) validate against Li et al.'s (2022) six VWP dimensions.

---

## 2. Literature Review

### 2.1 Base Paper: Li, Yabuki & Fukuda (2022)

Our project builds on Li et al. (2022), who measured Visual Walkability Perception (VWP) using panoramic street images, VR, and deep learning. They collected 2,642 panoramic images from seven cities; 30 VR-equipped raters performed 20,549 pairwise comparisons across six walkability dimensions from Alfonzo's hierarchy (2005): Walkability, Feasibility, Accessibility, Safety, Comfort, and Pleasurability. A DenseNet-based classifier achieved 85.4% accuracy. DeepLabv3+ semantic segmentation extracted area ratios of 19 visual components (vegetation, road, sidewalk, car, truck, person, etc.), and stepwise regression against VWP scores yielded R² = 0.41–0.59. Key findings: vegetation was the strongest positive predictor for safety/pleasurability; truck and motorcycle presence were consistently negative.

Our project takes the same six-category framework but replaces pixel-level visual features with municipal data features.

### 2.2 Walkability Scoring Methods

Several established approaches exist, each with limitations that motivate our work:

| Method | Approach | Limitation |
|--------|----------|------------|
| **Walk Score** (2007) | Distance-decay to nearby amenities (0–100) | Ignores street-level quality; a hostile interchange near shops scores well |
| **Frank Index** (Frank et al., 2010) | Weighted z-scores: `(6×z_intersection) + z_density + z_land_use + (2×z_retail)` | Requires GIS built-environment data not available in all cities |
| **EPA NWI** (2021) | Intersection density + transit + employment mix (1–20) | US-only, coarse spatial resolution |
| **Place Pulse** (Dubey et al., 2016) | Crowdsourced image comparisons + deep learning | Requires extensive imagery and crowdsourcing |
| **PERS** (TfL, 2003) | Field audit of 29 attributes per segment | Requires trained surveyors, labor-intensive |

Our approach uses *no images, no surveys, no distance calculations, and no field audits* — only municipal administrative data that cities already collect. The Frank Index is our closest methodological ancestor: we adopt its z-score weighting structure but derive weights empirically from model importance rather than predetermined coefficients.

---

## 3. Methodology and Results

### 3.1 Approach

We hypothesize that municipal data contains latent walkability signals: streets with many restaurants, diverse businesses, and few noise complaints feel more walkable than streets with high car ownership and frequent infrastructure disruptions. We use average traffic speed as the dependent variable (proxy for walkability), then extract model-learned feature weights to build a standalone walkability index.

### 3.2 Traffic Speed as a Walkability Proxy

Average traffic speed is an indirect measure — a proxy, not a definition. The logic: walkable streets share characteristics (narrow lanes, mixed-use frontages, pedestrian volumes, traffic calming) that structurally slow traffic. We use the mean across all weekday hours (6 AM–8 PM) to capture chronic slowness rather than temporary congestion.

**Supporting evidence.** Li et al. (2022) found that car/truck pixel ratios negatively correlate with VWP — our speed variable is the numerical equivalent. The shared-space design movement (Hamilton-Baillie, 2008) shows that pedestrian-priority streets naturally reduce speeds to 15–20 kph; Tel Aviv's most walkable corridor (Rothschild) averages 11.6 kph, while the least walkable (Neve Dan) averages 17.9 kph. Jacobs (1961) observed that mixed-use commerce creates pedestrian friction that slows vehicles — confirmed by our data where restaurant_count strongly predicts lower speeds. Tefft (2013) showed that pedestrian injury risk rises sharply above 30 kph, making low speed a *component* of walkability, not merely a correlate.

**Why not a direct measure?** No human perception survey exists for Tel Aviv at segment level. Street-view imagery coverage is incomplete. Walk Score captures access, not experience. Field audits are impractical for 2,070 segments. Traffic speed is the only continuously measured, segment-level, city-wide variable available.

**Mitigations against false signals.** (1) Temporal averaging smooths rush-hour congestion. (2) Multi-feature modeling ensures that streets slow only from construction (lacking the municipal feature signature of walkability) are distinguished from genuinely walkable streets. (3) The final walkability scores use 10–24 features, not speed alone.

### 3.3 Datasets

Eight freely available datasets from the Tel Aviv Open Data Portal and ArcGIS server:

| Dataset | Records | Format | Join Strategy |
|---------|---------|--------|--------------|
| Traffic speeds | 50,947 × 24 months | GeoJSON (ArcGIS API) | Direct (segment geometry) |
| Business registry | ~28,000 | CSV (UTF-16LE) | Neighborhood code |
| 106 Hotline complaints | ~180,000 | CSV (UTF-16LE) | Neighborhood code |
| Closed streets | ~8,500 | CSV (UTF-16LE) | Street code |
| Construction permits | ~15,000 | CSV (Win-1255) | Sub-district → neighborhood mapping |
| Population | ~85,000 | CSV (Win-1255) | Normalized Hebrew name |
| Dwelling units | ~4,500 | CSV (Win-1255) | Neighborhood code |
| Socioeconomic index | 71 neighborhoods | Excel | Neighborhood code |

Technical challenges included 3 encodings, 4 delimiters, ArcGIS pagination (2,000-record limit), inconsistent Hebrew spelling across datasets, and sub-district-to-neighborhood mapping. All data is loaded into a GeoPackage (16 layers, 243 MB).

### 3.4 Feature Engineering

The unit of analysis is a directed traffic segment (~100 m). Segments are spatially joined to 71 neighborhoods via centroid point-in-polygon matching (EPSG:2039 → 4326, 99.6% match rate). We compute 27 features:

| Category | Features | Sign | Join |
|----------|----------|------|------|
| **Traffic (5)** | avg_speed, peak_speed_drop, speed_variance, dir_speed_diff, evening_speed_recovery | −, −, −, −, + | Direct |
| **Business (5)** | restaurant_count, total_businesses, biz_diversity_index (Shannon entropy), licensed_biz_ratio, evening_biz_count | all + | Neighborhood |
| **Street Events (5)** | event_frequency, event_diversity, light_rail_closures, parade_route_count, infra_closure_count | +, +, −, +, − | Street code |
| **Complaints (2)** | noise_complaints, infra_complaints | both − | Neighborhood |
| **Construction (2)** | construction_starts, construction_completion_rate | −, + | Sub-district map |
| **Demographics (3)** | female_pop_growth_yoy, young_adult_share, elderly_share | +, +, − | Hebrew name |
| **Housing (2)** | residential_density, commercial_to_residential_ratio | +, neutral | Neighborhood |
| **Socioeconomic (3)** | ses_cluster, cars_per_100_residents, avg_monthly_income | +, −, neutral | Neighborhood |

Coverage: 82–100% across all features. Final dataset: 2,070 segments with complete traffic data; 1,278–1,408 with full municipal coverage.

### 3.5 Results

#### Multicollinearity and Feature Selection

A VIF check identified 9 features with VIF > 10; the extreme case was evening_biz_count (VIF = 1,498, r = 0.999 with restaurant_count). Stepwise regression (p_enter = 0.05, p_remove = 0.10) selected only features adding significant explanatory power. See Figures 1–2 for distributions and correlation heatmap.

#### Linear Regression: Municipal vs. Traffic Features

| Model | Predictors | Adj-R² |
|-------|-----------|--------|
| A: Traffic only | 4 | 0.178 |
| B: Municipal only | 12 | **0.212** |
| C: Combined | 17 | 0.354 |

**Central finding:** Municipal features alone (Model B) outperform traffic features (Model A), demonstrating that business registries, complaints, and demographics explain more about a street's traffic behavior than traffic's own patterns (Figure 3).

#### Machine Learning Generalization

5-fold cross-validation on the full 27-feature set:

| Model | CV R² (mean ± std) | MAE |
|-------|-------------------|-----|
| Linear Regression | 0.330 ± 0.029 | 2.3 kph |
| Neural Network | 0.437 ± 0.118 | 2.0 kph |
| **Random Forest** | **0.489 ± 0.022** | **1.9 kph** |

The Random Forest is both the most accurate and most stable. Its R² = 0.489 falls within Li et al.'s range (0.41–0.59) achieved with deep learning on imagery. The Neural Network's high variance (±0.118) reflects insufficient training data (~1,400 samples).

#### Feature Importance

| Rank | Feature | Importance | Interpretation |
|------|---------|-----------|----------------|
| 1 | restaurant_count | 2.668 | Street vitality |
| 2 | cars_per_100_residents | 2.127 | Car dependency (−) |
| 3 | ses_cluster | 1.822 | Infrastructure quality |
| 4 | noise_complaints | 0.790 | Pedestrian discomfort (−) |
| 5 | total_businesses | 0.400 | Mixed-use appeal |
| 6–10 | elderly_share, speed_variance, dir_speed_diff, young_adult_share, female_pop_growth | 0.098–0.259 | Demographics + traffic |

Municipal features dominate (8 of top 10), reinforcing that municipal data is richer than traffic sensors for walkability assessment (Figure 7).

#### From Speed Model to Walkability Score

The models predict *speed*, not walkability. The bridge: we use the model as a **feature selection and weighting tool**. The model's importance values reveal which features carry the most information about street character and by how much. We then extract those importance values as weights for a standalone walkability formula — the model's predictions are discarded; only its learned feature rankings survive.

> **Train model** (features → speed) → **Extract importance** (which features carry signal) → **Assign signs** (domain knowledge) → **Build formula** (weighted z-scores) → **Score** (0–100)

This mirrors how Frank et al. (2010) constructed their index: regression on walking behavior to discover weights, then a standalone weighted z-score formula.

#### Walkability Scoring — PCA (Approach 1)

PCA on 24 sign-flipped directional features. PC1 explains 26% of variance and captures the walkability gradient (Figure 4). Scores normalized to 0–100.

#### Walkability Scoring — Weighted Formula (Approach 2)

Following the Frank Index structure, we combine importance-derived weights with domain-assigned signs:

> Walkability = Σ (wᵢ × signᵢ × z_scoreᵢ), normalized to 0–100

| Feature | Sign | Weight |
|---------|------|--------|
| restaurant_count | + | 0.312 |
| cars_per_100_residents | − | 0.249 |
| ses_cluster | + | 0.213 |
| noise_complaints | − | 0.092 |
| total_businesses | + | 0.047 |
| elderly_share | − | 0.030 |
| speed_variance | − | 0.018 |
| dir_speed_diff | − | 0.015 |
| young_adult_share | + | 0.013 |
| female_pop_growth | + | 0.012 |

The weighted index (1,408 segments) correlates with PCA at r = 0.950, validating it as a simpler, more interpretable alternative (Figure 13).

**Table 1.** Neighborhood walkability rankings (PCA score, 0–100).

| Rank | Neighborhood | Score | Avg Speed | Key Characteristics |
|------|-------------|-------|-----------|-------------------|
| 1 | Lev Tel Aviv | 93.6 | 15.5 kph | Highest restaurant density, high SES |
| 2 | Old North (south) | 73.1 | 11.4 kph | Dense mixed-use, high young adult share |
| 3 | Old North (north) | 62.1 | 12.6 kph | Residential-commercial mix, frequent events |
| 4 | Montefiore | 48.0 | 13.2 kph | Historic mixed-use |
| 5 | Florentin | 45.9 | 12.1 kph | Arts/nightlife, high evening activity |
| ... | | | | |
| 37 | Ramat HaChayal | 9.0 | 15.0 kph | Tech-office, few restaurants, high car ownership |
| 38 | Rabiviim | 4.9 | 15.9 kph | Residential, few businesses or events |
| 39 | Neve Dan | 2.9 | 17.9 kph | Car-dependent, lowest commercial activity |

### 3.6 Comparison with Li et al. (2022)

| VWP Category | Li et al. Visual Features | Our Municipal Proxy | Agreement |
|-------------|--------------------------|-------------------|-----------|
| Walkability | Vegetation, sidewalk, person, bicycle | Business density, restaurant count | Both identify street vitality as key |
| Feasibility | Road, traffic light, fence (−) | Business diversity, commercial ratio | Mixed-use diversity aligns with land-use reading |
| Accessibility | Sidewalk, fence (−), wall (−) | Infra complaints, construction, light rail closures | Both identify physical barriers |
| Safety | Vegetation, truck (−), motorcycle (−) | Female pop growth, evening businesses | **Novel**: revealed-preference safety signal |
| Comfort | Vegetation, car (−), truck (−) | Noise complaints, cars per 100 residents | Strong: car density mirrors car/truck pixel ratio |
| Pleasurability | Vegetation, person, bicycle | Restaurant density, events, young adult share | Events/restaurants capture liveliness |

Four of six categories show strong alignment. The Safety category reveals a novel contribution: female population growth captures *revealed preference* — women disproportionately avoid unsafe neighborhoods, producing an aggregated safety signal invisible to cameras. Evening business count similarly proxies for Jacobs' "eyes on the street" — natural surveillance from after-dark commerce that daytime street imagery misses.

---

## 4. Discussion

### 4.1 Key Findings

Municipal administrative data captures walkability dimensions that complement and sometimes exceed traffic sensors or imagery. That municipal-only features (Adj-R² = 0.212) outperform traffic-only features (0.178) in predicting a *traffic* variable is the project's most striking result — the municipal context is more predictive than the traffic patterns themselves.

### 4.2 Practical Implications

The weighted formula provides an actionable tool for urban planners. Unlike PCA (requiring statistical expertise) or Walk Score (proprietary), each feature has a named weight and clear direction. Restaurant_count (weight 0.312) dominates, suggesting that zoning for mixed-use ground floors would have the largest walkability impact. The strong negative weight on cars_per_100_residents (0.249) directly supports traffic calming and parking reduction policies.

### 4.3 Limitations

1. **No ground truth.** Speed is an indirect proxy; validation against a human perception survey would strengthen findings (see Section 3.2 for full rationale and mitigations).
2. **No visual features.** Adding vegetation/tree canopy data would address the gap where Li et al.'s strongest predictor has no municipal equivalent.
3. **Spatial granularity.** Municipal features are at neighborhood level — all segments in a neighborhood share the same values.
4. **Temporal coverage.** Construction and demographic data extend only through 2022.
5. **Spatial autocorrelation.** Durbin-Watson = 1.16 suggests correlated residuals among nearby segments.

---

## 5. Conclusion

Municipal open data can serve as a viable proxy for walkability perception. Using 8 datasets and 27 features, we achieve R² = 0.489 (Random Forest) — comparable to Li et al.'s R² = 0.41–0.59 with deep learning on imagery. Our weighted walkability index provides a transparent, reproducible formula adaptable to any city with similar open data. No cameras, no surveys, no proprietary tools required.

**Future work.** (1) Validate against a human perception survey, even a small one covering 10–15 neighborhoods. (2) Integrate green space / tree canopy data to address the vegetation gap. (3) Track walkability scores over time to test whether the index captures dynamic changes as neighborhoods evolve.

**Reproducibility.** The pipeline is implemented in open-source Python on freely available data. Any city publishing business registries, complaint logs, demographics, and traffic speeds can adapt it.

---

## Figures

| # | File | Description |
|---|------|-------------|
| 1 | 01_distributions.png | Feature distributions |
| 2 | 02_correlation.png | Correlation heatmap (27 × 27) |
| 3 | 03_regression_coefs.png | Regression coefficients: Models A, B, C |
| 4 | 04_pca_walkability.png | PCA scree plot and PC1 loadings |
| 5 | 05_walkability_map.png | Walkability score map of Tel Aviv |
| 6 | 06_neighborhood_ranking.png | Neighborhood ranking |
| 7 | 07_permutation_importance.png | Permutation feature importance |
| 8 | 08_vwp_category_importance.png | Importance by VWP category |
| 9 | 09_paper_comparison.png | Li et al. vs. our features |
| 10 | 10_neighborhood_profiles.png | Neighborhood profiles heatmap |
| 11 | 11_model_comparison.png | ML model comparison |
| 12 | 12_feature_importance_comparison.png | LR vs. RF importance |
| 13 | 13_weighted_index_weights.png | Weighted index: signed weights |

Interactive map: `walkability_map.html` (Folium).

---

## References

Alfonzo, M. A. (2005). To walk or not to walk? The hierarchy of walking needs. *Environment and Behavior*, 37(6), 808–836.

Dubey, A., Naik, N., Parikh, D., Raskar, R., & Hidalgo, C. A. (2016). Deep learning the city: Quantifying urban perception at a global scale. *ECCV 2016*, 196–212.

Frank, L. D., Sallis, J. F., Saelens, B. E., Leary, L., Cain, K., Conway, T. L., & Hess, P. M. (2010). The development of a walkability index. *British Journal of Sports Medicine*, 44(13), 924–933.

Hamilton-Baillie, B. (2008). Shared space: Reconciling people, places and traffic. *Built Environment*, 34(2), 161–181.

Jacobs, J. (1961). *The Death and Life of Great American Cities*. Random House.

Li, Y., Yabuki, N., & Fukuda, T. (2022). Measuring visual walkability perception using panoramic street view images, virtual reality, and deep learning. *Sustainable Cities and Society*, 86, 104140.

Southworth, M. (2005). Designing the walkable city. *Journal of Urban Planning and Development*, 131(4), 246–257.

Speck, J. (2012). *Walkable City*. Farrar, Straus and Giroux.

Tefft, B. C. (2013). Impact speed and a pedestrian's risk of severe injury or death. *Accident Analysis & Prevention*, 50, 871–878.

Transport for London (2003). *PERS: Handbook for Assessors*. TfL.

U.S. EPA (2021). *National Walkability Index Methodology*. Smart Location Database.

Walk Score (2007). Methodology. Front Seat Management LLC.
