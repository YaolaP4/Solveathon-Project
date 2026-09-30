"""Layer 1 - deterministic checks. Plain pandas, no AI, no semantic judgment.

    python src/clean_data.py && python src/deterministic.py

Reads  data/processed/grants_cleaned.csv (Layer 0), agency/priorities.json
Writes data/processed/grants_features.csv   <- input to Layers 2, 3 and 4
       docs/layer1_report.md                <- counts per flag, for auditing

Rules
  * Dates use the fixed `as_of_date` from priorities.json, never today().
  * Forecasts are a separate track (`track = forecast`). They have no close date by
    design, so they are never expired and never get a deadline score.
  * Hard filters are conservative: a grant is only flagged `hard_filtered` when its
    close date is before as_of_date or its status says closed/archived/cancelled.
    Filtered rows STAY in the file (Layer 5 samples them to look for false negatives).
  * Structured eligibility (who is listed as an applicant) is a signal, never a filter.
  * Layer 4 needs two objective 0-10 scores from here: `financial_value_score`
    (always a number) and `deadline_score` (blank when there is no real deadline).
"""

import re

import numpy as np
import pandas as pd

import config
from clean_data import BOOL_COLS, CLEANED, DATE_COLS, NUM_COLS, to_bool
from text_utils import strip_html

REPORT = config.ROOT / "docs" / "layer1_report.md"

# Defaults mirror agency/priorities.json -> "layer1"; the JSON wins when both exist.
DEFAULTS = {
    "as_of_date": "2026-09-30",
    "data_pulled_date": "2026-08-18",
    "close_date_placeholder_year_min": 2090,
    "deadline_days": [7, 14, 30],
    "deadline_score_points": [[0, 0], [7, 2], [14, 4], [30, 7], [60, 10]],
    "large_award_usd": 1_000_000,
    "few_awards_max": 3,
    "min_description_chars": 100,
    "broad_applicant_types_min": 12,
    "financial_log_min_usd": 100_000,
    "financial_log_max_usd": 10_000_000,
    "financial_total_only_cap": 7.0,
    "financial_unknown_score": 5.0,
    "hard_filter_statuses": ["closed", "archived", "cancelled", "canceled"],
}

# Grants.gov applicant-type slugs, grouped into the signals we report.
STATE = {"state_governments"}
LOCAL = {"county_governments", "city_or_township_governments", "special_district_governments"}
HIGHER_ED = {"public_and_state_institutions_of_higher_education",
             "private_institutions_of_higher_education"}
NONPROFIT = {"nonprofits_non_higher_education_with_501c3",
             "nonprofits_non_higher_education_without_501c3"}
TRIBAL = {"federally_recognized_native_american_tribal_governments",
          "other_native_american_tribal_organizations"}
FOR_PROFIT = {"for_profit_organizations_other_than_small_businesses", "small_businesses"}
OTHER_KNOWN = {"individuals", "unrestricted", "other", "independent_school_districts",
               "public_and_indian_housing_authorities"}
KNOWN_SLUGS = STATE | LOCAL | HIGHER_ED | NONPROFIT | TRIBAL | FOR_PROFIT | OTHER_KNOWN

_COST_SHARE_WORDS = re.compile(
    r"cost[- ]?shar|matching (funds|requirement|share|contribution)|match(ing)? (is )?required"
    r"|non-federal (share|match)", re.I)
_COST_SHARE_PCT = [
    re.compile(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|percent)\s*(?:cost[- ]?shar\w*|match\w*|non-federal)", re.I),
    re.compile(r"(?:cost[- ]?shar\w*|match\w*)[^.%\n]{0,40}?(\d{1,3}(?:\.\d+)?)\s*(?:%|percent)", re.I),
]
_STATE_TEXT = re.compile(r"state (government|agenc|department|health|public health)|departments? of health", re.I)
_INDIV_ONLY = re.compile(r"(only|solely|exclusively)[^.]{0,40}individuals?|individuals?[^.]{0,20}(only|solely)", re.I)
_HIGHER_ED_ONLY = re.compile(
    r"(only|limited to|restricted to|solely)[^.]{0,80}(institutions? of higher education|universit|colleges?)", re.I)
