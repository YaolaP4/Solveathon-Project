"""Unit tests for Layer 4 deterministic scoring."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config  # noqa: E402
from scoring import rank_track, score_grant  # noqa: E402


AGENCY = config.load_agency()


def base_row(**overrides):
    row = {
        "grant_id": "g1",
        "is_forecast": False,
        "strategic_alignment": 10,
        "operational_fit": 10,
        "financial_value_score": 10,
        "deadline_score": 10,
        "applicant_role_verified": "lead",
        "eligibility_quote_verified": True,
        "strategic_quote_verified": True,
    }
    row.update(overrides)
    return pd.Series(row)


def test_perfect_open_grant_scores_100():
    out = score_grant(base_row(), AGENCY)
    assert out["final_score"] == 100.0
    assert out["score_status"] == "open"


def test_forecast_omits_deadline_and_renormalizes_without_penalty():
    out = score_grant(
        base_row(is_forecast=True, deadline_score=None),
        AGENCY,
    )
    assert out["final_score"] == 100.0
    assert out["weight_used"] == 0.85
    assert out["missing_deadline_penalty"] == 0.0
    assert out["score_status"] == "forecast_watchlist"


def test_open_missing_deadline_gets_three_point_uncertainty_penalty():
    out = score_grant(base_row(deadline_score=None), AGENCY)
    assert out["final_score"] == 97.0
    assert out["weight_used"] == 0.85
    assert out["missing_deadline_penalty"] == 3.0
    assert out["score_status"] == "open_missing_deadline"


def test_confirmed_ineligible_is_hard_gated_to_zero():
    out = score_grant(
        base_row(
            applicant_role_verified="ineligible",
            eligibility_quote_verified=True,
        ),
        AGENCY,
    )
    assert out["final_score"] == 0.0
    assert out["score_status"] == "confirmed_ineligible"


def test_unverified_eligibility_becomes_uncertain_not_zero():
    out = score_grant(
        base_row(
            applicant_role_verified="ineligible",
            eligibility_quote_verified=False,
        ),
        AGENCY,
    )
    assert out["final_score"] > 0
    assert out["eligibility_confidence_score"] == 5.0


def test_unverified_strategic_evidence_gets_explicit_penalty():
    out = score_grant(
        base_row(strategic_quote_verified=False),
        AGENCY,
    )
    assert out["final_score"] == 95.0
    assert out["strategic_evidence_penalty"] == 5.0


def test_verified_partner_and_atypical_are_not_double_penalized():
    partner = score_grant(base_row(applicant_role_verified="partner"), AGENCY)
    atypical = score_grant(base_row(applicant_role_verified="atypical"), AGENCY)
    assert partner["eligibility_confidence_score"] == 10.0
    assert atypical["eligibility_confidence_score"] == 10.0


def test_rank_track_uses_stable_tie_breakers():
    df = pd.DataFrame([
        {"grant_id": "b", "final_score": 90, "strategic_alignment": 8, "operational_fit": 9},
        {"grant_id": "a", "final_score": 90, "strategic_alignment": 9, "operational_fit": 8},
    ])
    ranked = rank_track(df)
    assert ranked.iloc[0]["grant_id"] == "a"
    assert list(ranked["rank"]) == [1, 2]
