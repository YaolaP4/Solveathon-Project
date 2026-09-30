"""Layer 2 - fast semantic triage with Jev.

For every grant that survived Layer 1's hard filters, Jev answers four `choice`
questions (prompts/jev_triage.json): domain relevance, matched strategic goal,
applicant role, owning division. Jev returns a probability for every option, and
those probabilities are the confidence signal: a grant is deprioritized only when
Jev puts high probability on "irrelevant" or "ineligible"; everything else goes to
Layer 3. Deprioritized grants are kept (not deleted) so validation can sample them.

Usage:
    python src/semantic_triage.py            # real run (needs AI_GATEWAY_API_KEY, or a full cache)
    python src/semantic_triage.py --mock     # dry run with fake answers
    python src/semantic_triage.py --limit 20 # first 20 grants only
"""

import argparse
import copy
import json
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

import config
from clients import JevClient, MockJevClient
from llm_cache import ResponseCache, prompt_version, request_hash
from text_utils import strip_html, truncate

# Columns Layer 2 needs from Layer 1's output (data/processed/grants_features.csv).
REQUIRED_COLUMNS = [
    "grant_id", "opportunity_title", "agency_name", "summary_description",
    "applicant_types", "applicant_eligibility_description",
    "opportunity_assistance_listings", "funding_instruments",
    "is_forecast", "hard_filtered",
]
RELEVANCE_VALUE = {"none": 0.0, "weak": 1 / 3, "moderate": 2 / 3, "strong": 1.0}
MAX_SUMMARY_CHARS = 3000


# ── Prompt construction ─────────────────────────────────────────────────────

def load_prompt(agency: dict) -> tuple[str, dict, str]:
    """-> (context sentence, Jev question dict, prompt version hash)."""
    path = config.PROMPTS / "jev_triage.json"
    raw_text = path.read_text(encoding="utf-8")
    spec = json.loads(raw_text)
    context = spec["context"].format(agency_name=agency["agency_name"],
                                     mission=agency["mission"], user=agency["user"])
    questions = copy.deepcopy(spec["questions"])
    for q in questions.values():
        if q["criteria"] == "FROM_CONFIG:strategic_priorities":
            q["criteria"] = {p["id"]: f"{p['name']}: {p['description']}"
                             for p in agency["strategic_priorities"]}
            q["criteria"]["none"] = "Advances none of these goals."
        elif q["criteria"] == "FROM_CONFIG:divisions":
            q["criteria"] = {d["id"]: f"{d['name']} ({d['scope']})" for d in agency["divisions"]}
            q["criteria"]["none"] = "No division of this agency would own it."
    version = prompt_version(raw_text, json.dumps(config.prompt_fields(agency), sort_keys=True))
    return context, questions, version


def grant_state(row: pd.Series, context: str) -> dict:
    """The structured `state` Jev reasons over."""
    return {
        "task": context,
        "grant": {
            "title": str(row["opportunity_title"]),
            "federal_agency": str(row["agency_name"]),
            "assistance_listings": str(row.get("opportunity_assistance_listings", "") or ""),
            "funding_instruments": str(row.get("funding_instruments", "") or ""),
            "applicant_types": str(row.get("applicant_types", "") or "").replace(";", ", "),
            "eligibility_text": strip_html(row.get("applicant_eligibility_description", "")) or "(none given)",
            "summary": truncate(strip_html(row.get("summary_description", "")), MAX_SUMMARY_CHARS) or "(none given)",
        },
    }


# ── Confidence-aware routing ────────────────────────────────────────────────

def _probs(answers: dict, question: str) -> dict:
    return (answers.get(question) or {}).get("probabilities") or {}


def route(answers: dict, thresholds: dict) -> tuple[str, str]:
    """-> ("deep_review" | "deprioritized", reason). Pure function; unit-tested."""
    rel = _probs(answers, "domain_relevance")
    role = _probs(answers, "applicant_role")
    if not rel:
        return "deep_review", "missing Jev relevance answer"
    p_none = rel.get("none", 0.0)
    p_none_weak = p_none + rel.get("weak", 0.0)
    p_inelig = role.get("ineligible", 0.0)
    if p_none >= thresholds["deprioritize_if_p_none_at_least"]:
        return "deprioritized", f"P(unrelated)={p_none:.2f}"
    if p_none_weak >= thresholds["deprioritize_if_p_none_or_weak_at_least"]:
        return "deprioritized", f"P(unrelated or weak)={p_none_weak:.2f}"
    if p_inelig >= thresholds["deprioritize_if_p_ineligible_at_least"]:
        return "deprioritized", f"P(ineligible)={p_inelig:.2f}"
    return "deep_review", "not confidently irrelevant"