_TRIBAL_ONLY = re.compile(r"(only|limited to|restricted to|solely)[^.]{0,80}(tribal|tribe|native american)", re.I)


# ── Loading ─────────────────────────────────────────────────────────────────

def settings(agency: dict) -> dict:
    """Defaults, overridden by priorities.json -> layer1, plus the fixed as_of_date."""
    cfg = {**DEFAULTS, **{k: v for k, v in (agency.get("layer1") or {}).items() if not k.startswith("_")}}
    cfg["as_of_date"] = agency.get("as_of_date", cfg["as_of_date"])
    return cfg


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Re-type grants_cleaned.csv after reading it back as strings."""
    df = df.copy()
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in BOOL_COLS:
        df[c] = to_bool(df[c])
    df["is_forecast"] = df["is_forecast"].fillna(False)
    return df


def load_cleaned() -> pd.DataFrame:
    return coerce_types(pd.read_csv(CLEANED, dtype=str, keep_default_na=False))


# ── Helpers ─────────────────────────────────────────────────────────────────

def _matches(series: pd.Series, pattern: re.Pattern) -> pd.Series:
    return series.map(lambda t: bool(pattern.search(t)))


def parse_cost_share_percent(text: str) -> float:
    for pattern in _COST_SHARE_PCT:
        m = pattern.search(text)
        if m and 0 < float(m.group(1)) <= 100:
            return float(m.group(1))
    return float("nan")


# ── Feature groups ──────────────────────────────────────────────────────────

def add_deadline_features(df: pd.DataFrame, cfg: dict) -> None:
    as_of = pd.Timestamp(cfg["as_of_date"])
    fc = df["is_forecast"].astype(bool)
    is_open = ~fc

    # Placeholder dates such as 2099-01-01 mean "no real deadline given".
    placeholder = df["close_date"].dt.year >= cfg["close_date_placeholder_year_min"]
    real_close = df["close_date"].where(~placeholder)
    df["close_date_placeholder"] = is_open & placeholder
    df["close_date_real"] = real_close.where(is_open)

    days = (real_close - as_of).dt.days
    df["days_until_close"] = days.where(is_open)
    df["missing_deadline"] = is_open & real_close.isna()
    df["expired"] = is_open & (real_close < as_of)        # closing ON as_of is still open
    live = is_open & real_close.notna() & ~df["expired"]
    d7, d14, d30 = cfg["deadline_days"]
    df["deadline_under_7_days"] = live & (days <= d7)
    df["deadline_under_14_days"] = live & (days <= d14)
    df["deadline_under_30_days"] = live & (days <= d30)
    df["deadline_comfortable"] = live & (days > d30)

    # Layer 4 input (0-10). Blank when there is no real deadline or the grant is a forecast.
    xs, ys = zip(*cfg["deadline_score_points"])
    score = pd.Series(np.interp(days.fillna(0), xs, ys), index=df.index)
    df["deadline_score"] = score.where(is_open & real_close.notna()).round(2)

    # Forecast track: when might it open? Never hard-filtered.
    fpost, fclose = df["forecasted_post_date"], df["forecasted_close_date"]
    df["forecast_missing_post_date"] = fc & fpost.isna()
    df["days_until_forecast_post"] = (fpost - as_of).dt.days.where(fc)
    df["forecast_post_passed"] = fc & (fpost < as_of)
    df["forecast_close_passed"] = fc & (fclose < as_of)
    # Post date has passed but the forecast close date has not: it may already be open
    # on Grants.gov, so the watchlist should say "check now".
    df["forecast_check_now"] = df["forecast_post_passed"] & ~df["forecast_close_passed"]
    df["archive_date_passed"] = df["archive_date"] < as_of


def add_funding_features(df: pd.DataFrame, cfg: dict) -> None:
    three = ["award_ceiling", "estimated_total_program_funding", "expected_number_of_awards"]
    # A 0 in these fields is a placeholder, not a real amount.
    df["funding_zero_placeholder"] = (df[three] == 0).any(axis=1)
    for c in three:
        df[c] = df[c].where(df[c] > 0)

    ceiling, total, n_awards = df["award_ceiling"], df["estimated_total_program_funding"], df["expected_number_of_awards"]
    avg = total / n_awards
    df["average_possible_award"] = avg
    df["financial_basis"] = np.select(
        [ceiling.notna(), avg.notna(), total.notna()],
        ["award_ceiling", "average_award", "program_total"], "unknown")
    amount = ceiling.fillna(avg).fillna(total)
    df["award_value_usd"] = amount
    df["funding_known"] = amount.notna()
    df["missing_award_amount"] = amount.isna()
    df["large_award"] = amount >= cfg["large_award_usd"]
    df["few_awards"] = n_awards.between(1, cfg["few_awards_max"])
    df["award_floor_gt_ceiling"] = df["award_floor"] > ceiling

    # Layer 4 input (0-10): log scale so a $50M award cannot drown out a better-fitting $1M one.
    lo, hi = np.log10(cfg["financial_log_min_usd"]), np.log10(cfg["financial_log_max_usd"])
    score = (10 * (np.log10(amount) - lo) / (hi - lo)).clip(0, 10)
    # Total program funding is not what one applicant receives, so it earns less credit.
    score = score.where(df["financial_basis"] != "program_total", score.clip(upper=cfg["financial_total_only_cap"]))
    df["financial_value_imputed"] = amount.isna()
    df["financial_value_score"] = score.fillna(cfg["financial_unknown_score"]).round(2)


def add_cost_share_features(df: pd.DataFrame) -> None:
    text = df["grant_text"]
    mention = _matches(text, _COST_SHARE_WORDS)
    df["cost_share_text_mention"] = mention
    df["cost_share_percent"] = text.map(parse_cost_share_percent)

    structured = df["is_cost_sharing"]                     # True / False / <NA>
    is_true = structured.fillna(False).astype(bool)
    is_false = ~structured.fillna(True).astype(bool)
    # A blank structured field is Unknown, never False (text can upgrade it to True).
    df["requires_cost_share"] = np.select(
        [is_true, is_false, mention.to_numpy()], ["True", "False", "True"], "Unknown")
    df["cost_share_conflict"] = is_false & df["cost_share_percent"].notna()


def add_eligibility_features(df: pd.DataFrame, cfg: dict) -> None:
    """Signals only. None of these may be used to drop a grant."""
    slugs = df["applicant_types"].map(lambda s: {x.strip() for x in s.split(";") if x.strip()})
    has = lambda names: slugs.map(lambda s: bool(s & names))
    df["state_government_listed"] = has(STATE)
    df["local_government_listed"] = has(LOCAL)
    df["universities_listed"] = has(HIGHER_ED)
    df["nonprofits_listed"] = has(NONPROFIT)
    df["tribal_listed"] = has(TRIBAL)
    df["for_profit_listed"] = has(FOR_PROFIT)
    df["individuals_listed"] = has({"individuals"})
    df["unrestricted_listed"] = has({"unrestricted"})
    df["other_listed"] = has({"other"})
    df["n_applicant_types"] = slugs.map(len)
    df["applicant_types_blank"] = df["n_applicant_types"] == 0
    # Listing nearly every type (e.g. NIH research grants) says little about DHHS specifically.
    df["broad_eligibility"] = df["n_applicant_types"] >= cfg["broad_applicant_types_min"]
    df["unknown_applicant_slugs"] = slugs.map(lambda s: ";".join(sorted(s - KNOWN_SLUGS)))

    elig = df["applicant_eligibility_description"].map(strip_html)
    df["text_mentions_state_agency"] = _matches(elig, _STATE_TEXT)
    df["text_individuals_only"] = _matches(elig, _INDIV_ONLY)
    df["text_higher_ed_only"] = _matches(elig, _HIGHER_ED_ONLY)
    df["text_tribal_only"] = _matches(elig, _TRIBAL_ONLY)


def add_listing_and_quality_features(df: pd.DataFrame, cfg: dict) -> None:
    # "93.243|Name;16.590|Name" -> ["93.243", "16.590"]
    codes = df["opportunity_assistance_listings"].map(
        lambda s: [x.split("|")[0].strip() for x in s.split(";") if x.strip()])
    df["n_assistance_listings"] = codes.map(len)
    df["aln_is_hhs"] = codes.map(lambda cs: any(c.startswith("93.") for c in cs))
    agency_code = df["agency_code"] if "agency_code" in df else pd.Series("", index=df.index)
    df["federal_agency_is_hhs"] = (
        df["top_level_agency_name"].eq("Department of Health and Human Services")
        | agency_code.str.upper().str.startswith("HHS"))

    df["missing_description"] = df["summary_text"].str.len() == 0
    df["description_too_short"] = df["summary_text"].str.len() < cfg["min_description_chars"]
    df["missing_eligibility_description"] = df["applicant_eligibility_description"].map(strip_html).str.len() == 0

    # Same title + same agency under a different id: a repost or an amendment. A feature only.
    key = (df["opportunity_title"].str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
           + "|" + df["agency_name"].str.lower().str.strip())
    order = df.assign(_key=key).sort_values(["_key", "post_date", "grant_id"], kind="stable")
    first = order.groupby("_key")["grant_id"].transform("first")
    df["possible_duplicate_of"] = first.where(first != order["grant_id"], "").reindex(df.index)


def add_hard_filters(df: pd.DataFrame, cfg: dict) -> None:
    status = df["opportunity_status"].str.lower()
    bad_status = status.isin(cfg["hard_filter_statuses"])
    reason = np.select([df["expired"], bad_status],
                       ["closed_before_as_of_date", ("status_" + status).to_numpy()], "")
    df["hard_filter_reason"] = reason
    df["hard_filtered"] = df["hard_filter_reason"] != ""


# ── Build, check, report ────────────────────────────────────────────────────

FRONT_COLUMNS = ["grant_id", "opportunity_title", "track", "is_forecast", "hard_filtered", "hard_filter_reason"]


def build_features(cleaned: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Typed Layer 0 frame in, feature frame out (same rows, sorted by grant_id)."""
    df = cleaned.sort_values("grant_id", kind="stable").reset_index(drop=True)
    df["is_forecast"] = df["is_forecast"].astype(bool)
    df["track"] = np.where(df["is_forecast"], "forecast", "open")
    add_deadline_features(df, cfg)
    add_funding_features(df, cfg)
    add_cost_share_features(df)
    add_eligibility_features(df, cfg)
    add_listing_and_quality_features(df, cfg)
    add_hard_filters(df, cfg)
    df["as_of_date"] = cfg["as_of_date"]
    df["data_pulled_date"] = cfg["data_pulled_date"]
    rest = [c for c in df.columns if c not in FRONT_COLUMNS]
    return df[FRONT_COLUMNS + rest]


