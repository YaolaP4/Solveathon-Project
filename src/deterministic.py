"""Layer 1 - deterministic checks and objective features. No semantic AI.

Reads data/processed/grants_cleaned.csv (Layer 0) and writes
data/processed/grants_features.csv, the input to Layer 2 and Layer 4.

All date math uses agency/priorities.json -> as_of_date, never today().

Hard filters are deliberately few (recall over precision). Only these are removed
from Layer 2, and they stay in the file with a reason:
  * a posted grant whose close date is before as_of_date   (expired)
  * a posted grant whose archive date is before as_of_date (archived)
  * status other than posted/forecasted, or a malformed record
Everything else - eligibility lists, cost sharing, missing data, stale
forecasts - becomes a feature, not a deletion rule.

Usage:
    python src/deterministic.py
"""

import math
import re

import numpy as np
import pandas as pd

import config
from clean_data import CLEANED

NIH_PREFIX = "HHS-NIH"
STATE_TEXT = re.compile(r"\bstates?\b|state (?:government|agenc|health department|medicaid)", re.I)
COST_SHARE_TEXT = re.compile(r"cost[- ]shar|matching funds|non-federal match|match requirement", re.I)
APPLICANT_FLAGS = {
    "state_government_listed": "state_governments",
    "county_government_listed": "county_governments",
    "city_government_listed": "city_or_township_governments",
    "public_university_listed": "public_and_state_institutions_of_higher_education",
    "nonprofit_listed": "nonprofits_non_higher_education_with_501c3",
    "tribal_government_listed": "federally_recognized_native_american_tribal_governments",
    "other_listed": "other",
}


def deadline_score(days, rolling: bool, cfg: dict) -> float:
    """0 at <= zero_at days, 10 at >= full_at days, linear between.
    Rolling deadlines get a fixed score; unknown deadlines stay missing (NaN)
    so Layer 4 can apply its explicit missing-deadline rule instead of a fake 0."""
    if rolling:
        return float(cfg["rolling_deadline_score"])
    if days is None or pd.isna(days):
        return math.nan
    lo, hi = cfg["zero_at_or_below_days"], cfg["full_at_or_above_days"]
    return round(float(np.clip((days - lo) / (hi - lo) * 10, 0, 10)), 2)


def award_estimate(row) -> tuple[float, str]:
    """Best single-award estimate: ceiling, else total/expected awards, else floor."""
    if pd.notna(row["award_ceiling"]):
        return row["award_ceiling"], "award_ceiling"
    total, n = row["estimated_total_program_funding"], row["expected_number_of_awards"]
    if pd.notna(total) and pd.notna(n) and n >= 1:
        return total / n, "total_funding / expected_awards"
    if pd.notna(row["award_floor"]):
        return row["award_floor"], "award_floor"
    return math.nan, "unknown"


def financial_value_score(award, cost_share: bool, cfg: dict) -> float:
    """Log scale: 0 at zero_at_award, 10 at full_at_award. Unknown award gets a
    fixed below-neutral score (not 0 - many large programs omit amounts)."""
    if pd.isna(award):
        score = float(cfg["missing_award_score"])
    else:
        lo, hi = math.log10(cfg["zero_at_award"]), math.log10(cfg["full_at_award"])
        score = float(np.clip((math.log10(award) - lo) / (hi - lo) * 10, 0, 10))
    if cost_share:
        score = max(0.0, score - cfg["cost_share_penalty_points"])
    return round(score, 2)


def deadline_flag(days, forecast: bool, rolling: bool) -> str:
    if forecast:
        return "forecast"
    if rolling:
        return "rolling"
    if pd.isna(days):
        return "missing_deadline"
    if days < 0:
        return "expired"
    for limit, name in ((7, "deadline_under_7_days"), (14, "deadline_under_14_days"),
                        (30, "deadline_under_30_days")):
        if days < limit:
            return name
    return "deadline_comfortable"


