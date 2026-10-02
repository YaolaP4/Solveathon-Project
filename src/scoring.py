"""Layer 4 - transparent, deterministic scoring for NCDHHS grants.

Layer 3 supplies the semantic judgments that require reading:
  * strategic_alignment (0-10)
  * operational_fit (0-10)
  * verified applicant-role / evidence fields

Layer 1 supplies objective scores:
  * financial_value_score (0-10)
  * deadline_score (0-10, nullable when the deadline is genuinely unknown)

Python combines those signals into the final ranking. No model ranks grants.

Outputs:
    data/results/ranked_grants.csv   open opportunities
    data/results/watchlist.csv       forecast opportunities
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import config


DEFAULT_WEIGHTS = {
    "strategic_alignment": 0.30,
    "operational_fit": 0.25,
    "financial_value_score": 0.15,
    "deadline_score": 0.15,
    "eligibility_confidence_score": 0.15,
}

DEFAULT_ROLE_SCORES = {
    # Eligibility confidence answers "can NCDHHS participate?", not
    # "is NCDHHS the most typical lead applicant?". Operational fit captures
    # the latter concern, so all verified eligible roles receive full credit.
    "lead": 10.0,
    "partner": 10.0,
    "atypical": 10.0,
    "unclear": 5.0,
    "ineligible": 0.0,
}

DEFAULT_MISSING_DEADLINE_PENALTY = 3.0
# A rolling ("accepted anytime") grant has a known, flexible deadline rather than an
# unknown one: a smaller penalty, so a similar grant with a real deadline comes first.
# If the money can run out (first come, first served) there is no flexibility, so no penalty.
DEFAULT_ROLLING_DEADLINE_PENALTY = 2.0
DEFAULT_ROLLING_FUNDS_LIMITED_PENALTY = 0.0
DEFAULT_UNVERIFIED_STRATEGIC_PENALTY = 5.0


def missing_deadline_penalties(agency: dict) -> dict[str, float]:
    """Penalty points for an open grant with no deadline score, by kind of missing deadline."""
    cfg = agency.get("layer4_scoring", {})
    out = {
        "unknown": float(cfg.get("missing_open_deadline_penalty_points", DEFAULT_MISSING_DEADLINE_PENALTY)),
        "rolling": float(cfg.get("rolling_deadline_penalty_points", DEFAULT_ROLLING_DEADLINE_PENALTY)),
        "rolling_funds_limited": float(cfg.get("rolling_funds_limited_penalty_points",
                                               DEFAULT_ROLLING_FUNDS_LIMITED_PENALTY)),
    }
    if any(v < 0 for v in out.values()):
        raise ValueError("Layer 4 penalties cannot be negative")
    return out


def scoring_config(agency: dict) -> tuple[dict[str, float], dict[str, float], float, float]:
    """Load and validate Layer 4 settings from priorities.json."""
    cfg = agency.get("layer4_scoring", {})
    weights = {**DEFAULT_WEIGHTS, **cfg.get("weights", {})}
    role_scores = {**DEFAULT_ROLE_SCORES, **cfg.get("eligibility_confidence_by_verified_role", {})}
    deadline_penalty = float(
        cfg.get("missing_open_deadline_penalty_points", DEFAULT_MISSING_DEADLINE_PENALTY)
    )
    evidence_penalty = float(
        cfg.get("unverified_strategic_evidence_penalty_points", DEFAULT_UNVERIFIED_STRATEGIC_PENALTY)
    )

    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError(f"Layer 4 weights must sum to 1.0; got {sum(weights.values()):.6f}")
    if any(w < 0 for w in weights.values()):
        raise ValueError("Layer 4 weights cannot be negative")
    if any(not 0 <= v <= 10 for v in role_scores.values()):
        raise ValueError("Eligibility-confidence role scores must be between 0 and 10")
    if deadline_penalty < 0 or evidence_penalty < 0:
        raise ValueError("Layer 4 penalties cannot be negative")

    return weights, role_scores, deadline_penalty, evidence_penalty


def _number(row: pd.Series, key: str) -> float | None:
    value = row.get(key)
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool(value) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def verified_role(row: pd.Series) -> str:
    """Use Layer 3's evidence-checked role; fall back to unclear."""
    role = row.get("applicant_role_verified")
    if isinstance(role, str) and role:
        return role
    return "unclear"


