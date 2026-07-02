# Presentation Cheat-Sheet — Smart Walkability Perception
## Doron Peleg | 2026

---

### Slide 1 — Title
> "This project measures how walkable Tel Aviv's streets *feel* using only the city's own open data — no cameras, no surveys."

---

### Slides 2-3 — Project Goal
- Some streets invite walking, others make you want to drive — that feeling is Visual Walkability Perception (VWP)
- Traditional measurement: expensive surveys or street-image AI
- Our question: can a city's operational data (businesses, complaints, demographics) tell us the same thing?

---

### Slides 4-6 — The Base Paper (Li et al. 2022)
- 2,642 panoramic images, 7 cities, 30 VR raters
- 19 visual features explain 41-59% of walkability perception
- Top visual drivers: vegetation, sidewalks, traffic signs
- 6 dimensions: Walkability, Feasibility, Accessibility, Safety, Comfort, Pleasurability (Alfonzo's Hierarchy)
- This is our benchmark

---

### Slides 7-8 — Our Project
- Paper: photos + AI pixel counting + VR headsets
- Us: municipal open data (business records, complaints, demographics)
- Key insight: "A camera sees trees and cars. Municipal data sees what a camera can't — are businesses thriving? Are residents complaining? Do women feel safe enough to move in?"

---

### Slides 9-11 — Approach & Datasets
- 8 data sources | 1.3M+ records | all freely available
- Traffic speeds (ArcGIS), businesses, 106-hotline complaints, closed streets, population, SES, construction
- Unit of analysis: directed traffic segment (~100m)
- Outcome variable: avg traffic speed as walkability proxy (slower = more walkable)
- 5-step pipeline: Download → Spatial DB → Features → Modeling → Validation

---

### Slides 12-13 — 27 Features in 8 Categories
- Traffic (5): speed, peak drop, variance, directional diff, evening recovery
- Business (5): restaurants, total, diversity (Shannon entropy), licensed ratio, evening count
- Street Events (5): frequency, diversity, light rail, parades, infrastructure
- Complaints (2): noise, infrastructure
- Construction (2): starts, completion rate
- Demographics (3): female growth, young adults 20-34, elderly 65+
- Housing (2): residential density, commercial-to-residential ratio
- Socio-Economic (3): SES cluster, cars/100 residents, income
- Coverage: 82-100% across all features

---

### Slides 14-15 — Project Plan
- Phase 1 (Weeks 1-2): Data collection & pipeline
- Phase 2 (Weeks 3-4): Feature engineering — 27 features per segment
- Phase 3 (Weeks 5-6): Analysis & modeling
- Phase 4 (Weeks 7-8): Validation & interpretation
- Stack: Python, GeoPandas, statsmodels, scikit-learn, Folium

---

### Slides 16-17 — Phase 1: Data Pipeline
- 3 encodings (UTF-16LE, Win-1255, UTF-8), 4 delimiters — real data is messy
- Paginated ArcGIS API (2,000 records/request), 24 monthly layers
- Output: GeoPackage, 16 layers, 50,947 segments, 243 MB
- Data wrangling = ~40% of project effort

---

### Slide 18 — Phase 2: Feature Engineering
- Spatial join: segment centroids → 71 neighborhood polygons (99.6% match)
- Hebrew name normalization across datasets (different spellings everywhere)
- SES grouped neighborhoods needed manual mapping dictionary
- Output: 2,070 segments x 27 features

---

### Slide 19 — Phase 3: Modeling
- Multicollinearity: restaurant_count ~ evening_biz_count (r=0.999)
- 5-fold cross-validation, three models:
  - Linear Regression: R²=0.330 (baseline)
  - Neural Network: R²=0.437 (unstable, +/-0.118)
  - **Random Forest: R²=0.489 (best, stable, +/-0.022)**
- PCA walkability score: PC1 = 26% of variance

---

### Slide 20 — Phase 4: Validation
- Top importance: restaurant_count (2.67), cars_per_100 (2.13), ses_cluster (1.82)
- Mapped features to Li et al.'s 6 VWP categories
- Interactive Folium map — click any segment for details

---

### Slide 22 — Dataset Overview (1,278 segments)
- Example contrast:
  | | Rothschild (walkable) | Yerushalayim (not) |
  |---|---|---|
  | Speed | 11.6 kph | 17.3 kph |
  | Restaurants | 635 | 1 |
  | SES | 6 | 1 |
- Walkable = slow traffic, many businesses, higher SES

---

### Slide 23 — Key Finding
- Municipal features alone explain MORE speed variance than traffic's own patterns
- Combined: Adj-R² = 0.354
- Top 5:
  1. Restaurant count — street vitality signal
  2. Cars per 100 residents — car dependency = less walkable
  3. SES cluster — wealthier = better infrastructure
  4. Noise complaints — direct pedestrian discomfort
  5. Total businesses — mixed-use attracts walking

---

### Slide 24 — Walkability Map
- Most walkable: Rothschild (100), Old North south (73), Old North north (62)
- Least walkable: Neve Dan (3), Rabiviim (5), Ramat HaChayal (9)
- Pattern: central mixed-use = high; peripheral car-dependent = low

---

### Slide 25 — Comparison with Paper
- Comfort: STRONG MATCH (car pixels ↔ cars/100 residents + noise)
- Pleasurability: STRONG MATCH (person pixels ↔ restaurants + events)
- Safety: NOVEL (vegetation ↔ female pop growth — no visual equivalent!)
- Accessibility: GOOD PROXY (sidewalk pixels ↔ infra complaints + construction)

---

### Slide 26 — Neighborhood Ranking
- North-south SES gradient matches walkability
- Jaffa = mid-range (high vitality BUT high complaints)
- Low-scoring areas share: few restaurants, few events, high car ownership

---

### Slide 27 — Three Models Compared
- RF > NN > LR
- Neural net: +32% over linear, but unstable (too few samples for deep learning)
- Random Forest: best accuracy, most stable, no tuning needed — practical for cities

---

### Slide 28 — Feature Importance Shifts
- Linear Regression top feature: restaurant_count (municipal)
- Random Forest top feature: speed_variance (traffic)
- Both agree: business count + speed patterns are key
- Relationship isn't purely linear — RF captures interactions

---

### Slide 29 — Closing
> "A city's own data — business registries, complaint logs, demographics — reveals how walkable its streets feel, capturing dimensions that even street-level photos miss."
>
> **No cameras needed. No surveys. Just open data.**

---

## Quick FAQ Prep

**Q: Why traffic speed as a proxy for walkability?**
A: Walkable streets naturally slow traffic — pedestrian activity, narrow lanes, mixed use. Li et al. also found negative correlation between vehicle presence and walkability perception.

**Q: R²=0.489 — is that good enough?**
A: Li et al. got 0.41-0.59 with street photos + deep learning. We're in that range with just tabular open data. Also, walkability is inherently subjective — perfect prediction isn't realistic.

**Q: Can this work for other cities?**
A: Yes — any city publishing business registries, complaint logs, and demographic data. The pipeline is open-source Python. The specific features may shift, but the methodology transfers.

**Q: What about the multicollinearity (restaurant ≈ evening biz)?**
A: We kept both for now — they measure the same thing (street vitality). In production, drop one. RF handles collinearity well; it hurt linear regression more.

**Q: What would you do next?**
A: (1) Add green space / tree canopy data if available, (2) validate against actual pedestrian surveys, (3) test temporal changes — does walkability shift when new businesses open?
