"""Layer 0 - Data cleaning and normalization.

Standardizes data/raw/grants.csv into data/processed/grants_cleaned.csv.
NO judgment about relevance happens here: nothing is dropped except exact
duplicate records, and nothing is hard-filtered (that is Layer 1).

Run:  python src/clean_data.py [--input PATH] [--output PATH]
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "grants.csv"
OUT_PATH = ROOT / "data" / "processed" / "grants_cleaned.csv"

# Reuse the project's HTML stripper when available (README: src/text_utils.strip_html).
try:
    sys.path.insert(0, str(ROOT / "src"))
    from text_utils import strip_html  # type: ignore
except Exception:  # fallback so this file also runs standalone
    def strip_html(text):
        if text is None or (isinstance(text, float) and pd.isna(text)):
            return ""
        t = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</div>", "\n", str(text))
        t = re.sub(r"(?i)<li[^>]*>", "- ", t)
        t = re.sub(r"<[^>]+>", " ", t)
        t = html.unescape(t)
        t = re.sub(r"[ \t\r\f\v\u00a0]+", " ", t)
        t = re.sub(r"\n\s*\n+", "\n\n", t)
        return t.strip()

ID_COL = "opportunity_id"
DATE_COLS = ["close_date", "post_date", "archive_date", "forecasted_post_date",
             "forecasted_close_date", "estimated_award_date",
             "estimated_project_start_date", "last_updated_date",
             "created_date", "posted_date", "close_date_explanation_date"]
NUM_COLS = ["award_floor", "award_ceiling", "estimated_total_program_funding",
            "expected_number_of_awards"]
BOOL_COLS = ["is_forecast", "is_cost_sharing", "cost_sharing",
             "is_cost_sharing_required"]
TEXT_COLS = ["opportunity_title", "agency_name", "summary_description",
             "applicant_eligibility_description", "additional_information_on_eligibility",
             "opportunity_assistance_listings", "funding_instruments",
             "funding_categories", "applicant_types", "opportunity_status",
             "opportunity_number", "category", "category_explanation",
             "cost_sharing_description", "close_date_description",
             "agency_code", "top_level_agency_name"]
LIST_COLS = ["applicant_types", "funding_instruments", "funding_categories",
             "opportunity_assistance_listings"]
TRUE = {"true", "t", "yes", "y", "1", "1.0"}
FALSE = {"false", "f", "no", "n", "0", "0.0"}
NULL_STRINGS = {"", "nan", "none", "null", "n/a", "na", "<na>", "nat"}


def _is_null(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or \
        (isinstance(v, str) and v.strip().lower() in NULL_STRINGS)


def clean_text(v) -> str:
    """Strip HTML, decode entities, collapse whitespace. Missing -> ''."""
    if _is_null(v):
        return ""
    t = strip_html(str(v))
    t = html.unescape(t).replace("\u00a0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return t.strip()


def to_bool(v):
    """True / False / <NA> (unknown). Unknown is kept distinct from False."""
    if _is_null(v):
        return pd.NA
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in TRUE:
        return True
    if s in FALSE:
        return False
    return pd.NA


def to_number(s: pd.Series) -> pd.Series:
    """'$1,250,000.00' -> 1250000.0 ; unparseable -> NaN."""
    cleaned = (s.astype("string").str.replace(r"[\$,\s]", "", regex=True)
               .replace({v: pd.NA for v in NULL_STRINGS}))
    return pd.to_numeric(cleaned, errors="coerce")


def normalize_list(v) -> str:
    """Pipe-separated, trimmed, de-duplicated, order-preserving, lowercased
    for applicant/instrument strings (assistance listings keep their case)."""
    if _is_null(v):
        return ""
    parts = re.split(r"[|;\n]+", str(v))
    seen, out = set(), []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip()
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return "|".join(out)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report: dict = {"rows_in": len(df)}
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if ID_COL not in df.columns:
        raise KeyError(f"'{ID_COL}' column not found. Columns: {list(df.columns)}")

    # --- unique IDs ---------------------------------------------------------
    df[ID_COL] = df[ID_COL].astype("string").str.strip()
    report["missing_id"] = int(df[ID_COL].isna().sum() + (df[ID_COL] == "").sum())
    df = df[df[ID_COL].notna() & (df[ID_COL] != "")]
    df["grant_id"] = df[ID_COL]

    # --- text ---------------------------------------------------------------
    html_before = 0
    if "summary_description" in df.columns:
        html_before = int(df["summary_description"].astype("string")
                          .str.contains(r"<[a-zA-Z/]|&[a-z]+;|&#\d+;", regex=True, na=False).sum())
    report["summaries_with_html_before"] = html_before
    for c in TEXT_COLS:
        if c in df.columns:
            df[c] = df[c].map(clean_text)

    # --- normalized applicant types / instruments / listings ---------------
    for c in LIST_COLS:
        if c in df.columns:
            df[c] = df[c].map(normalize_list)
    if "applicant_types" in df.columns:
        df["applicant_types_norm"] = df["applicant_types"].str.lower()

    # --- dates --------------------------------------------------------------
    for c in DATE_COLS:
        if c in df.columns:
            parsed = pd.to_datetime(df[c], errors="coerce", utc=False)
            report[f"{c}_unparseable"] = int(parsed.isna().sum() - df[c].map(_is_null).sum())
            df[c] = parsed.dt.strftime("%Y-%m-%d")   # ISO text; Layer 1 re-parses

    # --- numbers ------------------------------------------------------------
    for c in NUM_COLS:
        if c in df.columns:
            df[c] = to_number(df[c])
    if {"award_floor", "award_ceiling"} <= set(df.columns):
        swapped = (df["award_floor"] > df["award_ceiling"])
        report["award_floor_gt_ceiling"] = int(swapped.sum())
        df["award_range_inconsistent"] = swapped.fillna(False)   # flag only, do not "fix"

    # --- booleans -----------------------------------------------------------
    for c in BOOL_COLS:
        if c in df.columns:
            df[c] = df[c].map(to_bool).astype("boolean")
    if "is_forecast" in df.columns:
        df["track"] = df["is_forecast"].map(
            {True: "forecast", False: "open"}).fillna("open")   # README: track = open / forecast

    # --- combined text for semantic layers -----------------------------------
    parts = [c for c in ["opportunity_title", "summary_description",
                         "applicant_eligibility_description"] if c in df.columns]
    df["grant_text"] = df[parts].apply(lambda r: "\n".join(x for x in r if x), axis=1)

    # --- duplicates (exact only: same ID, or identical content) -------------
    n = len(df)
    df = df.drop_duplicates(subset=[ID_COL], keep="first")
    report["duplicate_ids_removed"] = n - len(df)
    n = len(df)
    content_cols = [c for c in ["opportunity_number", "opportunity_title", "agency_name",
                                "close_date", "forecasted_close_date", "summary_description"]
                    if c in df.columns]
    if content_cols:
        df = df.drop_duplicates(subset=content_cols, keep="first")
    report["duplicate_content_removed"] = n - len(df)

    # --- malformed / incomplete flags (information only) --------------------
    df["missing_title"] = df.get("opportunity_title", pd.Series("", index=df.index)).eq("")
    df["missing_description"] = df.get("summary_description", pd.Series("", index=df.index)).eq("")
    df["missing_eligibility_description"] = df.get(
        "applicant_eligibility_description", pd.Series("", index=df.index)).eq("")
    has_close = df["close_date"].notna() if "close_date" in df.columns else pd.Series(False, index=df.index)
    has_fc = df["forecasted_close_date"].notna() if "forecasted_close_date" in df.columns else pd.Series(False, index=df.index)
    df["missing_deadline"] = ~(has_close | has_fc)            # forecasts are NOT "missing"
    df["missing_award_amount"] = (df[["award_floor", "award_ceiling"]].isna().all(axis=1)
                                  if {"award_floor", "award_ceiling"} <= set(df.columns)
                                  else True)
    df["malformed_record"] = df["missing_title"] | (df["missing_description"]
                                                    & df["missing_eligibility_description"])
    for c in ["missing_title", "missing_description", "missing_eligibility_description",
              "missing_deadline", "missing_award_amount", "malformed_record"]:
        report[c] = int(df[c].sum())

    report["rows_out"] = len(df)
    return df.reset_index(drop=True), report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default=str(RAW_PATH))
    ap.add_argument("--output", default=str(OUT_PATH))
    a = ap.parse_args(argv)

    raw = pd.read_csv(a.input, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    out, rep = clean(raw)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.output, index=False)

    print(f"Layer 0: {rep['rows_in']} rows in -> {rep['rows_out']} rows out -> {a.output}")
    for k, v in rep.items():
        if k not in ("rows_in", "rows_out"):
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
