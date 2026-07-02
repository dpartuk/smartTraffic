# Smart Walkability Perception — Tel Aviv

Can a city's open data reveal how walkable its streets feel — without cameras or surveys?

This project uses 8 municipal datasets from Tel Aviv (business registries, complaint logs, demographics, traffic speeds) to measure street-level walkability perception. We engineer 27 features, train regression and ML models, and produce two walkability scoring systems — a PCA composite index and a transparent weighted formula.

## Key Results

| Finding | Value |
|---------|-------|
| Municipal features alone vs. traffic features | Adj-R² 0.212 vs. 0.178 — municipal data explains more |
| Best model (Random Forest, 5-fold CV) | R² = 0.489 |
| Li et al. (2022) with deep learning on imagery | R² = 0.41–0.59 |
| PCA vs. weighted formula correlation | r = 0.950 |
| Top walkability driver | restaurant_count (importance 2.668) |

## Walkability Formula

```
Walkability = Sigma(w_i * sign_i * z_score_i), normalized to 0-100
```

| Feature | Sign | Weight |
|---------|------|--------|
| restaurant_count | + | 0.312 |
| cars_per_100_residents | - | 0.249 |
| ses_cluster | + | 0.213 |
| noise_complaints | - | 0.092 |
| total_businesses | + | 0.047 |
| elderly_share | - | 0.030 |
| speed_variance | - | 0.018 |
| dir_speed_diff | - | 0.015 |
| young_adult_share | + | 0.013 |
| female_pop_growth | + | 0.012 |

Weights derived from permutation importance of linear regression. Formula structure follows Frank et al. (2010).

## Project Structure

```
scripts/
  01_download_all.py          # Download 8 datasets from TLV Open Data Portal + ArcGIS
  02_process_csvs.py          # Parse encodings (UTF-16LE, Win-1255, UTF-8) and delimiters
  03_build_geopackage.py      # Build spatial database (16 layers, 243 MB)
  04_verify_pipeline.py       # Data quality checks
  05_feature_engineering.py   # Compute 27 features per segment (5 join strategies)
  06_analysis.py              # Distributions, correlation, VIF, regression, PCA, weighted index
  07_validation.py            # Permutation importance, VWP mapping, Folium map, recommendations
  08_presentation.py          # Generate presentation.pptx (34 slides)

data/processed/analysis/      # Figures (13 PNGs), model results (JSON), rankings (CSV)
TLV-Street-Walkability.pdf    # Final project paper
presentation.pptx             # Presentation (34 slides)
presentation_notes.md         # Slide-by-slide talking points
```

## Datasets

All freely available from the [Tel Aviv Open Data Portal](https://opendata.tel-aviv.gov.il/) and Tel Aviv ArcGIS server.

| Dataset | Records | Source |
|---------|---------|--------|
| Traffic speeds | 50,947 segments x 24 months | ArcGIS REST API |
| Business registry | ~28,000 | Azure Blob (UTF-16LE) |
| 106 Hotline complaints | ~180,000 | Azure Blob (UTF-16LE) |
| Closed streets | ~8,500 | Azure Blob (UTF-16LE) |
| Construction permits | ~15,000 | Azure Blob (Win-1255) |
| Population by age/gender | ~85,000 | Municipal server (Win-1255) |
| Dwelling units | ~4,500 | Azure Blob (Win-1255) |
| Socioeconomic index | 71 neighborhoods | Municipal server (Excel) |

## Setup

```bash
conda create -n smarttraffic python=3.11
conda activate smarttraffic
pip install geopandas pandas numpy matplotlib seaborn scikit-learn statsmodels folium python-pptx python-bidi requests openpyxl
```

Run the pipeline:
```bash
python scripts/01_download_all.py        # Download raw data
python scripts/02_process_csvs.py        # Process CSVs
python scripts/03_build_geopackage.py    # Build GeoPackage
python scripts/05_feature_engineering.py # Compute features
python scripts/06_analysis.py           # Run analysis
python scripts/07_validation.py         # Validation & maps
python scripts/08_presentation.py       # Generate presentation
```

## Based On

Li, Y., Yabuki, N., & Fukuda, T. (2022). Measuring visual walkability perception using panoramic street view images, virtual reality, and deep learning. *Sustainable Cities and Society*, 86, 104140.

## Author

Doron Peleg — Tel Aviv University, 2026