def check(n_cleaned: int, df: pd.DataFrame) -> None:
    """Fail loudly if Layer 1 would break the layers that read its output."""
    from semantic_triage import REQUIRED_COLUMNS  # Layer 2's contract

    assert len(df) == n_cleaned, "Layer 1 must not add or drop rows"
    assert df["grant_id"].is_unique, "grant_id must be unique"
    missing = [c for c in REQUIRED_COLUMNS if c not in df]
    assert not missing, f"missing columns Layer 2 needs: {missing}"
    assert (df["track"] == "forecast").equals(df["is_forecast"]), "track must mirror is_forecast"
    assert not (df["is_forecast"] & (df["expired"] | (df["hard_filter_reason"] == "closed_before_as_of_date"))).any(), \
        "a forecast was treated as expired"
    assert df["financial_value_score"].between(0, 10).all(), "financial_value_score must be 0-10 and never blank"
    scored = df["deadline_score"].dropna()
    assert scored.between(0, 10).all(), "deadline_score must be 0-10"
    assert df.loc[df["is_forecast"], "deadline_score"].isna().all(), "forecasts must have no deadline_score"
    assert df.loc[~df["is_forecast"] & ~df["missing_deadline"], "deadline_score"].notna().all()


def _counts(series: pd.Series) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in series.value_counts().items()) or "- none"


