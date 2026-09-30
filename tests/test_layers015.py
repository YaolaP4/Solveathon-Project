"""Unit tests for Layer 0 (cleaning), Layer 1 (deterministic features) and
Layer 5 (baseline, sampling, metrics)."""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config  # noqa: E402
from clean_data import PLACEHOLDER_AMOUNTS, clean, clean_amount  # noqa: E402
from deterministic import award_estimate, build, deadline_score, financial_value_score  # noqa: E402
from keyword_baseline import score as baseline_score  # noqa: E402
from validation import cohen_kappa, draw_sample, resolve_labels, weighted_rates  # noqa: E402

AGENCY = config.load_agency()
DL = AGENCY["layer1"]["deadline_score"]
FIN = AGENCY["layer1"]["financial_value_score"]


def raw_row(**kw):
    row = {"opportunity_id": "id1", "opportunity_title": "Title", "opportunity_status": "posted",
           "summary_description": "<p>Funds state &amp; local health departments.</p>",
           "applicant_eligibility_description": "State governments", "applicant_types": "state_governments;Other",
           "close_date": "2026-12-31", "archive_date": "", "forecasted_close_date": "", "close_date_description": "",
           "award_floor": "0", "award_ceiling": "500000", "estimated_total_program_funding": "",
           "expected_number_of_awards": "", "is_cost_sharing": "False", "is_forecast": "False",
           "agency_code": "HHS-CDC", "funding_category_description": "", "agency_contact_description": ""}
    for c in ["post_date", "forecasted_post_date", "forecasted_award_date", "forecasted_project_start_date"]:
        row[c] = ""
    row.update(kw)
    return row


def features(*rows):
    cleaned, _ = clean(pd.DataFrame(list(rows)))
    return build(cleaned, AGENCY).set_index("grant_id")


# ── Layer 0 ─────────────────────────────────────────────────────────────────

def test_placeholder_and_zero_amounts_become_missing():
    s, n = clean_amount(pd.Series(["999999999", "2147483647", "0", "250000"]), PLACEHOLDER_AMOUNTS)
    assert s.isna().tolist() == [True, True, True, False] and n == 3


def test_clean_strips_html_and_normalizes_types():
    df, q = clean(pd.DataFrame([raw_row()]))
    assert df.loc[0, "summary_description"] == "Funds state & local health departments."
    assert df.loc[0, "applicant_types"] == "other;state_governments"
    assert q["summaries_with_html"] == 1


# ── Layer 1 ─────────────────────────────────────────────────────────────────

def test_deadline_score_is_linear_between_thresholds():
    assert deadline_score(7, False, DL) == 0
    assert deadline_score(60, False, DL) == 10
    assert deadline_score(33.5, False, DL) == 5
    assert deadline_score(None, True, DL) == DL["rolling_deadline_score"]
    assert math.isnan(deadline_score(float("nan"), False, DL))


def test_financial_score_log_scale_missing_and_cost_share():
    assert financial_value_score(50_000, False, FIN) == 0
    assert financial_value_score(5_000_000, False, FIN) == 10
    assert financial_value_score(500_000, False, FIN) == 5
    assert financial_value_score(float("nan"), False, FIN) == FIN["missing_award_score"]
    assert financial_value_score(5_000_000, True, FIN) == 10 - FIN["cost_share_penalty_points"]


def test_award_estimate_prefers_ceiling_then_total_per_award():
    base = {"award_ceiling": np.nan, "estimated_total_program_funding": 1_000_000,
            "expected_number_of_awards": 4, "award_floor": 10}
    assert award_estimate(pd.Series({**base, "award_ceiling": 300})) == (300, "award_ceiling")
    assert award_estimate(pd.Series(base)) == (250_000, "total_funding / expected_awards")


def test_hard_filters_are_conservative():
    f = features(
        raw_row(opportunity_id="expired", close_date="2026-09-01"),
        raw_row(opportunity_id="archived", close_date="", archive_date="2026-01-01"),
        raw_row(opportunity_id="open", close_date="2026-12-31"),
        raw_row(opportunity_id="stale_fc", is_forecast="True", opportunity_status="forecasted",
                close_date="", forecasted_close_date="2026-01-01"),
        raw_row(opportunity_id="no_state", applicant_types="nonprofits_non_higher_education_with_501c3"),
    )
    assert f.loc["expired", "hard_filtered"] and f.loc["archived", "hard_filtered"]
    assert not f.loc["open", "hard_filtered"] and f.loc["open", "deadline_flag"] == "deadline_comfortable"
    # Stale forecasts and grants without 'state' in the structured list are kept (recall over precision).
    assert not f.loc["stale_fc", "hard_filtered"] and f.loc["stale_fc", "stale_forecast"]
    assert math.isnan(f.loc["stale_fc", "deadline_score"])
    assert not f.loc["no_state", "hard_filtered"] and not f.loc["no_state", "state_government_listed"]


def test_rolling_deadline_detected():
    f = features(raw_row(close_date="", close_date_description="Proposals accepted anytime"))
    assert f.iloc[0]["rolling_deadline"] and f.iloc[0]["deadline_score"] == DL["rolling_deadline_score"]


# ── Layer 5 ─────────────────────────────────────────────────────────────────

def test_baseline_ranks_health_grant_above_unrelated():
    g = pd.DataFrame({"grant_id": ["a", "b"], "opportunity_title": ["x", "y"], "hard_filtered": [False, False],
                      "grant_text": ["Opioid substance use treatment and harm reduction for state behavioral health",
                                     "Hypersonic propulsion materials research for the Air Force"]})
    out = baseline_score(g, AGENCY).set_index("grant_id")
    assert out.loc["a", "baseline_score"] > out.loc["b", "baseline_score"]


def test_sample_is_stratified_blind_and_deterministic():
    n = 600
    feats = pd.DataFrame({"grant_id": [f"g{i}" for i in range(n)], "hard_filtered": False})
    base = pd.DataFrame({"grant_id": feats["grant_id"], "baseline_rank": range(1, n + 1)})
    s1, d1 = draw_sample(feats, base)
    s2, _ = draw_sample(feats, base)
    assert s1["grant_id"].tolist() == s2["grant_id"].tolist()
    assert d1.set_index("stratum")["population_size"].to_dict() == {
        "S1_top100": 100, "S2_rank101_400": 300, "S3_rank401_plus": 200}


def test_label_resolution_needs_agreement_or_adjudication():
    labels = pd.DataFrame({"sample_id": ["1", "2", "3"], "labeler_A_relevant": ["Y", "Y", "N"],
                           "labeler_B_relevant": ["y", "N", "Y"], "final_relevant": ["", "", "N"]})
    out, unresolved = resolve_labels(labels)
    assert out["relevant"].tolist()[0] == 1 and np.isnan(out["relevant"].tolist()[1])
    assert out["relevant"].tolist()[2] == 0 and unresolved == ["2"]


def test_weighted_recall_uses_stratum_sizes():
    # Stratum A (pop 10): 1 labeled, relevant, retained. Stratum B (pop 90): 1 labeled, relevant, missed.
    df = pd.DataFrame({"stratum": ["A", "B"], "population_size": [10, 90], "relevant": [1.0, 1.0],
                       "ret": [True, False]})
    assert weighted_rates(df, "ret")["recall"] == 0.1


def test_kappa():
    a = pd.Series([1.0, 0.0, 1.0, 0.0])
    assert cohen_kappa(a, a) == 1.0
