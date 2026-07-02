"""
Process raw CSVs: standardize column names, parse dates, validate row counts.
Outputs cleaned CSVs to data/processed/ and prints a summary.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

COLUMN_MAPS = {
    "businesses": {
        "id_esek": "business_id",
        "k_shchuna": "neighborhood_code",
        "t_shchuna": "neighborhood_name",
        "sw_taun_rishui": "license_status",
        "k_category": "category_code",
        "t_category": "category_name",
        "k_anaf_rashi_merkaz_lemechkar": "industry_code",
        "t_anaf_rashi_merkaz_lemechkar": "industry_name",
        "shetach": "area_sqm",
        "k_rova": "district_code",
    },
    "construction": {
        "rn": "row_num",
        "Shana": "year",
        "Rova": "district",
        "Tat_Rova": "sub_district",
        "Ez_Stat": "stat_area",
        "Thum": "type_code",
        "teur_thum": "type_name",
        "Nose": "topic_code",
        "teur_nose": "topic_name",
        "Tat_nose": "subtopic_code",
        "teur_tat_nose": "subtopic_name",
        "Kod": "detail_code",
        "teur": "detail_name",
        "Natun": "value",
    },
    "hotline_106": {
        "RowN": "row_num",
        "new_level1idName": "category_l1",
        "new_level2idName": "category_l2",
        "new_level3idName": "category_l3",
        "Value": "value_type",
        "year_create": "year",
        "month_create": "month",
        "nam_Month_heb": "month_name_heb",
        "new_neighborhood": "neighborhood_name",
        "k_shchuna": "neighborhood_code",
        "DES_Rova": "district_name",
        "k_rova": "district_code",
        "k_tat_rova_n": "sub_district_code",
        "cnt_incidentId": "incident_count",
        "t_routingcode": "routing_code",
    },
    "closed_streets": {
        "ID": "id",
        "id_rechov": "record_id",
        "k_rechov": "street_code",
        "shem_rechov_win": "street_name",
        "me_k_rechov": "from_street_code",
        "me_shem_rechov": "from_street_name",
        "ad_k_rechov": "to_street_code",
        "ad_shem_rechov": "to_street_name",
        "me_ms_bayit": "from_house_num",
        "ad_ms_bayit": "to_house_num",
        "tr_from": "date_from",
        "tr_to": "date_to",
        "k_sug": "closure_type_code",
        "t_sug": "closure_type_name",
        "k_sgira": "closure_scope_code",
        "t_sgira": "closure_scope_name",
        "shaot": "hours_description",
        "sw_laila": "night_flag",
    },
    "population": {
        "des_min": "gender",
        "des_KvutzatGil": "age_group",
        "Num_Rova": "district_code",
        "Num_Tat_Rova": "sub_district_code",
        "des_shchuna_lamas_2011": "neighborhood_name",
        "dt_year": "year",
        "cnt_Uchlusiya": "population_count",
        "id": "id",
    },
    "pop_growth": {
        "des_MarkivGidul": "growth_component",
        "des_shchuna_lamas_2011": "neighborhood_name",
        "Num_Tat_Rova": "sub_district_code",
        "Num_Rova": "district_code",
        "cnt_GidulUchlusiya": "growth_count",
        "dt_year": "year",
        "id": "id",
    },
    "pop_migration": {
        "des_min": "gender",
        "des_KvutzatGil": "age_group",
        "des_KvutzatMarkivGidul": "migration_group",
        "des_MarkivGidul": "migration_component",
        "Num_Rova": "district_code",
        "Num_Tat_Rova": "sub_district_code",
        "des_shchuna_lamas_2011": "neighborhood_name",
        "dt_year": "year",
        "cnt_NayadutUchlusiya": "migration_count",
        "id": "id",
    },
    "dwelling": {
        "shnat_hiyuv": "billing_year",
        "cnt_yechidot_diur": "dwelling_units",
        "sug_shimush": "use_type",
        "sum_area_hiuv": "billed_area",
        "k_shchuna_lamas_2011": "neighborhood_code",
        "des_shchuna_lamas_2011": "neighborhood_name",
        "k_rova_n": "district_code",
        "k_tat_rova_n": "sub_district_code",
        "id": "id",
    },
    "digitel": {
        "mailing_date": "mailing_date",
        "title": "title",
        "new_neighborhood_code": "neighborhood_code",
        "new_neighborhood_name": "neighborhood_name",
        "merhav": "municipal_area",
        "agaf": "department",
        "Des_kvutzat_gil": "age_group",
        "count_sent": "count_sent",
        "open_mail": "count_opened",
        "click_item": "count_clicked",
        "RowN": "row_num",
    },
    "budget_capital": {
        "SHANA_TAKTZIVIT": "budget_year",
        "msr_takziv_mudkan": "updated_budget",
        "bizua_hn_zmani": "execution_to_date",
        "des_perek2": "chapter2_name",
        "des_perek3": "chapter3_name",
        "cd_seif_hn": "item_code",
        "nam_seif_takziv_sas": "item_name",
        "cd_seif_cheshbon": "account_code",
        "cd_perek5_sas": "chapter5_code",
        "fl_sachar": "salary_flag",
        "Num_Name_seif": "item_full_name",
        "calc_yehidat_hachnasa": "revenue_unit",
        "desc_fl_tiful": "handling_desc",
        "Des_sug_seif": "item_type",
        "cd_sefer": "book_code",
        "hotsaa_hachnasa_group": "expense_income_group",
        "seif_sub_group": "sub_group",
        "kod_teur_minhal": "admin_code",
        "year_for_filter": "year_filter",
    },
}

DELIMITERS = {
    "businesses": ";",
    "hotline_106": ";",
    "digitel": ";",
    "budget_capital": ";",
    "population": "|",
    "pop_growth": "|",
    "pop_migration": "|",
    "dwelling": "|",
}

DATE_COLUMNS = {
    "closed_streets": ["date_from", "date_to"],
    "population": ["year"],
    "pop_growth": ["year"],
    "pop_migration": ["year"],
    "digitel": ["mailing_date"],
}


def read_closed_streets(raw_file: Path) -> pd.DataFrame:
    """Parse closed_streets.csv where the hours_description field contains commas."""
    import csv
    rows = []
    with open(raw_file, encoding="utf-8") as f:
        header = f.readline().strip().split(",")
        n_cols = len(header)
        for line in f:
            parts = line.strip().split(",")
            if len(parts) > n_cols:
                # Rejoin the overflow into the hours_description field (second-to-last)
                fixed = parts[: n_cols - 2]
                fixed.append(",".join(parts[n_cols - 2 : -1]))
                fixed.append(parts[-1])
                parts = fixed
            rows.append(parts)
    return pd.DataFrame(rows, columns=header)


def process_csv(name: str):
    raw_file = RAW_DIR / f"{name}.csv"
    if not raw_file.exists():
        print(f"  [skip] {name}.csv not found")
        return

    if name == "closed_streets":
        df = read_closed_streets(raw_file)
    else:
        sep = DELIMITERS.get(name, ",")
        df = pd.read_csv(raw_file, encoding="utf-8", sep=sep, low_memory=False, on_bad_lines="warn")

    if name in COLUMN_MAPS:
        rename_map = {k: v for k, v in COLUMN_MAPS[name].items() if k in df.columns}
        df = df.rename(columns=rename_map)

    # Strip whitespace from string columns
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    if name in DATE_COLUMNS:
        for col in DATE_COLUMNS[name]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

    out_file = PROC_DIR / f"{name}.csv"
    df.to_csv(out_file, index=False, encoding="utf-8")

    print(f"  [done] {name}: {len(df)} rows, {len(df.columns)} columns")
    print(f"         columns: {list(df.columns)}")


def process_ses():
    raw_file = RAW_DIR / "ses.xlsx"
    if not raw_file.exists():
        print("  [skip] ses.xlsx not found")
        return

    ses_columns = {
        "kod_shchuna": "neighborhood_code",
        "name_shchuna": "neighborhood_name",
        "index_population_2019": "index_population",
        "dependency_ratio": "dependency_ratio",
        "median_age": "median_age",
        "perc_families_more_than_4_children": "pct_families_4plus_children",
        "avg_years_of_education_25_54yo": "avg_years_education",
        "perc_academic_27_54yo": "pct_academic_degree",
        "perc_receiving_income_supplement_over_19yo": "pct_income_supplement",
        "perc_women_without_income_25_54yo": "pct_women_no_income",
        "perc_earning_above_double_avg_wage": "pct_earning_above_2x_avg",
        "perc_earning_below_minimum_wage": "pct_earning_below_min",
        "perc_have_income_25_54yo": "pct_employed",
        "avg_monthly_income_per_person": "avg_monthly_income_per_capita",
        "avg_days_abroad": "avg_days_abroad",
        "avg_car_license_fee": "avg_car_license_fee",
        "cnt_cars_per_100_persons_over_16yo": "cars_per_100_residents",
    }

    all_rows = []
    for sheet_year in ["2019", "2017"]:
        df = pd.read_excel(raw_file, sheet_name=sheet_year, header=2)
        # Drop unnamed columns
        df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
        df = df.dropna(how="all")

        rename_map = {k: v for k, v in ses_columns.items() if k in df.columns}
        # Handle the year-specific eshkol column
        for col in df.columns:
            if "eshkol" in col.lower():
                rename_map[col] = "ses_cluster"
        df = df.rename(columns=rename_map)
        df["year"] = int(sheet_year)
        all_rows.append(df)

    combined = pd.concat(all_rows, ignore_index=True)
    out_file = PROC_DIR / "ses.csv"
    combined.to_csv(out_file, index=False, encoding="utf-8")
    print(f"  [done] ses: {len(combined)} rows, {len(combined.columns)} columns")
    print(f"         columns: {list(combined.columns)}")


def main():
    print("=== Processing CSV datasets ===")
    for name in COLUMN_MAPS:
        process_csv(name)

    print("\n=== Processing SES Excel ===")
    process_ses()

    print("\n=== Processing complete ===")
    for f in sorted(PROC_DIR.glob("*.csv")):
        size = f.stat().st_size / 1024
        print(f"  {f.name}: {size:.0f} KB")


if __name__ == "__main__":
    main()
