"""Unit tests for Layer 5 (keyword baseline, sampling, label resolution, metrics).
Layers 0-1 are covered by tests/test_layer01.py."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import config  # noqa: E402
from keyword_baseline import score as baseline_score  # noqa: E402
from validation import cohen_kappa, draw_sample, resolve_labels, weighted_rates  # noqa: E402

AGENCY = config.load_agency()


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
