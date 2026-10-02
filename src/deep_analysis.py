"""Layer 3 - deep evaluation with Muse Spark 1.3 (via the Vercel AI Gateway).

Runs only on grants Layer 2 routed to "deep_review". For each one the model returns
structured judgments plus verbatim evidence quotes (prompts/deep_analysis.txt).
Python then checks the model's work:

  * every quote must appear verbatim in the grant text; an unverified eligibility
    quote downgrades the applicant role to "unclear";
  * ids must exist in the agency config, scores must be in range;
  * Layer 2 (Jev) and Layer 3 answers are compared, and disagreements are logged.

Every caught problem goes to data/results/ai_error_log.csv - the raw material for
"one place the AI was wrong and how we caught it".

Deadlines and award size are NOT judged here; they are deterministic (Layers 1/4).

Usage:
    python src/deep_analysis.py            # real run (needs AI_GATEWAY_API_KEY, or a full cache)
    python src/deep_analysis.py --mock     # dry run on mock Layer 2 output
"""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

import config
from clients import ChatClient, MockChatClient
from llm_cache import ResponseCache, prompt_version, request_hash
from semantic_triage import load_grants
from text_utils import quote_in_source, strip_html, truncate

ROLES = {"lead", "partner", "atypical", "ineligible", "unclear"}
MAX_SUMMARY_CHARS = 8000
MAX_ELIGIBILITY_CHARS = 3000


# ── Prompt ──────────────────────────────────────────────────────────────────

def load_template() -> tuple[str, str, str]:
    raw = (config.PROMPTS / "deep_analysis.txt").read_text(encoding="utf-8")
    system, user = raw.split("=== USER ===")
    system = system.replace("=== SYSTEM ===", "").strip()
    return system, user.strip(), raw


def agency_blocks(agency: dict) -> dict:
    pri = []
    for p in agency["strategic_priorities"]:
        pri.append(f"{p['id']} {p['name']}: {p['description']}")
        pri += [f"  {o['id']}: {o['text']}" for o in p["objectives"]]
    div = [f"{d['id']}: {d['name']} ({d['scope']})" for d in agency["divisions"]]
    return {"agency_name": agency["agency_name"], "mission": agency["mission"],
            "user": agency["user"], "priorities_block": "\n".join(pri),
            "divisions_block": "\n".join(div)}


def grant_texts(row: pd.Series) -> dict:
    return {
        "title": str(row["opportunity_title"]),
        "federal_agency": str(row["agency_name"]),
        "assistance_listings": str(row.get("opportunity_assistance_listings", "") or "(none)"),
        "funding_instruments": str(row.get("funding_instruments", "") or "(none)"),
        "applicant_types": str(row.get("applicant_types", "") or "(none)").replace(";", ", "),
        "summary": truncate(strip_html(row.get("summary_description", "")), MAX_SUMMARY_CHARS) or "(none given)",
        "eligibility": truncate(strip_html(row.get("applicant_eligibility_description", "")),
                                MAX_ELIGIBILITY_CHARS) or "(none given)",
    }


# ── Parsing and validation ──────────────────────────────────────────────────

