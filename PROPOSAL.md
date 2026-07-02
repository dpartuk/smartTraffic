# Smart Walkability Perception for Tel Aviv
## Project Proposal

### 1. Motivation

Walkable streets promote social and economic prosperity in urban communities. Measuring how walkable a street *feels* to pedestrians — visual walkability perception (VWP) — is critical for urban planning, but traditional methods don't scale: field surveys are expensive, and computer-aided audits based on pixel ratios miss the subjective human experience.

This project proposes a data-driven walkability analysis framework for Tel Aviv, combining the city's rich open municipal data with visual street-level features. Unlike prior work that relies solely on image-based features, we incorporate operational, demographic, and socioeconomic signals that capture dimensions of walkability invisible to a camera.

### 2. Background: Li et al. (2022)

This project is informed by Li, Yabuki & Fukuda (2022), *"Measuring visual walkability perception using panoramic street view images, virtual reality, and deep learning"* (Sustainable Cities and Society, vol. 86, 104140).

**What they did:**
- Built a dataset of 2,642 panoramic street view images from 7 cities (NYC, LA, London, Paris, Berlin, Tokyo, Osaka)
- 30 trained raters scored images in VR across six walkability categories via pairwise comparison (20,549 comparisons)
- Trained a DenseNet-based deep learning classifier (VWPCL) achieving 85.4% accuracy across six VWP categories
- Used DeepLabv3+ semantic segmentation to extract area ratios of 19 physical components, then stepwise multiple linear regression (R² = 0.41–0.59) to identify which features drive each walkability category
- Applied Grad-CAM heatmaps for visual interpretability