def confirmed_ineligible(row: pd.Series) -> bool:
    """Hard-gate only evidence-verified ineligibility.

    A model saying "ineligible" without a verified eligibility quote is not
    enough to remove a grant from consideration.
    """
    return (
        verified_role(row) == "ineligible"
        and _bool(row.get("eligibility_quote_verified")) is True
    )


def eligibility_confidence(row: pd.Series, role_scores: dict[str, float]) -> float:
    """Convert verified eligibility evidence to the 0-10 scoring component."""
    role = verified_role(row)

    # If eligibility evidence was not verified, treat the result as uncertain
    # rather than trusting a confident-sounding model label.
    if _bool(row.get("eligibility_quote_verified")) is not True:
        return role_scores.get("unclear", 5.0)

    return float(role_scores.get(role, role_scores.get("unclear", 5.0)))


def _check_0_10(name: str, value: float | None) -> None:
    if value is None:
        raise ValueError(f"{name} is required for Layer 4 scoring")
    if not 0 <= value <= 10:
        raise ValueError(f"{name} must be between 0 and 10; got {value}")


def score_grant(
    row: pd.Series,
    agency: dict | None = None,
) -> dict:
    """Score one grant and return an auditable scoring breakdown.

    Final scores are on a 0-100 scale. For forecasts, deadline is intentionally
    excluded and the remaining weights are re-normalized. For an open grant
    whose deadline is missing from the dataset, deadline is also excluded, but
    a small uncertainty penalty is applied.
    """
    agency = agency or config.load_agency()
    weights, role_scores, missing_deadline_penalty, evidence_penalty = scoring_config(agency)

    is_forecast = _bool(row.get("is_forecast"))
    if is_forecast is None:
        is_forecast = str(row.get("track", "")).strip().lower() == "forecast"
    track = "forecast" if is_forecast else "open"

    strategic = _number(row, "strategic_alignment")
    operational = _number(row, "operational_fit")
    financial = _number(row, "financial_value_score")
    deadline = _number(row, "deadline_score")

    _check_0_10("strategic_alignment", strategic)
    _check_0_10("operational_fit", operational)
    _check_0_10("financial_value_score", financial)
    if deadline is not None:
        _check_0_10("deadline_score", deadline)

    elig = eligibility_confidence(row, role_scores)

    if confirmed_ineligible(row):
        return {
            "track": track,
            "eligibility_confidence_score": 0.0,
            "deadline_weight_used": 0.0 if is_forecast else weights["deadline_score"],
            "weight_used": 1.0 - weights["deadline_score"] if is_forecast else 1.0,
            "missing_deadline_penalty": 0.0,
            "strategic_evidence_penalty": 0.0,
            "final_score": 0.0,
            "score_status": "confirmed_ineligible",
        }

    components = {
        "strategic_alignment": strategic,
        "operational_fit": operational,
        "financial_value_score": financial,
        "eligibility_confidence_score": elig,
    }

    weighted_sum = sum(components[k] * weights[k] for k in components)
    weight_used = sum(weights[k] for k in components)
    deadline_weight_used = 0.0
    missing_deadline = deadline is None

    if not is_forecast and deadline is not None:
        weighted_sum += deadline * weights["deadline_score"]
        weight_used += weights["deadline_score"]
        deadline_weight_used = weights["deadline_score"]

    # Forecasts intentionally omit deadline. Open grants with a genuinely
    # missing deadline are re-normalized over the four known criteria.
    base_10 = weighted_sum / weight_used
    final_100 = base_10 * 10.0

    applied_deadline_penalty = 0.0
    deadline_kind = None
    if not is_forecast and missing_deadline:
        if _bool(row.get("rolling_funds_limited")) is True:
            deadline_kind = "rolling_funds_limited"
        elif _bool(row.get("rolling_deadline")) is True:
            deadline_kind = "rolling"
        else:
            deadline_kind = "unknown"
        applied_deadline_penalty = missing_deadline_penalties(agency)[deadline_kind]
        final_100 -= applied_deadline_penalty

    # Existing Layer 3 design requires unsupported strategic evidence to hurt
    # the ranking rather than silently trusting the model's 0-10 judgment.
    applied_evidence_penalty = 0.0
    if _bool(row.get("strategic_quote_verified")) is False:
        applied_evidence_penalty = evidence_penalty
        final_100 -= applied_evidence_penalty

    final_100 = round(max(0.0, min(100.0, final_100)), 2)

    if is_forecast:
        status = "forecast_watchlist"
    elif deadline_kind == "rolling_funds_limited":
        status = "open_rolling_funds_limited"
    elif deadline_kind == "rolling":
        status = "open_rolling"
    elif missing_deadline:
        status = "open_missing_deadline"
    else:
        status = "open"

    return {
        "track": track,
        "eligibility_confidence_score": round(elig, 2),
        "deadline_weight_used": round(deadline_weight_used, 4),
        "weight_used": round(weight_used, 4),
        "missing_deadline_penalty": round(applied_deadline_penalty, 2),
        "strategic_evidence_penalty": round(applied_evidence_penalty, 2),
        "final_score": final_100,
        "score_status": status,
    }