def parse_json(text: str) -> dict:
    """Models sometimes wrap JSON in ```fences``` or add a sentence; take the object."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in the response")
    return json.loads(m.group(0))


def validate(out: dict, agency: dict) -> list[str]:
    """-> list of problems (empty = valid)."""
    problems = []
    goal_ids = {p["id"] for p in agency["strategic_priorities"]} | {"none"}
    obj_ids = config.objective_ids(agency) | {"none"}
    div_ids = {d["id"] for d in agency["divisions"]} | {"none"}
    for k in ("strategic_alignment", "operational_fit"):
        v = out.get(k)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 10:
            problems.append(f"{k} must be a number 0-10, got {v!r}")
    if out.get("matched_goal") not in goal_ids:
        problems.append(f"matched_goal {out.get('matched_goal')!r} is not a goal id")
    if out.get("matched_objective") not in obj_ids:
        problems.append(f"matched_objective {out.get('matched_objective')!r} is not an objective id")
    elif (out.get("matched_objective") != "none"
          and not str(out["matched_objective"]).startswith(f"{out.get('matched_goal')}.")):
        problems.append(f"objective {out['matched_objective']} does not belong to goal {out.get('matched_goal')}")
    if out.get("applicant_role") not in ROLES:
        problems.append(f"applicant_role {out.get('applicant_role')!r} not in {sorted(ROLES)}")
    if out.get("owning_division") not in div_ids:
        problems.append(f"owning_division {out.get('owning_division')!r} is not a division id")
    if not isinstance(out.get("recommended_for_review"), bool):
        problems.append("recommended_for_review must be true/false")
    if not isinstance(out.get("restrictions", []), list):
        problems.append("restrictions must be a list")
    for k in ("strategic_reason", "one_line_rationale", "major_risk"):
        if not isinstance(out.get(k), str) or not out[k].strip():
            problems.append(f"{k} is missing")
    return problems


# ── Checks on the model's claims ────────────────────────────────────────────

def verify(out: dict, texts: dict) -> tuple[dict, list[dict]]:
    """Check quotes against the source. -> (verified fields, error-log entries)."""
    errors = []
    strategic_src = f"{texts['title']}\n{texts['summary']}"
    elig_src = f"{texts['eligibility']}\n{texts['summary']}\n{texts['applicant_types']}"

    s_ok = quote_in_source(out.get("strategic_evidence_quote"), strategic_src)
    e_quote = out.get("eligibility_evidence_quote") or ""
    e_ok = quote_in_source(e_quote, elig_src)

    role = out.get("applicant_role")
    role_verified = role
    if not s_ok:
        errors.append({"check": "unverified_strategic_quote", "severity": "high",
                       "detail": f"quote not found in grant text: {str(out.get('strategic_evidence_quote'))[:200]!r}"})
    if role in ("lead", "partner") and not e_ok:
        role_verified = "unclear"
        errors.append({"check": "unverified_eligibility_quote", "severity": "high",
                       "detail": f"claimed role '{role}' but its quote was not found in the eligibility text "
                                 f"({e_quote[:200]!r}); role downgraded to 'unclear'"})
    elif e_quote and not e_ok:
        errors.append({"check": "unverified_eligibility_quote", "severity": "medium",
                       "detail": f"quote not found: {e_quote[:200]!r}"})
    return ({"strategic_quote_verified": s_ok, "eligibility_quote_verified": e_ok,
             "applicant_role_verified": role_verified}, errors)


def compare_layers(l2: pd.Series, out: dict) -> list[dict]:
    """Log where Jev (Layer 2) and the deep model (Layer 3) disagree."""
    found = []
    rel, align = l2.get("domain_relevance"), out.get("strategic_alignment", 0)
    if rel == "strong" and align <= 3:
        found.append({"check": "layer2_vs_layer3_relevance", "severity": "medium",
                      "detail": f"Jev said 'strong' (p={l2.get('domain_relevance_p')}) but deep model scored alignment {align}/10"})
    if rel in ("none", "weak") and align >= 7:
        found.append({"check": "layer2_vs_layer3_relevance", "severity": "high",
                      "detail": f"Jev said '{rel}' (p={l2.get('domain_relevance_p')}) but deep model scored alignment {align}/10 "
                                f"- a possible Layer 2 false negative"})
    r2, r3 = l2.get("applicant_role"), out.get("applicant_role")
    ours, not_ours = {"lead", "partner"}, {"atypical", "ineligible"}
    if (r2 in ours and r3 in not_ours) or (r2 in not_ours and r3 in ours):
        found.append({"check": "layer2_vs_layer3_role", "severity": "medium",
                      "detail": f"Jev role '{r2}' vs deep model role '{r3}'"})
    if l2.get("owning_division") and out.get("owning_division") and l2["owning_division"] != out["owning_division"]:
        found.append({"check": "layer2_vs_layer3_division", "severity": "low",
                      "detail": f"Jev division {l2['owning_division']} vs deep model {out['owning_division']}"})
    return found


# ── Runner ──────────────────────────────────────────────────────────────────

def run(mock: bool = False, limit: int | None = None, workers: int = 4) -> pd.DataFrame:
    agency = config.load_agency()
    system, user_tmpl, raw_prompt = load_template()
    blocks = agency_blocks(agency)
    version = prompt_version(raw_prompt, json.dumps(config.prompt_fields(agency), sort_keys=True))
    client = MockChatClient() if mock else ChatClient()
    cache = ResponseCache(config.MOCK_CACHE if mock else config.CACHE, "layer3_deep")
    out_dir = config.MOCK_RESULTS if mock else config.RESULTS

    l2 = pd.read_csv(out_dir / "jev_outputs.csv")
    queue = l2[l2["route"] == "deep_review"].sort_values("triage_priority", ascending=False)
    cap = limit or agency.get("layer3", {}).get("max_grants")
    overflow = queue.iloc[cap:] if cap else queue.iloc[0:0]
    queue = queue.iloc[:cap] if cap else queue
    grants = load_grants().set_index("grant_id")
    print(f"Layer 3: {len(queue)} grants to analyze"
          + (f"; {len(overflow)} more routed to deep review but over the cap (logged)" if len(overflow) else ""))

    def analyze(l2row: pd.Series) -> tuple[dict, list[dict]]:
        gid = l2row["grant_id"]
        grant = grants.loc[gid]
        if isinstance(grant, pd.DataFrame):  # duplicate id; Layer 0 should have removed it
            grant = grant.iloc[0]
        texts = grant_texts(grant)
        messages = [{"role": "system", "content": system.format(**blocks)},
                    {"role": "user", "content": user_tmpl.format(**blocks, **texts)}]
        key = request_hash(client.model, version, messages)
        cached = cache.get(gid, key)
        log = []
        if cached is not None:
            out, attempts = cached["parsed"], cached["attempts"]
        else:
            out, attempts, problems = None, [], []
            for _ in range(2):  # one retry, telling the model what was wrong
                raw = client.complete(messages if not problems else messages + [
                    {"role": "assistant", "content": attempts[-1]},
                    {"role": "user", "content": "Your JSON had these problems: " + "; ".join(problems)
                                                + ". Return the corrected JSON object only."}])
                attempts.append(raw)
                try:
                    candidate = parse_json(raw)
                    problems = validate(candidate, agency)
                except (ValueError, json.JSONDecodeError) as e:
                    candidate, problems = None, [f"unparseable JSON: {e}"]
                if not problems:
                    out = candidate
                    break
            if len(attempts) > 1:
                log.append({"check": "invalid_output_retried", "severity": "medium",
                            "detail": f"first answer rejected by validation; {'fixed on retry' if out else 'still invalid: ' + '; '.join(problems)}"})
            cache.put(gid, key, client.model, version, {"parsed": out, "attempts": attempts})
        if out is None:
            log.append({"check": "invalid_output", "severity": "high", "detail": "no valid JSON after retry"})
            return {"grant_id": gid, "status": "invalid_output"}, log
        checks, errs = verify(out, texts)
        log += errs + compare_layers(l2row, out)
        row = {"grant_id": gid, "opportunity_title": l2row["opportunity_title"], "track": l2row["track"],
               "status": "ok", **{k: out.get(k) for k in (
                   "strategic_alignment", "matched_goal", "matched_objective", "strategic_reason",
                   "strategic_evidence_quote", "applicant_role", "eligibility_evidence_quote",
                   "owning_division", "operational_fit", "operational_reason", "major_risk",
                   "recommended_for_review", "one_line_rationale")},
               "restrictions": json.dumps(out.get("restrictions", [])), **checks,
               "model": client.model, "prompt_version": version, "from_cache": cached is not None}
        return row, log

    rows, error_log = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(analyze, r): r for _, r in queue.iterrows()}
        for i, fut in enumerate(futures, 1):
            l2row = futures[fut]
            try:
                row, log = fut.result()
            except Exception as e:
                row, log = {"grant_id": l2row["grant_id"], "status": "api_error"}, [
                    {"check": "api_error", "severity": "high", "detail": str(e)[:300]}]
            rows.append(row)
            error_log += [{"grant_id": l2row["grant_id"], "opportunity_title": l2row["opportunity_title"],
                           "layer": 3, **e} for e in log]
            if i % 25 == 0:
                print(f"  {i}/{len(futures)}")
    for _, r in overflow.iterrows():
        error_log.append({"grant_id": r["grant_id"], "opportunity_title": r["opportunity_title"], "layer": 3,
                          "check": "over_layer3_cap", "severity": "info",
                          "detail": f"routed to deep review but beyond layer3.max_grants={cap}; not analyzed"})

    result = pd.DataFrame(rows)
    result.to_csv(out_dir / "deep_analysis.csv", index=False)
    log_df = pd.DataFrame(error_log, columns=["grant_id", "opportunity_title", "layer", "check", "severity", "detail"])
    log_df.to_csv(out_dir / "ai_error_log.csv", index=False)
    print(result["status"].value_counts().to_string() if len(result) else "no grants analyzed")
    if len(log_df):
        print("AI error log:\n" + log_df["check"].value_counts().to_string())
    print(f"Wrote {out_dir / 'deep_analysis.csv'} and {out_dir / 'ai_error_log.csv'}"
          + ("   [MOCK - fake answers]" if mock else ""))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mock", action="store_true", help="fake model answers; no API key needed")
    ap.add_argument("--limit", type=int, help="analyze at most N grants (overrides config cap)")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    run(mock=a.mock, limit=a.limit, workers=a.workers)
