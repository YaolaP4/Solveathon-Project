"""Unit tests for Layers 2-3 logic that does not need an API: routing,
quote verification, output validation, cross-layer comparison, caching."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config  # noqa: E402
from deep_analysis import compare_layers, parse_json, validate, verify  # noqa: E402
from llm_cache import ResponseCache, request_hash  # noqa: E402
from semantic_triage import load_prompt, route, summarize  # noqa: E402
from text_utils import quote_in_source, strip_html  # noqa: E402

AGENCY = config.load_agency()
TH = AGENCY["layer2_routing"]


def jev(rel: dict, role: dict | None = None) -> dict:
    a = {"domain_relevance": {"choice": max(rel, key=rel.get), "probabilities": rel}}
    if role:
        a["applicant_role"] = {"choice": max(role, key=role.get), "probabilities": role}
    return a


# ── Layer 2 routing ─────────────────────────────────────────────────────────

def test_confident_irrelevant_is_deprioritized():
    assert route(jev({"none": 0.9, "weak": 0.05, "moderate": 0.03, "strong": 0.02}), TH)[0] == "deprioritized"


def test_uncertain_goes_to_deep_review():
    # Argmax is "none" but Jev is not confident: recall over precision.
    assert route(jev({"none": 0.6, "weak": 0.2, "moderate": 0.1, "strong": 0.1}), TH)[0] == "deep_review"


def test_confidently_ineligible_is_deprioritized():
    r = route(jev({"none": 0.1, "weak": 0.1, "moderate": 0.3, "strong": 0.5},
                  {"lead": 0.02, "partner": 0.03, "atypical": 0.02, "ineligible": 0.92, "unclear": 0.01}), TH)
    assert r[0] == "deprioritized" and "ineligible" in r[1]


def test_missing_answer_is_never_dropped():
    assert route({}, TH)[0] == "deep_review"


def test_summary_priority_rewards_relevance_and_role():
    strong_lead = summarize(jev({"none": 0, "weak": 0, "moderate": 0, "strong": 1.0},
                                {"lead": 1.0, "partner": 0, "atypical": 0, "ineligible": 0, "unclear": 0}))
    strong_atyp = summarize(jev({"none": 0, "weak": 0, "moderate": 0, "strong": 1.0},
                                {"lead": 0, "partner": 0, "atypical": 1.0, "ineligible": 0, "unclear": 0}))
    assert strong_lead["triage_priority"] == 1.0
    assert strong_atyp["triage_priority"] == 0.5


def test_prompt_fills_goals_and_divisions_from_config():
    _, questions, version = load_prompt(AGENCY)
    assert set(questions["matched_goal"]["criteria"]) == {"G1", "G2", "G3", "G4", "G5", "none"}
    assert "DPH" in questions["owning_division"]["criteria"]
    assert len(version) == 12


# ── Quote verification ──────────────────────────────────────────────────────

SOURCE = "<p>Eligible applicants are limited to: State governments, Indian Tribal governments,&nbsp;and units of local government.</p>"


def test_quote_found_despite_html_case_and_whitespace():
    assert quote_in_source("eligible applicants are limited to:  State   governments", SOURCE)


def test_quote_with_ellipsis_fragments_in_order():
    assert quote_in_source("Eligible applicants are limited to ... units of local government", SOURCE)
    assert not quote_in_source("units of local government ... Eligible applicants", SOURCE)


def test_fabricated_or_trivial_quote_rejected():
    assert not quote_in_source("State health departments are the only eligible applicants", SOURCE)
    assert not quote_in_source("State", SOURCE)
    assert not quote_in_source("", SOURCE)
    assert not quote_in_source(None, SOURCE)


def test_strip_html():
    assert strip_html("a<br/>b &amp; c") == "a\nb & c"


# ── Layer 3 validation and verification ─────────────────────────────────────

GOOD = {
    "strategic_alignment": 8, "matched_goal": "G3", "matched_objective": "G3.O4",
    "strategic_reason": "Funds opioid treatment.", "strategic_evidence_quote": "x",
    "applicant_role": "lead", "eligibility_evidence_quote": "x", "owning_division": "DMHDDSUS",
    "operational_fit": 7, "operational_reason": "r", "restrictions": [], "major_risk": "short deadline",
    "recommended_for_review": True, "one_line_rationale": "Fits G3.",
}


def test_valid_output_has_no_problems():
    assert validate(GOOD, AGENCY) == []


@pytest.mark.parametrize("field,value", [
    ("strategic_alignment", 11), ("strategic_alignment", "8"), ("matched_goal", "G9"),
    ("matched_objective", "G1.O1"),  # objective from a different goal
    ("applicant_role", "maybe"), ("owning_division", "NASA"), ("recommended_for_review", "yes"),
])
def test_invalid_fields_are_caught(field, value):
    assert validate({**GOOD, field: value}, AGENCY)


def test_parse_json_handles_fences():
    assert parse_json('Here:\n```json\n{"a": 1}\n```')["a"] == 1


TEXTS = {"title": "State Opioid Response", "summary": "This program funds medication treatment for opioid use disorder.",
         "eligibility": "Eligible applicants are single state agencies.", "applicant_types": "state_governments"}


def test_verified_quotes_keep_role():
    out = {**GOOD, "strategic_evidence_quote": "funds medication treatment for opioid use disorder",
           "eligibility_evidence_quote": "Eligible applicants are single state agencies"}
    checks, errors = verify(out, TEXTS)
    assert checks["applicant_role_verified"] == "lead" and errors == []


def test_hallucinated_eligibility_quote_downgrades_role():
    out = {**GOOD, "strategic_evidence_quote": "funds medication treatment for opioid use disorder",
           "eligibility_evidence_quote": "State health departments are explicitly eligible"}
    checks, errors = verify(out, TEXTS)
    assert checks["applicant_role_verified"] == "unclear"
    assert errors[0]["check"] == "unverified_eligibility_quote"


def test_layer_disagreement_flags_possible_false_negative():
    l2 = pd.Series({"domain_relevance": "weak", "domain_relevance_p": 0.7,
                    "applicant_role": "atypical", "owning_division": "DPH"})
    checks = {e["check"] for e in compare_layers(l2, GOOD)}
    assert checks == {"layer2_vs_layer3_relevance", "layer2_vs_layer3_role", "layer2_vs_layer3_division"}


# ── Cache ───────────────────────────────────────────────────────────────────

def test_cache_roundtrip_and_prompt_change_misses(tmp_path):
    c = ResponseCache(tmp_path, "t")
    k1 = request_hash("m", "v1", {"q": 1})
    c.put("g1", k1, "m", "v1", {"answer": 42})
    assert c.get("g1", k1) == {"answer": 42}
    assert c.get("g1", request_hash("m", "v2", {"q": 1})) is None


def test_every_jev_question_declares_a_type_the_api_accepts():
    # The gateway rejects questions without type in {boolean, choice, score} (HTTP 400);
    # routing relies on per-option probabilities, so every question must be `choice`.
    _, questions, _ = load_prompt(AGENCY)
    assert {q["type"] for q in questions.values()} == {"choice"}
