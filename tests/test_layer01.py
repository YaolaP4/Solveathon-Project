"""Tests for Layers 0-1 (clean_data.py, deterministic.py).

Unit tests build tiny grants by hand; the last group runs the real pipeline on
data/raw/grants.csv and checks the contract that Layers 2 and 4 depend on.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config  # noqa: E402
import clean_data  # noqa: E402
import deterministic as d  # noqa: E402

CFG = d.settings({"as_of_date": "2026-09-30"})

RAW_COLUMNS = list(pd.read_csv(config.RAW_GRANTS, nrows=0).columns)


def make(**rows_overrides) -> pd.DataFrame:
    """One-row raw frame (all strings, like the CSV) with sensible defaults."""
    row = {c: "" for c in RAW_COLUMNS}
    row.update({
        "opportunity_id": "g1", "opportunity_title": "A grant", "opportunity_status": "posted",
        "agency_name": "Some Agency", "top_level_agency_name": "Some Dept", "agency_code": "X-Y",
        "post_date": "2026-06-01", "close_date": "2026-12-01", "is_forecast": "False",
        "is_cost_sharing": "False", "applicant_types": "state_governments;county_governments",
        "summary_description": "<p>" + "Funds things. " * 20 + "</p>",
        "applicant_eligibility_description": "State agencies may apply.",
        "opportunity_assistance_listings": "93.243|Substance Abuse",
        "award_ceiling": "500000",
    })
    row.update(rows_overrides)
    return pd.DataFrame([row])


def features(*rows: dict) -> pd.DataFrame:
    raw = pd.concat([make(**r) for r in rows], ignore_index=True)
    cleaned, _ = clean_data.clean(raw)
    return d.build_features(cleaned, CFG).set_index("grant_id")


# ── Layer 0 ─────────────────────────────────────────────────────────────────

def test_clean_keeps_text_raw_and_adds_plain_text():
    raw = make(summary_description="<p>Hello &amp; welcome</p> ", opportunity_title="Title  ")
    df, _ = clean_data.clean(raw)
    assert df.loc[0, "summary_description"] == "<p>Hello &amp; welcome</p> "  # untouched
    assert df.loc[0, "opportunity_title"] == "Title  "
    assert df.loc[0, "summary_text"] == "Hello & welcome"


def test_clean_drops_duplicate_ids_and_keeps_blank_cost_share_unknown():
    raw = pd.concat([make(opportunity_id="a", is_cost_sharing=""), make(opportunity_id="a")], ignore_index=True)
    df, report = clean_data.clean(raw)
    assert len(df) == 1 and report["duplicate_ids_dropped"] == 1
    assert pd.isna(df.loc[0, "is_cost_sharing"])


def test_clean_reports_unparseable_values():
    _, report = clean_data.clean(make(close_date="soon", award_ceiling="lots"))
    assert report["unparseable"] == {"close_date": 1, "award_ceiling": 1}


# ── Deadlines and tracks ────────────────────────────────────────────────────

def test_expired_boundary_and_hard_filter():
    f = features(
        {"opportunity_id": "past", "close_date": "2026-09-29"},
        {"opportunity_id": "today", "close_date": "2026-09-30"},
        {"opportunity_id": "later", "close_date": "2026-10-30"},
    )
    assert bool(f.loc["past", "expired"]) and bool(f.loc["past", "hard_filtered"])
    assert f.loc["past", "hard_filter_reason"] == "closed_before_as_of_date"
    assert not f.loc["today", "expired"] and not f.loc["today", "hard_filtered"]   # closing on as_of is open
    assert f.loc["today", "days_until_close"] == 0 and f.loc["later", "days_until_close"] == 30
    assert bool(f.loc["later", "deadline_under_30_days"]) and not f.loc["later", "deadline_comfortable"]


def test_forecast_is_never_expired_or_scored_for_deadline():
    f = features({"opportunity_id": "fc", "is_forecast": "True", "opportunity_status": "forecasted",
                  "close_date": "", "forecasted_post_date": "2026-09-01", "forecasted_close_date": ""})
    row = f.loc["fc"]
    assert row["track"] == "forecast" and not row["expired"] and not row["hard_filtered"]
    assert pd.isna(row["deadline_score"]) and pd.isna(row["days_until_close"])
    assert row["forecast_post_passed"] and row["forecast_check_now"]


def test_stale_forecast_is_flagged_not_filtered():
    f = features({"opportunity_id": "old", "is_forecast": "True", "opportunity_status": "forecasted",
                  "forecasted_post_date": "2025-01-01", "forecasted_close_date": "2025-06-01"})
    assert f.loc["old", "forecast_close_passed"] and not f.loc["old", "forecast_check_now"]
    assert not f.loc["old", "hard_filtered"]


def test_placeholder_and_missing_close_dates_are_missing_deadlines():
    f = features({"opportunity_id": "ph", "close_date": "2099-01-01"},
                 {"opportunity_id": "none", "close_date": ""})
    for gid in ("ph", "none"):
        assert f.loc[gid, "missing_deadline"] and pd.isna(f.loc[gid, "deadline_score"])
        assert not f.loc[gid, "hard_filtered"]
    assert f.loc["ph", "close_date_placeholder"] and not f.loc["none", "close_date_placeholder"]


def test_deadline_score_rises_with_time_and_stays_in_range():
    days = [0, 3, 7, 14, 30, 45, 60, 400]
    rows = [{"opportunity_id": f"d{n}", "close_date": str((pd.Timestamp("2026-09-30") + pd.Timedelta(days=n)).date())}
            for n in days]
    f = features(*rows)
    scores = [f.loc[f"d{n}", "deadline_score"] for n in days]
    assert scores == sorted(scores) and scores[0] == 0 and scores[-1] == 10
    assert scores[days.index(7)] == 2 and scores[days.index(30)] == 7


def test_closed_status_is_hard_filtered_but_unknown_status_is_kept():
    f = features({"opportunity_id": "c", "opportunity_status": "cancelled"},
                 {"opportunity_id": "u", "opportunity_status": "something_new"})
    assert f.loc["c", "hard_filter_reason"] == "status_cancelled"
    assert not f.loc["u", "hard_filtered"]


# ── Funding ─────────────────────────────────────────────────────────────────

def test_financial_score_uses_log_scale_and_ceiling_first():
    f = features({"opportunity_id": "small", "award_ceiling": "100000"},
                 {"opportunity_id": "mid", "award_ceiling": "1000000"},
                 {"opportunity_id": "big", "award_ceiling": "500000000"})
    assert f.loc["small", "financial_value_score"] == 0
    assert f.loc["mid", "financial_value_score"] == 5
    assert f.loc["big", "financial_value_score"] == 10            # capped: huge awards don't run away
    assert (f["financial_basis"] == "award_ceiling").all()


def test_zero_amounts_are_placeholders_and_unknown_amount_is_imputed():
    f = features({"opportunity_id": "z", "award_ceiling": "0"},
                 {"opportunity_id": "avg", "award_ceiling": "", "estimated_total_program_funding": "10000000",
                  "expected_number_of_awards": "10"},
                 {"opportunity_id": "tot", "award_ceiling": "", "estimated_total_program_funding": "90000000"})
    assert f.loc["z", "funding_zero_placeholder"] and f.loc["z", "financial_basis"] == "unknown"
    assert f.loc["z", "financial_value_score"] == 5 and f.loc["z", "financial_value_imputed"]
    assert f.loc["avg", "financial_basis"] == "average_award" and f.loc["avg", "award_value_usd"] == 1_000_000
    assert f.loc["tot", "financial_basis"] == "program_total" and f.loc["tot", "financial_value_score"] == 7  # capped


# ── Cost sharing ────────────────────────────────────────────────────────────

def test_cost_share_blank_is_unknown_and_text_can_upgrade_it():
    f = features({"opportunity_id": "blank", "is_cost_sharing": ""},
                 {"opportunity_id": "text", "is_cost_sharing": "",
                  "applicant_eligibility_description": "Applicants must provide a 20% cost share."},
                 {"opportunity_id": "yes", "is_cost_sharing": "True"},
                 {"opportunity_id": "conf", "is_cost_sharing": "False",
                  "applicant_eligibility_description": "A 25% match is required."})
    assert f.loc["blank", "requires_cost_share"] == "Unknown"
    assert f.loc["text", "requires_cost_share"] == "True" and f.loc["text", "cost_share_percent"] == 20
    assert f.loc["yes", "requires_cost_share"] == "True"
    assert f.loc["conf", "requires_cost_share"] == "False" and f.loc["conf", "cost_share_conflict"]


# ── Eligibility and HHS signals ─────────────────────────────────────────────

def test_applicant_slugs_become_signals_not_filters():
    f = features({"opportunity_id": "s", "applicant_types": "state_governments;nonprofits_non_higher_education_with_501c3"},
                 {"opportunity_id": "n", "applicant_types": "small_businesses;individuals"},
                 {"opportunity_id": "all", "applicant_types": ";".join(sorted(d.KNOWN_SLUGS))})
    assert f.loc["s", "state_government_listed"] and f.loc["s", "nonprofits_listed"]
    assert not f.loc["n", "state_government_listed"] and not f.loc["n", "hard_filtered"]
    assert f.loc["all", "broad_eligibility"] and not f.loc["s", "broad_eligibility"]
    assert f.loc["all", "unknown_applicant_slugs"] == ""


def test_unknown_applicant_slug_is_reported():
    f = features({"opportunity_id": "x", "applicant_types": "state_governments;martians"})
    assert f.loc["x", "unknown_applicant_slugs"] == "martians"


def test_assistance_listing_and_agency_hhs_flags():
    f = features({"opportunity_id": "h", "opportunity_assistance_listings": "16.590|DOJ;93.243|SAMHSA",
                  "top_level_agency_name": "Department of Health and Human Services"},
                 {"opportunity_id": "o", "opportunity_assistance_listings": "16.590|DOJ thing 93.5",
                  "top_level_agency_name": "Department of Justice"})
    assert f.loc["h", "aln_is_hhs"] and f.loc["h", "federal_agency_is_hhs"] and f.loc["h", "n_assistance_listings"] == 2
    assert not f.loc["o", "aln_is_hhs"] and not f.loc["o", "federal_agency_is_hhs"]


def test_data_quality_flags_and_possible_duplicates():
    f = features({"opportunity_id": "a", "opportunity_title": "Same Title", "agency_name": "Agency",
                  "post_date": "2026-01-01", "summary_description": "short"},
                 {"opportunity_id": "b", "opportunity_title": "same  title", "agency_name": "agency",
                  "post_date": "2026-02-01", "applicant_eligibility_description": ""})
    assert f.loc["a", "description_too_short"] and not f.loc["a", "missing_description"]
    assert f.loc["b", "missing_eligibility_description"]
    assert f.loc["a", "possible_duplicate_of"] == "" and f.loc["b", "possible_duplicate_of"] == "a"
    assert not f["hard_filtered"].any()                        # duplicates are a feature, not a filter


# ── Real data: the contract Layers 2 and 4 rely on ──────────────────────────

@pytest.fixture(scope="module")
def real():
    raw = pd.read_csv(config.RAW_GRANTS, dtype=str, keep_default_na=False)
    cleaned, _ = clean_data.clean(raw)
    feats = d.build_features(cleaned, d.settings(config.load_agency()))
    d.check(len(cleaned), feats)
    return raw, feats


def test_real_row_counts_and_tracks(real):
    raw, f = real
    assert len(f) == len(raw) == 1662 and f["grant_id"].is_unique
    assert f["track"].value_counts().to_dict() == {"open": 1103, "forecast": 559}


def test_real_hard_filters_are_only_expired_or_archived_open_grants(real):
    _, f = real
    assert set(f["hard_filter_reason"].unique()) <= {"", "closed_before_as_of_date", "archived_before_as_of_date"}
    archived = f["hard_filter_reason"] == "archived_before_as_of_date"
    assert f["hard_filtered"].sum() == f["expired"].sum() + archived.sum() == 342
    # Archived grants are posted grants with no real close date whose archive date has passed.
    assert archived.sum() == 12 and f.loc[archived, "missing_deadline"].all()
    assert not f.loc[f["is_forecast"], "hard_filtered"].any()


def test_real_sentinel_amounts_are_not_money(real):
    _, f = real
    assert f["funding_sentinel_placeholder"].sum() >= 2
    assert not f[["award_ceiling", "estimated_total_program_funding"]].isin(d.PLACEHOLDER_AMOUNTS).any().any()
    assert f["award_value_usd"].max() < 999_999_999


def test_real_layer4_inputs_are_present_and_in_range(real):
    _, f = real
    assert f["financial_value_score"].notna().all() and f["financial_value_score"].between(0, 10).all()
    assert f.loc[~f["is_forecast"] & ~f["missing_deadline"], "deadline_score"].between(0, 10).all()
    assert f.loc[f["is_forecast"], "deadline_score"].isna().all()


def test_real_prompt_text_matches_raw_export(real):
    raw, f = real
    f = f.set_index("grant_id")
    raw = raw.set_index("opportunity_id")
    for col in ["opportunity_title", "summary_description", "applicant_eligibility_description",
                "applicant_types", "opportunity_assistance_listings", "funding_instruments", "agency_name"]:
        assert (f[col].reindex(raw.index) == raw[col]).all(), col


def test_real_output_is_deterministic(real):
    raw, f = real
    cleaned, _ = clean_data.clean(raw)
    again = d.build_features(cleaned, d.settings(config.load_agency()))
    pd.testing.assert_frame_equal(f, again)


def test_written_file_feeds_layer4_loader(real, tmp_path):
    """The CSV Layer 1 writes must satisfy scoring.load_inputs' column check."""
    _, f = real
    path = tmp_path / "f.csv"
    f.to_csv(path, index=False)
    back = pd.read_csv(path)
    for col in ["grant_id", "is_forecast", "financial_value_score", "deadline_score"]:
        assert col in back.columns
    assert back["hard_filtered"].dtype == bool and back["is_forecast"].dtype == bool
