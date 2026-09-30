"""Layer 0 - data cleaning and normalization. No judgments about relevance.

Reads data/raw/grants.csv (the starter-kit Grants.gov export) and writes
data/processed/grants_cleaned.csv plus data/processed/data_quality.json.

What it does:
  * grant_id = opportunity_id; exact duplicate ids removed
  * dates -> ISO dates; numbers -> numeric
  * placeholder amounts (0, 999,999,999, 2^31) -> missing, and counted
  * booleans normalized
  * HTML stripped from free text (1,040 of 1,662 summaries contain HTML)
  * applicant_types normalized to a sorted ';'-list
  * grant_text = title + summary + eligibility (for keyword matching)
  * data-quality flags: missing summary / eligibility / deadline / award info

Usage:
    python src/clean_data.py
"""

import json

import pandas as pd

import config
from text_utils import strip_html

DATE_COLUMNS = ["post_date", "close_date", "archive_date", "forecasted_post_date",
                "forecasted_close_date", "forecasted_award_date", "forecasted_project_start_date"]
MONEY_COLUMNS = ["award_floor", "award_ceiling", "estimated_total_program_funding"]
TEXT_COLUMNS = ["opportunity_title", "summary_description", "applicant_eligibility_description",
                "close_date_description", "funding_category_description", "agency_contact_description"]
# Values Grants.gov uses as "no real number" (seen in this dataset: 999,999,999 and 2^31).
PLACEHOLDER_AMOUNTS = {999999999.0, 2147483647.0, 2147483648.0}
PLACEHOLDER_COUNTS = {9999.0}

CLEANED = config.DATA / "processed" / "grants_cleaned.csv"
QUALITY = config.DATA / "processed" / "data_quality.json"


def to_bool(s: pd.Series) -> pd.Series:
    return s.map(lambda v: {"true": True, "false": False}.get(str(v).strip().lower())).astype("boolean")


def clean_amount(s: pd.Series, placeholders: set) -> tuple[pd.Series, int]:
    s = pd.to_numeric(s, errors="coerce")
    bad = s.isin(placeholders) | (s <= 0)
    return s.mask(bad), int(bad.sum())


def normalize_applicant_types(v) -> str:
    if not isinstance(v, str) or not v.strip():
        return ""
    return ";".join(sorted({t.strip().lower() for t in v.split(";") if t.strip()}))


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = raw.copy()
    quality = {"raw_rows": len(df)}

    df = df.rename(columns={"opportunity_id": "grant_id"})
    df["grant_id"] = df["grant_id"].astype(str).str.strip()
    quality["duplicate_ids_removed"] = int(df["grant_id"].duplicated().sum())
    df = df.drop_duplicates("grant_id", keep="first")
    # Same title under different opportunity numbers: kept, but flagged for review.
    df["duplicate_title"] = df["opportunity_title"].duplicated(keep=False)
    quality["rows_sharing_a_title"] = int(df["duplicate_title"].sum())

    for c in DATE_COLUMNS:
        df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    placeholder_counts = {}
    for c in MONEY_COLUMNS:
        df[c], placeholder_counts[c] = clean_amount(df[c], PLACEHOLDER_AMOUNTS)
    df["expected_number_of_awards"], placeholder_counts["expected_number_of_awards"] = clean_amount(
        df["expected_number_of_awards"], PLACEHOLDER_COUNTS)
    quality["placeholder_or_zero_amounts_set_missing"] = placeholder_counts

    for c in ["is_cost_sharing", "is_forecast"]:
        df[c] = to_bool(df[c])

    quality["summaries_with_html"] = int(df["summary_description"].fillna("").str.contains(r"<[a-zA-Z]").sum())
    for c in TEXT_COLUMNS:
        df[c] = df[c].map(strip_html)
    df["applicant_types"] = df["applicant_types"].map(normalize_applicant_types)

    df["grant_text"] = (df["opportunity_title"] + "\n" + df["summary_description"] + "\n"
                        + df["applicant_eligibility_description"]).str.strip()

    df["missing_summary"] = df["summary_description"].str.len() < 20
    df["missing_eligibility_description"] = df["applicant_eligibility_description"].str.len() == 0
    df["missing_close_date"] = df["close_date"].isna() & ~df["is_forecast"].fillna(False)
    df["missing_award_amount"] = df[["award_ceiling", "award_floor", "estimated_total_program_funding"]].isna().all(axis=1)
    df["malformed"] = df["opportunity_title"].str.len() == 0

    for flag in ["missing_summary", "missing_eligibility_description", "missing_close_date",
                 "missing_award_amount", "malformed"]:
        quality[flag] = int(df[flag].sum())
    quality["clean_rows"] = len(df)
    return df, quality


def run() -> pd.DataFrame:
    raw = pd.read_csv(config.RAW_GRANTS)
    df, quality = clean(raw)
    CLEANED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEANED, index=False)
    QUALITY.write_text(json.dumps(quality, indent=2), encoding="utf-8")
    print(f"Layer 0: {quality['raw_rows']} raw -> {quality['clean_rows']} clean rows -> {CLEANED}")
    print(json.dumps(quality, indent=2))
    return df


if __name__ == "__main__":
    run()