def build(cleaned: pd.DataFrame | None = None, agency: dict | None = None) -> pd.DataFrame:
    agency = agency or config.load_agency()
    cfg = agency["layer1"]
    df = cleaned.copy() if cleaned is not None else pd.read_csv(CLEANED)
    as_of = pd.Timestamp(agency["as_of_date"])
    df["as_of_date"] = as_of.date()

    forecast = df["is_forecast"].astype(str).str.lower().eq("true")
    df["is_forecast"] = forecast
    df["track"] = np.where(forecast, "forecast", "open")
    close = pd.to_datetime(df["close_date"], errors="coerce")
    fc_close = pd.to_datetime(df["forecasted_close_date"], errors="coerce")
    archive = pd.to_datetime(df["archive_date"], errors="coerce")

    # Deadline
    df["days_until_close"] = (close - as_of).dt.days.where(~forecast)
    df["forecast_days_until_close"] = (fc_close - as_of).dt.days.where(forecast)
    rolling_re = re.compile(cfg["rolling_deadline_pattern"], re.I)
    df["rolling_deadline"] = (~forecast & close.isna()
                              & df["close_date_description"].fillna("").map(lambda t: bool(rolling_re.search(t))))
    df["deadline_flag"] = [deadline_flag(d, f, r) for d, f, r in
                           zip(df["days_until_close"], forecast, df["rolling_deadline"])]
    df["deadline_score"] = [math.nan if f else deadline_score(d, r, cfg["deadline_score"])
                            for d, f, r in zip(df["days_until_close"], forecast, df["rolling_deadline"])]
    # A forecast whose forecasted close date has passed was probably posted under
    # another record, delayed, or dropped - kept, but flagged for the watchlist.
    df["stale_forecast"] = forecast & (fc_close < as_of)

    # Funding
    est = df.apply(award_estimate, axis=1, result_type="expand")
    df["award_estimate"], df["award_estimate_source"] = est[0], est[1]
    df["average_possible_award"] = (df["estimated_total_program_funding"] / df["expected_number_of_awards"]).where(
        df["expected_number_of_awards"] >= 1)
    df["funding_known"] = df["award_estimate"].notna()
    df["large_award"] = df["award_estimate"] >= 1_000_000
    cost_share = df["is_cost_sharing"].astype(str).str.lower().eq("true")
    df["requires_cost_share"] = np.where(cost_share, "True", np.where(df["is_cost_sharing"].isna(), "Unknown", "False"))
    df["cost_share_mentioned_in_text"] = df["summary_description"].fillna("").str.contains(COST_SHARE_TEXT)
    df["financial_value_score"] = [financial_value_score(a, c, cfg["financial_value_score"])
                                   for a, c in zip(df["award_estimate"], cost_share)]

    # Structured eligibility: signals only, never a filter
    types = df["applicant_types"].fillna("").str.split(";")
    for col, token in APPLICANT_FLAGS.items():
        df[col] = types.map(lambda t, token=token: token in t)
    df["eligibility_text_mentions_state"] = df["applicant_eligibility_description"].fillna("").str.contains(STATE_TEXT)
    df["is_nih"] = df["agency_code"].fillna("").str.startswith(NIH_PREFIX)

    # Conservative hard filters
    expired = ~forecast & close.notna() & (close < as_of)
    archived = ~forecast & archive.notna() & (archive < as_of) & ~expired
    bad_status = ~df["opportunity_status"].isin(["posted", "forecasted"])
    malformed = df["malformed"].astype(str).str.lower().eq("true")
    df["hard_filter_reason"] = ""
    for mask, reason in ((malformed, "malformed record"), (bad_status, "status not posted/forecasted"),
                         (archived, f"archived before {as_of.date()}"), (expired, f"closed before {as_of.date()}")):
        df.loc[mask, "hard_filter_reason"] = reason
    df["hard_filtered"] = df["hard_filter_reason"] != ""
    return df


def run() -> pd.DataFrame:
    df = build()
    config.LAYER1_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.LAYER1_OUTPUT, index=False)
    kept = df[~df["hard_filtered"]]
    print(f"Layer 1: {len(df)} grants, {df['hard_filtered'].sum()} hard-filtered, {len(kept)} go to Layer 2 "
          f"({(kept['track'] == 'open').sum()} open, {(kept['track'] == 'forecast').sum()} forecast)")
    print(df["hard_filter_reason"].replace("", "(kept)").value_counts().to_string())
    print("Deadline flags (kept):\n" + kept["deadline_flag"].value_counts().to_string())
    print(f"Stale forecasts: {kept['stale_forecast'].sum()};  award known: {kept['funding_known'].sum()}/{len(kept)}")
    print(f"Wrote {config.LAYER1_OUTPUT}")
    return df


if __name__ == "__main__":
    run()
