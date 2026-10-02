"""Layer 0 - data cleaning and normalization. No judgment about relevance.

    python src/clean_data.py

Reads  data/raw/grants.csv
Writes data/processed/grants_cleaned.csv

What it does: parse dates and numbers, normalize booleans, drop exact duplicate
opportunity ids, add `grant_id` (= opportunity_id) and plain-text helper columns.

What it deliberately does NOT do:
  * Text columns (title, summary, eligibility, applicant types, listings, ...) stay
    exactly as exported, raw HTML and trailing spaces included. Layers 2-3 strip HTML
    themselves when they build prompts, and unchanged text keeps their cached model
    responses valid. HTML-free versions are added as `summary_text` and `grant_text`.
  * Blanks stay blank. A blank `is_cost_sharing` is unknown, not False.
  * Zero award amounts are kept as 0 here; Layer 1 decides they are placeholders.
"""

import pandas as pd

import config
from text_utils import strip_html

CLEANED = config.DATA / "processed" / "grants_cleaned.csv"

DATE_COLS = ["post_date", "close_date", "archive_date", "forecasted_post_date",
             "forecasted_close_date", "forecasted_award_date", "forecasted_project_start_date"]
NUM_COLS = ["award_floor", "award_ceiling", "estimated_total_program_funding",
            "expected_number_of_awards"]
BOOL_COLS = ["is_forecast", "is_cost_sharing"]
TEXT_COLS = ["opportunity_title", "opportunity_status", "agency_name", "top_level_agency_name",
             "summary_description", "applicant_types", "applicant_eligibility_description",
             "opportunity_assistance_listings", "funding_instruments"]
_BOOL_MAP = {"true": True, "yes": True, "1": True, "false": False, "no": False, "0": False}


def to_bool(series: pd.Series) -> pd.Series:
    """'True'/'False' -> bool; anything else (blank, junk) -> <NA>."""
    return series.astype(str).str.strip().str.lower().map(_BOOL_MAP).astype("boolean")


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return the cleaned frame plus a small report of what was fixed or dropped."""
    df = raw.copy()
    report = {"rows_in": len(df)}

    # Text is kept exactly as exported (no trimming): Layers 2-3 build their prompts, and
    # their cache keys, from these strings. Only the status is trimmed, because Layer 1
    # compares it against fixed words.
    for c in TEXT_COLS:
        df[c] = df[c].fillna("").astype(str) if c in df else ""
    df["opportunity_status"] = df["opportunity_status"].str.strip()

    # Dates and numbers. Count values that were present but unparseable.
    report["unparseable"] = {}
    for c in DATE_COLS + NUM_COLS:
        if c not in df:
            df[c] = pd.NaT if c in DATE_COLS else float("nan")
            continue
        present = df[c].astype(str).str.strip() != ""
        parsed = (pd.to_datetime(df[c], errors="coerce") if c in DATE_COLS
                  else pd.to_numeric(df[c], errors="coerce"))
        bad = int((present & parsed.isna()).sum())
        if bad:
            report["unparseable"][c] = bad
        df[c] = parsed

    for c in BOOL_COLS:
        df[c] = to_bool(df[c]) if c in df else pd.array([pd.NA] * len(df), dtype="boolean")
    report["is_forecast_unknown"] = int(df["is_forecast"].isna().sum())
    df["is_forecast"] = df["is_forecast"].fillna(False)

    df["opportunity_id"] = df["opportunity_id"].astype(str).str.strip()
    dup = df.duplicated("opportunity_id", keep="first")
    report["duplicate_ids_dropped"] = int(dup.sum())
    df = df[~dup].copy()
    df["grant_id"] = df["opportunity_id"]

    df["summary_text"] = df["summary_description"].map(strip_html)
    df["grant_text"] = (df["opportunity_title"] + "\n" + df["summary_text"]
                        + "\n" + df["applicant_eligibility_description"].map(strip_html))

    report["rows_out"] = len(df)
    return df.sort_values("grant_id", kind="stable").reset_index(drop=True), report


def main() -> None:
    raw = pd.read_csv(config.RAW_GRANTS, dtype=str, keep_default_na=False)
    df, report = clean(raw)
    CLEANED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEANED, index=False)
    print(f"Layer 0: {report['rows_in']} rows in, {report['rows_out']} out "
          f"({report['duplicate_ids_dropped']} duplicate ids dropped) -> {CLEANED}")
    if report["unparseable"]:
        print(f"  WARNING unparseable values (turned into blanks): {report['unparseable']}")
    if report["is_forecast_unknown"]:
        print(f"  WARNING {report['is_forecast_unknown']} rows had no is_forecast value; treated as open")


if __name__ == "__main__":
    main()