def report_markdown(df: pd.DataFrame, cfg: dict) -> str:
    n = lambda mask: int(mask.sum())
    op, fc = df[~df["is_forecast"]], df[df["is_forecast"]]
    kept = df[~df["hard_filtered"]]
    flags = ["deadline_under_7_days", "deadline_under_14_days", "deadline_under_30_days", "deadline_comfortable"]
    unknown = sorted({s for v in df["unknown_applicant_slugs"] for s in v.split(";") if s})
    lines = [
        "# Layer 1 report", "",
        f"Generated by `src/deterministic.py`. All date math uses the fixed as-of date "
        f"**{cfg['as_of_date']}**. The data was pulled **{cfg['data_pulled_date']}**, so anything "
        "posted or changed after that is not in it.", "",
        "## Rows", f"- total: {len(df)}", f"- open track: {len(op)}", f"- forecast track: {len(fc)}",
        f"- sent on to Layer 2 (not hard-filtered): {len(kept)}", "",
        "## Hard filters (rows stay in the file, flagged)", _counts(df["hard_filter_reason"].replace("", "kept")), "",
        "## Open grants: deadlines",
        f"- expired (closed before as-of date): {n(op['expired'])}",
        f"- no close date in the data: {n(op['missing_deadline'])} "
        f"(of which {n(op['close_date_placeholder'])} carry a placeholder year-{cfg['close_date_placeholder_year_min']}+ date)",
        *[f"- {f}: {n(op[f])}" for f in flags], "",
        "## Forecast grants (watchlist track)",
        f"- forecasted post date already passed: {n(fc['forecast_post_passed'])}",
        f"- forecasted close date already passed (stale?): {n(fc['forecast_close_passed'])}",
        f"- post date passed but close not: {n(fc['forecast_check_now'])} (may already be open, check Grants.gov now)",
        f"- no forecasted post date: {n(fc['forecast_missing_post_date'])}", "",
        "## Funding",
        _counts(df["financial_basis"]),
        f"- rows where a 0 amount was treated as a placeholder: {n(df['funding_zero_placeholder'])}",
        f"- financial_value_score imputed to {cfg['financial_unknown_score']} (no amount at all): {n(df['financial_value_imputed'])}",
        f"- award_floor above ceiling: {n(df['award_floor_gt_ceiling'])}", "",
        "## Cost sharing (structured field, text can upgrade Unknown)", _counts(df["requires_cost_share"]),
        f"- structured says False but the text states a percentage: {n(df['cost_share_conflict'])}", "",
        "## Eligibility signals (never used to filter)",
        f"- state_governments listed: {n(df['state_government_listed'])}",
        f"- broad eligibility ({cfg['broad_applicant_types_min']}+ types listed): {n(df['broad_eligibility'])}",
        f"- applicant types blank: {n(df['applicant_types_blank'])}",
        f"- eligibility text blank: {n(df['missing_eligibility_description'])}",
        f"- state grants but text says higher-ed / tribal / individuals only: "
        f"{n(df['state_government_listed'] & (df['text_higher_ed_only'] | df['text_tribal_only'] | df['text_individuals_only']))}",
        f"- applicant slugs not in our known list: {unknown or 'none'}", "",
        "## HHS signals",
        f"- assistance listing 93.x: {n(df['aln_is_hhs'])}",
        f"- federal agency is HHS: {n(df['federal_agency_is_hhs'])}", "",
        "## Data quality",
        f"- description under {cfg['min_description_chars']} characters: {n(df['description_too_short'])} "
        f"(blank: {n(df['missing_description'])})",
        f"- same title + agency under a different id: {n(df['possible_duplicate_of'] != '')}",
        f"- open grants whose archive date has passed: {n(op['archive_date_passed'])}", "",
        "## Layer 4 inputs",
        f"- financial_value_score: mean {df['financial_value_score'].mean():.2f}, "
        f"{n(df['financial_value_score'] >= 8)} grants score 8 or more",
        f"- deadline_score: present for {int(df['deadline_score'].notna().sum())} open grants, "
        f"blank for forecasts and for the {n(op['missing_deadline'])} with no real close date", "",
    ]
    return "\n".join(lines)


def main() -> None:
    cfg = settings(config.load_agency())
    cleaned = load_cleaned()
    features = build_features(cleaned, cfg)
    check(len(cleaned), features)

    config.LAYER1_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(config.LAYER1_OUTPUT, index=False)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_markdown(features, cfg), encoding="utf-8")
    print(f"Layer 1: {len(features)} rows -> {config.LAYER1_OUTPUT}")
    print(f"  open={int((~features['is_forecast']).sum())} forecast={int(features['is_forecast'].sum())} "
          f"hard_filtered={int(features['hard_filtered'].sum())} -> report: {REPORT}")


if __name__ == "__main__":
    main()