def score_dataframe(df: pd.DataFrame, agency: dict | None = None) -> pd.DataFrame:
    """Score every row, preserving the inputs for explainability."""
    agency = agency or config.load_agency()
    scored = df.copy()
    breakdowns = scored.apply(lambda r: pd.Series(score_grant(r, agency)), axis=1)
    for column in breakdowns.columns:
        scored[column] = breakdowns[column]
    return scored


def rank_track(df: pd.DataFrame) -> pd.DataFrame:
    """Rank one track with deterministic tie-breakers."""
    ranked = df.sort_values(
        ["final_score", "strategic_alignment", "operational_fit", "grant_id"],
        ascending=[False, False, False, True],
        kind="stable",
    ).copy()
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    return ranked


def load_inputs(out_dir: Path) -> pd.DataFrame:
    """Join Layer 1 objective features to successful Layer 3 analyses."""
    if not config.LAYER1_OUTPUT.exists():
        raise FileNotFoundError(
            f"{config.LAYER1_OUTPUT} does not exist. Layer 4 requires the real "
            "Layer 1 output with financial_value_score and deadline_score."
        )

    deep_path = out_dir / "deep_analysis.csv"
    if not deep_path.exists():
        raise FileNotFoundError(f"{deep_path} does not exist; run Layer 3 first")

    features = pd.read_csv(config.LAYER1_OUTPUT)
    deep = pd.read_csv(deep_path)
    if "status" in deep.columns:
        failed = deep[deep["status"] != "ok"]
        if len(failed):
            print(f"WARNING: {len(failed)} grants have no valid Layer 3 analysis "
                  f"({failed['status'].value_counts().to_dict()}) and are NOT ranked. "
                  f"See ai_error_log.csv; rerun deep_analysis.py to retry.")
        deep = deep[deep["status"] == "ok"].copy()

    required_features = {"grant_id", "is_forecast", "financial_value_score", "deadline_score"}
    missing = required_features - set(features.columns)
    if missing:
        raise ValueError(
            "Layer 1 output is missing fields required by Layer 4: "
            + ", ".join(sorted(missing))
        )

    required_deep = {
        "grant_id",
        "strategic_alignment",
        "operational_fit",
        "applicant_role_verified",
        "eligibility_quote_verified",
        "strategic_quote_verified",
    }
    missing = required_deep - set(deep.columns)
    if missing:
        raise ValueError(
            "Layer 3 output is missing fields required by Layer 4: "
            + ", ".join(sorted(missing))
        )

    # Keep Layer 1 as the source of objective/raw fields and Layer 3 as the
    # source of semantic judgments. Overlapping descriptive fields from Layer 3
    # receive a _layer3 suffix rather than silently overwriting Layer 1.
    return features.merge(deep, on="grant_id", how="inner", suffixes=("", "_layer3"))


def run(mock: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create the open ranking and forecast watchlist CSVs."""
    agency = config.load_agency()
    out_dir = config.MOCK_RESULTS if mock else config.RESULTS
    out_dir.mkdir(parents=True, exist_ok=True)

    joined = load_inputs(out_dir)
    scored = score_dataframe(joined, agency)

    open_ranked = rank_track(scored[scored["track"] == "open"])
    watchlist = rank_track(scored[scored["track"] == "forecast"])

    open_path = out_dir / "ranked_grants.csv"
    watch_path = out_dir / "watchlist.csv"
    open_ranked.to_csv(open_path, index=False)
    watchlist.to_csv(watch_path, index=False)

    print(f"Wrote {open_path} ({len(open_ranked)} grants)")
    print(f"Wrote {watch_path} ({len(watchlist)} forecast grants)")
    return open_ranked, watchlist


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mock", action="store_true", help="read mock Layer 3 output")
    args = ap.parse_args()
    run(mock=args.mock)