**Six VWP categories** (from Alfonzo's hierarchy of walking needs):

| Category | Definition |
|---|---|
| Walkability | Overall visual impression of walking support |
| Feasibility | Incentive factors — land use diversity, facility presence |
| Accessibility | Visible barriers — dead ends, restricted access, missing sidewalks |
| Safety | Appearance of safety from crime and traffic accidents |
| Comfort | Street furniture, sidewalk width, amenities, barrier-free facilities |
| Pleasurability | Appeal, diversity, liveliness, enjoyment |

**19 visual features used** (pixel area ratio from semantic segmentation):
vegetation, road, sidewalk, terrain, building, wall, fence, sky, car, truck, bus, train, motorcycle, bicycle, pole, traffic light, traffic sign, person, rider

**Key findings:**
- Vegetation was the strongest positive predictor for safety and pleasurability
- Sidewalk area was most important for accessibility
- Fence was the strongest negative predictor for feasibility
- Trucks and motorcycles were negative across nearly all categories
- Traffic lights and signs were positive for feasibility, accessibility, safety, and comfort
- Pixel area ratios alone cannot capture spatial arrangement, scale, or fine-grained elements (graffiti, street furniture, store signs)

**Our differentiation:** The paper had only visual features. We add operational + demographic + socioeconomic features from municipal open data, enabling analysis of walkability dimensions that cameras cannot see (complaint patterns, business vitality, demographic shifts, construction disruption).

### 3. Source Datasets

All data is publicly available from the Tel Aviv Open Data Portal (https://opendata.tel-aviv.gov.il/).

#### 3.1 ArcGIS Traffic Speed Segments

| Property | Value |
|---|---|
| Source | `gisn.tel-aviv.gov.il/arcgis/rest/services/OpenData/segs_kph_monthly_*` |
| Coverage | 24 monthly layers (April 2024 – May 2026) |
| Format | ArcGIS MapServer, queryable as GeoJSON |
| Geometry | Polyline segments (EPSG:3857), typically 70–165m long |
| Key fields | `t_rechov` (street name), `UniqueId` (segment ID), `direction`, `dir_text`, `weekday_6`..`weekday_20` (avg kph per hour), `Shape_Length` |
| Access | HTTP GET with pagination (max 2,000 records/request via `resultOffset`) |
| Notes | Speeds range 7–21 kph in central TLV; bidirectional streets have two records per segment |

#### 3.2 CSV Datasets

| ID | Dataset | File | Encoding | Delim | Key Fields |
|---|---|---|---|---|---|
| 132 | Construction starts/completions | binyanimLamas.csv | Win-1255 | `,` | Year, district, stat area, type (start/completion), buildings by floors, dwelling count |
| 130 | Businesses registry | maagar_asakim.csv | UTF-16LE | `;` | Business ID, neighborhood code/name, licensing status (`sw_taun_rishui`), category (`t_category`), industry branch, area sqm, district |
| 129 | Digitel info items | divurim_open_click_new.csv | UTF-16LE | `;` | Mailing date, title, neighborhood, age group, sent/opened/clicked counts |
| 128 | 106+ hotline inquiries | PniyotKriyot106.csv | UTF-16LE | `;` | 3-level category hierarchy, year/month, neighborhood, district, incident count, routing code |
| 112 | Closed streets history | rechov_sagur.csv | UTF-16LE | `,` | Street name, from/to streets, date range, closure type (`t_sug`: event/light rail/infrastructure), full/partial, hours, night flag |
| 117 | Population by age/gender | Uchlusiya_KvutzatUchlusiya.csv | Win-1255 | `\|` | Gender, 5-year age group, neighborhood, district, year, population count |
| 4 | Population growth components | MarkiveyGidul.csv | Win-1255 | `\|` | Growth component (start pop, births, deaths, migration), neighborhood, year, count |
| 3 | Dwelling units | yehidot_diyur.csv | Win-1255 | `,` | Billing year, unit count, use type (residential/commercial), area, neighborhood |
| 2 | Population migration | Nayadut_Uchlusiya_Min_Gil.csv | Win-1255 | `\|` | Gender, age, migration type (inter/intra-city in/out), neighborhood, year, count |
| 146 | Capital budget | hoshen_od_tabar.csv | UTF-16LE | `;` | Budget year, updated amount, execution to date, item name, department, sub-group |

#### 3.3 Other Formats

| ID | Dataset | Format | Notes |
|---|---|---|---|
| 118 | Socio-economic index (SES) | Excel (.xlsx), 2 sheets (2017, 2019) | 18 indicators per neighborhood: SES cluster (1–10), dependency ratio, median age, % academic, avg income, cars/100 residents, etc. |
| 144 | Census 2022 | PowerBI dashboard only | No raw download available |
| 147 | Pride parade routes | GTFS zip | Alternative transit routes during events |

#### 3.4 External Data (to be acquired)

| Source | Data | Format | Purpose |
|---|---|---|---|
| Google Street View Static API or Mapillary (free) | Panoramic street images at each segment centroid | JPEG | Visual feature extraction via semantic segmentation |

### 4. Feature Engineering

#### 4.1 Unit of Analysis

Each record represents a **traffic segment** (`UniqueId` + `direction`), which is a directed polyline of 70–165m on a Tel Aviv street.

Features are joined at two spatial scales:
- **Street-level** (100–200m buffer around segment): businesses, complaints, events, traffic speed
- **Neighborhood-level** (join via `k_shchuna` / `k_rova`): demographics, SES, dwelling, population growth

#### 4.2 Features from Municipal Open Data

**Construction & Infrastructure**

| # | Feature | Source | Walkability Proxy | Dir | Derivation |
|---|---|---|---|---|---|
| 1 | Construction count (last 12 months) | Construction (ID 132) | Comfort, Accessibility | (-) | Count construction starts within buffer in trailing 12 months |
| 2 | Construction completion rate | Construction (ID 132) | Comfort | (+) | Ratio of completed to started projects — low ratio = prolonged disruption |
| 3 | Light rail construction proximity | Closed streets (ID 112), filter `t_sug=נת"ע` | Accessibility (-) short term, (+) long term | mixed | Binary/distance: active light rail construction nearby. Current disruption but future transit access improves walkability |

**Business & Commerce**

| # | Feature | Source | Walkability Proxy | Dir | Derivation |
|---|---|---|---|---|---|
| 4 | Restaurant/cafe density | Businesses (ID 130), `k_category=3` (הסעדה ומלונאות) | Pleasurability, Feasibility | (+) | Count of hospitality businesses per 100m of street. People eat where they walk; restaurants signal street-level vitality |
| 5 | Business growth rate YoY | Businesses (ID 130) | Feasibility, Pleasurability | (+) | Year-over-year change in business count within buffer. Growing commercial activity = street is attracting investment and foot traffic |
| 6 | Business diversity index | Businesses (ID 130), Shannon entropy of `t_category` per area | Feasibility, Pleasurability | (+) | Mixed-use streets (food + retail + services) are more walkable than mono-use |
| 7 | Licensed vs. unlicensed business ratio | Businesses (ID 130), `sw_taun_rishui` field | Safety | (+) | More licensed = more regulated = more maintained streetscape |
| 8 | Evening business density | Businesses (ID 130), filter restaurants/bars/entertainment | Safety | (+) | "Eyes on the street" at night — Jane Jacobs principle |

**Street Events & Closures**

| # | Feature | Source | Walkability Proxy | Dir | Derivation |
|---|---|---|---|---|---|
| 9 | Street event frequency | Closed streets (ID 112), `t_sug=ארוע` | Pleasurability, Safety | (+) | Count of event-type closures on this street per year |
| 10 | Event diversity | Closed streets (ID 112), count distinct event types | Pleasurability | (+) | Streets hosting varied events (sports, culture, markets) = vibrant |
| 11 | Parade/marathon route flag | Closed streets (ID 112) + Pride GTFS (ID 147) | Safety, Comfort | (+) | Binary: has this street been selected for a parade or marathon route. These routes are specifically chosen for wide sidewalks, low crime, crowd capacity |

**Municipal Service Complaints**

| # | Feature | Source | Walkability Proxy | Dir | Derivation |
|---|---|---|---|---|---|
| 12 | Noise complaint density | 106 hotline (ID 128), filter `level2=רעש` | Comfort | (-) | Direct signal of pedestrian discomfort. Noise-related complaints per 100m per year |
| 13 | Infrastructure complaint density | 106 hotline (ID 128), filter on sidewalk/road/lighting categories | Accessibility, Safety | (-) | Broken sidewalks, missing lighting = hostile walking environment |
| 14 | Complaint resolution time | 106 hotline (ID 128), if available | Comfort | (-) | Slow resolution = persistent problems in the walking environment |

**Demographics & Population**

| # | Feature | Source | Walkability Proxy | Dir | Derivation |
|---|---|---|---|---|---|
| 15 | Female population growth YoY | Population (ID 117), `des_min=נשים` | Safety | (+) | Year-over-year growth rate of female residents — women are more sensitive to safety in residential choices |
| 16 | Young adult concentration (20–34) | Population (ID 117) | Pleasurability | (+) | Share of 20–34 age group in neighborhood — young adults cluster in lively, walkable areas |
| 17 | Elderly population share (65+) | Population (ID 117), filter 65+ age groups | Accessibility | indicator | High elderly share + high walkability score = street is accessible |

**Housing & Land Use**

| # | Feature | Source | Walkability Proxy | Dir | Derivation |
|---|---|---|---|---|---|
| 18 | Residential density | Dwelling units (ID 3) / area | Feasibility | (+) | Dense residential = more pedestrians = more demand for walkable streets |
| 19 | Commercial-to-residential ratio | Dwelling units (ID 3), `sug_shimush` | Feasibility | balance | Mixed-use balance signals walkable urban design |

**Socio-Economic Controls**

| # | Feature | Source | Walkability Proxy | Dir | Derivation |
|---|---|---|---|---|---|
| 20 | SES cluster | SES (ID 118), `eshkol_pnimi` | Control variable | — | Wealthier neighborhoods have better infrastructure — need to control for this |
| 21 | Cars per 100 residents | SES (ID 118), `cnt_cars_per_100_persons` | Walkability | (-) | High car ownership = car-dependent neighborhood = less walkable |
| 22 | Avg monthly income per capita | SES (ID 118) | Control variable | — | Confound control |

#### 4.3 Features from Traffic Speed Data

| Feature | Derivation | Walkability Proxy | Direction |
|---|---|---|---|
| Average speed (all hours) | Mean of `weekday_6`..`weekday_20` | Overall walkability | context |
| Peak-hour speed drop | `weekday_8` / `weekday_6` ratio | Congestion severity | (-) |
| Speed variance across hours | Std dev of hourly speeds | Traffic predictability | (-) |
| Directional speed differential | Abs difference between dir 1 and dir 2 avg speeds | Safety | (-) |
| Evening speed recovery | `weekday_19` / `weekday_17` ratio | Evening street character | context |

#### 4.4 Visual Features (from street imagery)

Using DeepLabv3+ semantic segmentation (Cityscapes-trained) on panoramic street view images at each segment centroid, extract area ratios for the same 19 physical components used in Li et al. (2022):

| Feature | Walkability Proxy | Expected Direction (from paper) |
|---|---|---|
| Vegetation ratio | Safety, Pleasurability | (+) |
| Sidewalk ratio | Accessibility | (+) |
| Road ratio | Feasibility | (+) but excessive bare road is (-) |
| Terrain ratio | Pleasurability | (+) |
| Fence ratio | Feasibility | (-) |
| Sky ratio | Enclosure | context-dependent |
| Building ratio | Urban character | context-dependent |
| Car ratio | Comfort | (-) |
| Truck ratio | Safety, Comfort | (-) |
| Bicycle ratio | Pleasurability | (+) |
| Person ratio | Pleasurability | (+) |
| Traffic light/sign ratio | Safety, Feasibility | (+) |
| Wall ratio | Accessibility | (-) |
| Bus/motorcycle/train/pole/rider | Various | Various |

### 5. Feature Categories by VWP Dimension

Each of the paper's six VWP categories is mapped to both our municipal data features and visual features:

#### Walkability (overall)
- **Municipal:** business growth (#5), restaurant density (#4), residential density (#18), avg traffic speed, cars per 100 residents (#21)
- **Visual:** vegetation, sidewalk, road, person, bicycle

#### Feasibility
- **Municipal:** business diversity index (#6), commercial-to-residential ratio (#19), residential density (#18)
- **Visual:** road, traffic light, traffic sign, fence (-)

#### Accessibility
- **Municipal:** infrastructure complaints (#13), construction in progress (#1, #2), light rail construction (#3), elderly population share (#17)
- **Visual:** sidewalk, fence (-), wall (-)

#### Safety
- **Municipal:** female population growth (#15), evening business density (#8), noise complaints (#12), licensed business ratio (#7), event route selection (#11), directional speed differential
- **Visual:** vegetation, truck (-), motorcycle (-), traffic light, traffic sign

#### Comfort
- **Municipal:** noise complaints (#12), construction count (#1), peak speed drop, cars per 100 residents (#21), complaint resolution time (#14)
- **Visual:** vegetation, car (-), truck (-), sky

#### Pleasurability
- **Municipal:** restaurant density (#4), event frequency/diversity (#9, #10), young adult concentration (#16), business growth (#5)
- **Visual:** vegetation, terrain, person, bicycle

#### Summary Table

| VWP Category | Municipal Data Features | Visual Features |
|---|---|---|
| **Walkability** (overall) | Business growth, restaurant density, residential density, avg traffic speed, cars per 100 residents | Vegetation, sidewalk, road, person, bicycle |
| **Feasibility** | Business diversity index, commercial-to-residential ratio, residential density | Road, traffic light, traffic sign, fence (-) |
| **Accessibility** | Infrastructure complaints, construction in progress, light rail proximity, elderly population share | Sidewalk, fence (-), wall (-) |
| **Safety** | Female population growth, evening business density, noise complaints, licensed business ratio, event route selection | Vegetation, truck (-), motorcycle (-), traffic light, traffic sign |
| **Comfort** | Noise complaints, construction count, peak speed drop, cars per 100 residents, complaint resolution time | Vegetation, car (-), truck (-), sky |
| **Pleasurability** | Restaurant density, event frequency/diversity, young adult concentration, business growth | Vegetation, terrain, person, bicycle |

### 6. Outcome Variable

Three options, in order of increasing effort:

| Option | Source | Pros | Cons |
|---|---|---|---|
| **A. Traffic speed as proxy** | Traffic speed data | No human labeling needed; immediate | Measures congestion, not walkability directly |
| **B. Composite index** | Weighted combination of features | Can use paper's regression coefficients as initial weights; no survey needed | Circular if same features used for prediction |
| **C. Human perception survey** | Web-based rating tool (200+ images, 10–20 raters) | Ground truth comparable to paper; validates against TLV-specific perception | Requires recruiting raters and building a rating tool |

**Recommended approach:** Start with Option A to build the pipeline and validate feature engineering, then conduct a small-scale survey (Option C) to calibrate and validate.

### 7. Implementation Plan

#### Phase 1: Data Collection & Pipeline (Weeks 1–2)

1. **Download all datasets**
   - Paginate through all ArcGIS traffic layers (24 months) and store as GeoJSON/GeoPackage
   - Download all CSV datasets with correct encodings
   - Download SES Excel file
   - Geocode/spatially index all datasets

2. **Acquire street imagery**
   - For each unique segment centroid, fetch a panoramic image from Google Street View API or Mapillary
   - Store images with segment ID as filename

3. **Build spatial database**
   - Import all datasets into a spatial database (PostGIS or GeoPackage)
   - Create spatial indices for efficient buffer queries
   - Define segment-to-neighborhood mapping

#### Phase 2: Feature Engineering (Weeks 3–4)

4. **Compute street-level features**
   - Buffer each segment (100–200m) and spatial-join businesses, complaints, closed streets, construction
   - Compute all derived features from Section 4.2 and 4.3

5. **Run semantic segmentation**
   - Apply DeepLabv3+ (Cityscapes-pretrained) to each street image
   - Extract 19 area ratios per image
   - Store as feature columns per segment

6. **Merge into master feature table**
   - One row per segment-direction
   - Columns: segment ID, direction, street name, geometry, all municipal features, all visual features, neighborhood-level features
   - Handle missing values (segments without nearby businesses, etc.)

#### Phase 3: Analysis (Weeks 5–6)

7. **Exploratory analysis**
   - Feature distributions and correlations
   - Spatial clustering and mapping of feature patterns
   - Compare municipal vs. visual features for redundancy

8. **Regression modeling**
   - Stepwise multiple linear regression (replicating paper's method) with traffic speed as initial outcome
   - Compare three models: (a) visual features only, (b) municipal features only, (c) combined
   - Identify which municipal features explain variance *beyond* visual features

9. **Walkability scoring**
   - Use regression coefficients to produce a walkability score per segment
   - Map results across Tel Aviv
   - Identify highest/lowest walkability corridors

#### Phase 4: Validation & Interpretation (Weeks 7–8)

10. **Human perception survey** (Optional but recommended)
    - Build a simple web-based rating tool showing panoramic images
    - Recruit 10–20 raters to score 200+ images on the six VWP categories
    - Compare model predictions against human ratings

11. **Interpretability**
    - If classifier is trained: apply Grad-CAM to visualize contributing image regions
    - Feature importance analysis across all VWP categories
    - Compare findings to Li et al.'s results — which features behave the same? Which differ for Tel Aviv?

12. **Documentation and deliverables**
    - Final walkability maps for Tel Aviv
    - Feature importance rankings
    - Comparison with paper's findings
    - Recommendations for urban planning interventions

### 8. Phase 1–2 Results

#### 8.1 Data Pipeline (Phase 1 — completed)

All data downloaded, cleaned, and stored in `data/processed/smarttraffic.gpkg` (243.6 MB, 15 layers).

| Layer | Rows | Type | Notes |
|---|---|---|---|
| traffic_segments | 50,947 | Spatial (polyline) | 24 months (Apr 2024 – May 2026), EPSG:4326 |
| traffic_segments_latest | 2,070 | Spatial (polyline) | May 2026, base geometry for analysis |
| neighborhood_boundaries | 71 | Spatial (polygon) | From IView2 MapServer layer 511 |
| businesses | 35,172 | Attribute | 10 categories, 72 neighborhoods |
| hotline_106 | 286,657 | Attribute | 3-level complaint hierarchy |
| construction | 15,328 | Attribute | 2020–2022, by sub-district |
| population | 33,120 | Attribute | 2010–2022, by age/gender/neighborhood |
| pop_growth | 13,509 | Attribute | Growth components by neighborhood |
| pop_migration | 73,236 | Attribute | Migration flows by age/gender |
| dwelling | 2,764 | Attribute | Residential + commercial units |
| ses | 116 | Attribute | 2017 + 2019, 18 indicators |
| digitel | 862,688 | Attribute | Municipal newsletter engagement |
| budget_capital | 9,872 | Attribute | Capital budget items |
| closed_streets | 2,006 | Attribute | 25 closure types incl. events, light rail |

Scripts: `01_download_all.py` → `02_process_csvs.py` → `03_build_geopackage.py` → `04_verify_pipeline.py`

#### 8.2 Feature Engineering (Phase 2 — completed)

Master feature table: `features` layer in GeoPackage — **2,070 rows × 27 features**.

Unit of analysis: traffic segment (`segment_id` + `direction`) from the latest month (May 2026).

**Join strategy:**
- Segments → neighborhoods: spatial join (centroid within boundary polygon, EPSG:2039 for accuracy), 2,062/2,070 matched (99.6%)
- Businesses, hotline, dwelling → `neighborhood_code` (71/71 match)
- Closed streets → `street_code` (110/148 traffic streets matched)
- Construction → `sub_district` → neighborhoods (via population data mapping)
- Population → normalized neighborhood name (88% coverage)
- SES → normalized name with manual expansion of combined entries (90.2% coverage)

**Feature coverage:**

| Category | Features | Coverage | Key Stats |
|---|---|---|---|
| Traffic (5) | avg_speed, peak_speed_drop, speed_variance, dir_speed_diff, evening_speed_recovery | 82–100% | Mean speed 14.2 kph; peak drop ratio 0.81 |
| Business (5) | restaurant_count, total_businesses, biz_diversity_index, licensed_biz_ratio, evening_biz_count | 97–99.6% | Shannon entropy diversity 1.79; 35% licensed |
| Street events (5) | event_frequency, event_diversity, light_rail_closures, parade_route_count, infra_closure_count | 100% | Filled with 0 where no closures recorded |
| Complaints (2) | noise_complaints, infra_complaints | 99.6% | Infrastructure complaints 2× noise complaints |
| Construction (2) | construction_starts, construction_completion_rate | 84% | Completion rate ~0.96 (healthy) |
| Demographics (3) | female_pop_growth_yoy, young_adult_share, elderly_share | 88% | 26% young adults (20–34), 12.4% elderly (65+) |
| Dwelling (2) | residential_density, commercial_to_residential_ratio | 95–98% | Commercial-to-residential ratio 1.87 |
| SES (3) | ses_cluster, cars_per_100_residents, avg_monthly_income_per_capita | 90.2% | Mean SES cluster 5.6, 46 cars/100 residents |

**Spatial patterns observed in feature maps:**
- Clear north-south SES gradient (wealthier north, lower SES south)
- Restaurant density concentrated in old north / city center
- Noise complaints hotspots in dense central/south areas
- Young adult concentration in central neighborhoods
- Higher traffic speeds on arterials in north/east, slower in dense center

Script: `05_feature_engineering.py`

#### 8.3 Analysis (Phase 3 — completed)

Script: `06_analysis.py` — produces 6 diagnostic plots, neighborhood walkability CSV, and `features_scored` GeoPackage layer.

**Regression models** (outcome: avg_speed as walkability proxy):

| Model | Predictors | N | Adj-R² | AIC |
|---|---|---|---|---|
| A: Traffic features only | 4 | 1,635 | 0.178 | 8,901 |
| B: Municipal (stepwise) | 12 | 1,630 | 0.212 | 8,627 |
| C: Combined (stepwise) | 17 | 1,278 | 0.354 | 6,420 |

Municipal features alone (Model B) outperform traffic pattern features (Model A), and combining both (Model C) nearly doubles the explained variance. This supports the project's thesis that operational/demographic data captures walkability dimensions invisible to traffic sensors alone.

**Stepwise-selected municipal predictors** (Model B, all p<0.01):
- **Strongest negative**: elderly_share (β=-33.0), female_pop_growth_yoy (β=-23.4), licensed_biz_ratio (β=-6.9), ses_cluster (β=-1.4) — neighborhoods with more elderly, growing female pop, regulated businesses, and higher SES have *lower* average speeds (more pedestrian-oriented)
- **Strongest positive**: young_adult_share (β=+12.1), cars_per_100_residents (β=+0.38), infra_closure_count (β=+0.44) — young-adult areas, car-heavy areas, and streets with infrastructure work have higher speeds

**Multicollinearity** (VIF analysis):
- restaurant_count ≈ evening_biz_count (r=0.999, VIF >1000) — same underlying signal
- ses_cluster ≈ avg_monthly_income (r=0.975)
- noise_complaints ≈ infra_complaints (r=0.87)
- Recommendation: drop evening_biz_count, avg_monthly_income, and one of noise/infra complaints in future modeling

**PCA walkability composite score** (0–100 scale):
- PC1 explains 26% of variance; 5 PCs explain 65%
- Top positive loadings: evening businesses, restaurants, total businesses, young adult share
- Top negative loadings: noise complaints, infrastructure complaints, residential density
- **Most walkable**: Rothschild Blvd / Lev Tel Aviv (score ~100) — Tel Aviv's iconic pedestrian boulevard
- **Least walkable**: Modai Yitzhak / Tzmerot Ayalon (score ~0) — car-oriented arterial
- Clear spatial pattern: high scores in central/old-north Tel Aviv, low scores in peripheral residential neighborhoods

**Neighborhood walkability ranking** (39 neighborhoods scored):
- Top 5: לב תל-אביב (93.6), הצפון הישן-דרומי (73.1), הצפון הישן-צפוני (62.1), מונטיפיורי (48.0), פלורנטין (45.9)
- Bottom 5: נוה דן (2.9), רביבים (4.9), רמת החייל (9.0), נאות אפקה ב' (10.3), צמרות איילון (10.4)

Outputs in `data/processed/analysis/`: `01_distributions.png`, `02_correlation.png`, `03_regression_coefs.png`, `04_pca_walkability.png`, `05_walkability_map.png`, `06_neighborhood_ranking.png`, `neighborhood_walkability.csv`

#### 8.4 Validation & Interpretation (Phase 4 — completed)

Script: `07_validation.py` — produces 4 additional plots, interactive Folium map, comparison CSV, neighborhood profiles, and recommendations report.

**Permutation feature importance** (top 5 by R² decrease):

| Feature | Importance | Category |
|---|---|---|
| restaurant_count | 2.668 | Business / Pleasurability |
| cars_per_100_residents | 2.127 | SES / Comfort |
| ses_cluster | 1.822 | SES / Control |
| noise_complaints | 0.790 | Complaints / Safety+Comfort |
| total_businesses | 0.400 | Business / Walkability |

**VWP category importance** (cumulative permutation importance of mapped features):
- Walkability (overall): 5.27 — dominated by restaurant_count + cars_per_100_residents
- Pleasurability: 3.18 — restaurants, total businesses, young adult share
- Comfort: 3.09 — cars per 100 residents, noise complaints
- Safety: 1.19 — noise complaints, directional speed differential, female pop growth
- Accessibility: 0.33 — elderly share, construction starts
- Feasibility: 0.08 — residential density, business diversity index

**Comparison with Li et al. (2022):**

| VWP Category | Paper's Visual Feature | Our Municipal Proxy | Alignment |
|---|---|---|---|
| Walkability | Vegetation, sidewalk, person, bicycle | Business density, restaurants, residential density | Both identify street vitality as key |
| Safety | Vegetation (+), truck/motorcycle (-) | Female pop growth, evening businesses, licensed biz ratio | Novel: female growth has no visual equivalent |
| Comfort | Car (-), truck (-), sky | Noise complaints, construction, cars per 100 residents | Strong: car density mirrors car/truck pixel ratio |
| Pleasurability | Person, bicycle, terrain | Restaurants, events, young adult share | Events/restaurants capture liveliness from person pixels |
| Accessibility | Sidewalk (+), fence/wall (-) | Infrastructure complaints, construction, light rail | Complaints = maintained vs. degraded sidewalks |
| Feasibility | Road, traffic light/sign, fence (-) | Business diversity, commercial-to-residential ratio | Mixed-use diversity ≈ land-use visual reading |

**Novel contributions** not capturable by street imagery:
- Female population growth as safety proxy (revealed residential preference)
- Licensed business ratio as streetscape maintenance/regulation signal
- Evening business density as "eyes on the street" at night (Jane Jacobs)
- SES cluster as confound control (wealthier neighborhoods = better infrastructure)

**Deliverables:**
- Interactive walkability map: `data/processed/analysis/walkability_map.html` (Folium, color-coded by score)
- Neighborhood profiles heatmap: `10_neighborhood_profiles.png`
- Paper comparison table: `09_paper_comparison.png`, `paper_comparison.csv`
- Permutation importance: `07_permutation_importance.png`
- VWP category chart: `08_vwp_category_importance.png`
- Recommendations report: `recommendations.txt`
- Scored features layer: `features_scored` in GeoPackage

**Key policy recommendations:**
1. **Business vitality**: Encourage mixed-use ground floors in low-scoring neighborhoods (Ramat HaChayal, Rabiviim, Neve Dan)
2. **Street events**: Expand cultural events to peripheral neighborhoods to activate street space
3. **Complaint-driven maintenance**: Prioritize complaint resolution in walkability-improvement target areas
4. **Demographic tracking**: Monitor female population growth and young adult concentration as early-warning walkability indicators
5. **Car dependency**: Traffic calming and parking policy in high-car-ownership areas

**Limitations:**
- No human perception survey (ground truth); avg_speed used as proxy only
- No visual features (street imagery not acquired in this phase)
- Neighborhood-level features assigned uniformly to all segments within each neighborhood
- Construction data only through 2022; population through 2022
- Durbin-Watson = 1.16 suggests positive spatial autocorrelation in residuals

### 9. Technical Stack

| Component | Tool |
|---|---|
| Data storage | GeoPackage or PostGIS |
| Spatial operations | GeoPandas + Shapely |
| Data processing | Python (pandas, numpy) |
| Semantic segmentation | PyTorch + DeepLabv3+ (torchvision, Cityscapes-pretrained) |
| Regression | scikit-learn (stepwise via statsmodels) |
| Classification | PyTorch (DenseNet or ResNet) |
| Interpretability | Grad-CAM (pytorch-grad-cam) |
| Visualization | Folium / Kepler.gl for maps, matplotlib/seaborn for charts |
| Street imagery | Google Street View Static API or Mapillary API |

### 10. Expected Contributions

1. **A replicable walkability assessment framework for Tel Aviv** using freely available municipal data, demonstrating that operational data can complement or partially substitute for visual perception surveys.

2. **Empirical comparison of visual vs. municipal features** for walkability prediction — testing whether business vitality, complaint patterns, and demographic shifts capture dimensions of walkability that pixel ratios miss.

3. **Tel Aviv-specific walkability maps** at street-segment resolution, actionable for urban planning.

4. **Methodological contribution**: extending the Li et al. (2022) framework with non-visual features, applicable to any city with open municipal data.