def summarize(answers: dict) -> dict:
    """Flatten Jev's answers into CSV columns."""
    out = {}
    for q in ("domain_relevance", "matched_goal", "applicant_role", "owning_division"):
        a = answers.get(q) or {}
        probs = a.get("probabilities") or {}
        choice = a.get("choice") or (max(probs, key=probs.get) if probs else None)
        out[q] = choice
        out[f"{q}_p"] = round(probs.get(choice, 0.0), 4) if choice else None
        out[f"{q}_probs"] = json.dumps({k: round(v, 4) for k, v in probs.items()})
    rel = _probs(answers, "domain_relevance")
    role = _probs(answers, "applicant_role")
    expected_rel = sum(RELEVANCE_VALUE.get(k, 0) * v for k, v in rel.items())
    p_ours = role.get("lead", 0.0) + role.get("partner", 0.0)
    out["expected_relevance"] = round(expected_rel, 4)
    out["p_lead_or_partner"] = round(p_ours, 4)
    # Orders the Layer 3 queue only; the final ranking is Layer 4's job.
    out["triage_priority"] = round(expected_rel * (0.5 + 0.5 * p_ours), 4)
    return out


# ── Runner ──────────────────────────────────────────────────────────────────

def load_grants() -> pd.DataFrame:
    if not config.LAYER1_OUTPUT.exists():
        import clean_data
        import deterministic
        clean_data.run()
        deterministic.run()
    df = pd.read_csv(config.LAYER1_OUTPUT)
    source = config.LAYER1_OUTPUT
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        sys.exit(f"Layer 1 output is missing columns Layer 2 needs: {missing}")
    print(f"Layer 2 input: {len(df)} grants from {source}")
    return df


def run(mock: bool = False, limit: int | None = None, workers: int = 8) -> pd.DataFrame:
    agency = config.load_agency()
    context, questions, version = load_prompt(agency)
    client = MockJevClient() if mock else JevClient()
    cache = ResponseCache(config.MOCK_CACHE if mock else config.CACHE, "layer2_jev")
    out_dir = config.MOCK_RESULTS if mock else config.RESULTS
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_grants()
    todo = df[~df["hard_filtered"].astype(bool)]
    if limit:
        todo = todo.head(limit)
    print(f"Triaging {len(todo)} grants (skipping {len(df) - len(todo)} hard-filtered or beyond --limit)")

    def triage(row) -> dict:
        state = grant_state(row, context)
        key = request_hash(client.model, version, {"state": state, "questions": questions})
        answers = cache.get(row["grant_id"], key)
        cached = answers is not None
        if not cached:
            answers = client.evaluate(state, questions)
            cache.put(row["grant_id"], key, client.model, version, answers)
        decision, reason = route(answers, agency["layer2_routing"])
        return {"grant_id": row["grant_id"], "opportunity_title": row["opportunity_title"],
                "track": "forecast" if str(row["is_forecast"]).lower() == "true" else "open",
                **summarize(answers), "route": decision, "route_reason": reason,
                "model": client.model, "prompt_version": version, "from_cache": cached}

    rows, errors = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(triage, r): r["grant_id"] for _, r in todo.iterrows()}
        for i, fut in enumerate(futures, 1):
            try:
                rows.append(fut.result())
            except Exception as e:  # one bad grant must not kill the run
                errors.append({"grant_id": futures[fut], "error": str(e)[:300]})
            if i % 100 == 0:
                print(f"  {i}/{len(futures)}")

    result = pd.DataFrame(rows)
    result.to_csv(out_dir / "jev_outputs.csv", index=False)
    if errors:
        pd.DataFrame(errors).to_csv(out_dir / "jev_errors.csv", index=False)
        print(f"WARNING: {len(errors)} grants failed; see {out_dir / 'jev_errors.csv'}. "
              f"They are NOT in jev_outputs.csv - rerun to retry them.")
    if len(result):
        print(result["route"].value_counts().to_string())
        print("By track:\n" + pd.crosstab(result["track"], result["route"]).to_string())
    print(f"Wrote {out_dir / 'jev_outputs.csv'}" + ("   [MOCK - fake answers]" if mock else ""))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mock", action="store_true", help="fake Jev answers; no API key needed")
    ap.add_argument("--limit", type=int, help="only triage the first N grants")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    run(mock=a.mock, limit=a.limit, workers=a.workers)
