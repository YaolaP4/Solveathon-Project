"""AI summaries and "why it matches" rationales, for the top N opportunities only.

For each one the chat model (Azure OpenAI) gets the announcement text and the matched plan
objective (prompts/rationale.txt) and returns: a summary, why it matches, eligibility notes,
deadline, one risk or gap, the applicant role a state agency would have, and two verbatim quotes.

Python then checks the model's work, as in the qualifier's Layer 3:
  * each quote must appear verbatim in the announcement; an unverified quote is hidden and logged;
  * an "ineligible" role only counts when its eligibility quote is verified;
  * ids must exist in the profile; unknown ids are dropped and logged.
Every caught problem goes to the AI check log shown on the Evaluation page.

The model never changes the score. It can only (a) move a record to the "not eligible" list
when it proves, with a verified quote, that a state agency cannot apply, (b) lower the confidence
band one step when it says the match to the plan objective is wrong, and (c) lower it one step and
flag it when it quotes a geographic limit that would exclude North Carolina.

Answers are cached in storage (cache/rationales/), keyed by the prompt version, the record's
text and its matched objective, so the daily job only pays for new or changed records.
"""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

import aoai
import config
from text_utils import quote_in_source, strip_html, truncate

ROLES = {"lead", "partner", "atypical", "ineligible", "unclear"}
DOWNGRADE = {"High": "Medium", "Medium": "Low", "Low": "Low"}
DEFAULT_TOP = {"agency": 40, "research": 5}


def template() -> tuple[str, str, str]:
    raw = (config.PROMPTS / "rationale.txt").read_text(encoding="utf-8")
    system, user = raw.split("=== USER ===")
    return system.replace("=== SYSTEM ===", "").strip(), user.strip(), raw


def _money(v) -> str:
    return "not stated" if v is None or pd.isna(v) else f"${float(v):,.0f}"


def build_prompt(r: pd.Series, agency: dict) -> tuple[str, str]:
    system, user, _ = template()
    goals = {g["id"]: g for g in agency["strategic_priorities"]}
    g = goals[r["matched_goal_id"]]
    o = next(o for o in g["objectives"] if o["id"] == r["matched_objective_id"])
    others = "\n".join(f"{x['id']} {x['name']}: {x['description']}" for gid, x in goals.items() if gid != g["id"])
    divs = "\n".join(f"{d['id']}: {d['name']} ({d['scope']})" for d in agency["divisions"])
    close = ("forecast, estimated " + (str(r["forecasted_close_date"])[:10] if pd.notna(r["forecasted_close_date"]) else "not stated")
             if r["is_forecast"] else (str(r["close_date_real"])[:10] if pd.notna(r["close_date_real"]) else "not stated"))
    fields = {
        "agency_name": agency["agency_name"], "mission": agency["mission"], "user": agency["user"],
        "plan_title": agency["profile"]["plan_title"], "goal_id": g["id"], "goal_name": g["name"],
        "goal_description": g["description"], "objective_id": o["id"], "objective_text": o["text"],
        "objective_source": o.get("source", ""), "other_goals": others, "divisions_block": divs,
        "title": r["opportunity_title"], "number": r["opportunity_number"], "federal_agency": r["agency_name"],
        "status": "forecasted" if r["is_forecast"] else "posted", "close_date": close,
        "award_ceiling": _money(r["award_ceiling"]), "cost_sharing": r["requires_cost_share"],
        "applicant_types": r["applicant_types"].replace(";", ", ") or "not stated",
        "description": truncate(strip_html(r["summary_description"]), 7000) or "not stated",
        "eligibility": truncate(strip_html(r["applicant_eligibility_description"]), 2500) or "not stated",
    }
    return system.format(**fields) if "{" in system else system, user.format(**fields)


def cache_key(r: pd.Series, user_prompt: str) -> str:
    _, _, raw = template()
    h = hashlib.sha1((aoai.chat_deployment() + "\n" + raw + "\n" + user_prompt).encode("utf-8")).hexdigest()[:16]
    return f"cache/rationales/{r['grant_id']}-{h}.json"


def _q(text: str) -> str:
    return (text or "").replace('"', "'").replace("“", "'").replace("”", "'")


def check(answer: dict, r: pd.Series, agency: dict) -> tuple[dict, list[dict]]:
    """Validate one answer against the source text and the profile. Returns (clean answer, problems)."""
    problems = []
    # Source = exactly what the model was shown (applicant types as listed in the prompt too).
    # Double quotes are treated like single quotes: inside a JSON string the model often swaps
    # "Domestic" for 'Domestic' to avoid escaping, which is not a change of wording.
    src = _q(f"{r['opportunity_title']}\n{strip_html(r['summary_description'])}\n"
             f"{strip_html(r['applicant_eligibility_description'])}\n{r['applicant_types']}\n"
             f"{r['applicant_types'].replace(';', ', ')}")

    def log(kind, detail):
        problems.append({"grant_id": r["grant_id"], "title": r["opportunity_title"], "kind": kind, "detail": detail})

    a = {k: answer.get(k) for k in ["summary", "why_it_matches", "fits_matched_goal", "better_goal_id", "evidence_quote",
                                    "applicant_role", "eligibility_notes", "eligibility_quote", "owning_division",
                                    "deadline_note", "risk_or_gap", "excludes_north_carolina", "geographic_quote"]}
    for k in ["summary", "why_it_matches", "eligibility_notes", "deadline_note", "risk_or_gap", "evidence_quote",
              "eligibility_quote", "geographic_quote"]:
        a[k] = str(a[k] or "").strip()
    for k in ["evidence_quote", "eligibility_quote", "geographic_quote"]:       # "no quote" answers are not quotes
        if a[k].lower().strip(" .'\"") in {"not stated", "n/a", "na", "none", "no quote"}:
            a[k] = ""
    a["evidence_verified"] = quote_in_source(_q(a["evidence_quote"]), src)
    if a["evidence_quote"] and not a["evidence_verified"]:
        log("quote_not_in_source", f"evidence quote not found verbatim: '{a['evidence_quote'][:120]}'")
    a["eligibility_verified"] = quote_in_source(_q(a["eligibility_quote"]), src)
    if a["eligibility_quote"] and not a["eligibility_verified"]:
        log("quote_not_in_source", f"eligibility quote not found verbatim: '{a['eligibility_quote'][:120]}'")
    a["geographic_verified"] = quote_in_source(_q(a["geographic_quote"]), src)
    excl = a["excludes_north_carolina"]
    a["excludes_north_carolina"] = excl is True or str(excl).lower() == "true"
    if a["excludes_north_carolina"] and not a["geographic_verified"]:
        log("unsupported_claim", "said the funding excludes North Carolina but gave no verified quote; not acted on")
        a["excludes_north_carolina"] = False
    role = str(a["applicant_role"] or "").strip().lower()
    if role not in ROLES:
        log("invalid_value", f"applicant_role '{role}' is not one of {sorted(ROLES)}")
        role = "unclear"
    if role == "ineligible" and not a["eligibility_verified"]:
        log("unsupported_claim", "said a state agency is ineligible but its eligibility quote was not verified; treated as unclear")
        role = "unclear"
    if role in ("lead", "partner") and r["s_eligibility"] == 0:
        log("contradiction", f"said role '{role}' but the structured eligibility excludes state governments")
    a["applicant_role"] = role
    divs = {d["id"] for d in agency["divisions"]}
    if a["owning_division"] not in divs:
        if a["owning_division"] not in (None, "", "none"):
            log("invalid_value", f"owning_division '{a['owning_division']}' is not a known division")
        a["owning_division"] = ""
    goals = {g["id"] for g in agency["strategic_priorities"]}
    a["better_goal_id"] = a["better_goal_id"] if a["better_goal_id"] in goals and a["better_goal_id"] != r["matched_goal_id"] else ""
    a["fits_matched_goal"] = bool(a["fits_matched_goal"]) if isinstance(a["fits_matched_goal"], bool) else str(a["fits_matched_goal"]).lower() == "true"
    if not a["fits_matched_goal"]:
        log("disagrees_with_match", f"AI says the grant does not fit {r['matched_objective_id']}"
            + (f"; suggests {a['better_goal_id']}" if a["better_goal_id"] else ""))
    return a, problems


def review_one(r: pd.Series, agency: dict, store) -> tuple[dict | None, list[dict], dict]:
    system, user = build_prompt(r, agency)
    key = cache_key(r, user)
    cached = store.read_json(key)
    usage = {}
    if cached is None:
        content, usage = aoai.chat_json(system, user, max_tokens=1600)
        try:
            answer = json.loads(content)
        except json.JSONDecodeError:      # usually a cut-off answer: retry once with more room
            content, usage = aoai.chat_json(system, user, max_tokens=3000)
            try:
                answer = json.loads(content)
            except json.JSONDecodeError:
                return None, [{"grant_id": r["grant_id"], "title": r["opportunity_title"], "kind": "invalid_json",
                               "detail": content[:200]}], usage
        store.write_json(key, {"answer": answer, "model": aoai.chat_deployment()})
    else:
        answer = cached["answer"]
    clean, problems = check(answer, r, agency)
    return clean, problems, usage


def select(scored: pd.DataFrame, top: dict) -> pd.DataFrame:
    parts = [scored[scored["track"] == t].head(n) for t, n in top.items()]
    return pd.concat(parts) if parts else scored.iloc[0:0]


def review(scored: pd.DataFrame, agency: dict, store, log=print, top: dict | None = None) -> tuple[dict, list, dict]:
    """Returns ({grant_id: answer}, problems, stats). Skipped entirely if Azure OpenAI is not configured."""
    top = top or (agency.get("matchmaker") or {}).get("ai_review_top", DEFAULT_TOP)
    pick = select(scored, top)
    if not aoai.available():
        log("  AI rationales: skipped (Azure OpenAI not configured); the app shows the score breakdown instead")
        return {}, [], {"reviewed": 0, "skipped": len(pick), "reason": "Azure OpenAI not configured"}
    results, problems, tokens, errors = {}, [], {"prompt_tokens": 0, "completion_tokens": 0}, 0

    def one(item):
        _, r = item
        try:
            return r["grant_id"], *review_one(r, agency, store)
        except Exception as e:
            return r["grant_id"], None, [{"grant_id": r["grant_id"], "title": r["opportunity_title"], "kind": "api_error",
                                          "detail": str(e)[:200]}], {}

    with ThreadPoolExecutor(6) as pool:
        for gid, ans, probs, usage in pool.map(one, pick.iterrows()):
            problems += probs
            for k in tokens:
                tokens[k] += usage.get(k, 0)
            if ans is None:
                errors += 1
            else:
                results[gid] = ans
    stats = {"reviewed": len(results), "errors": errors, "model": f"{aoai.chat_model_name()} (Azure OpenAI)", **tokens,
             "quotes_checked": 2 * len(results),
             "quotes_verified": sum(a["evidence_verified"] + a["eligibility_verified"] for a in results.values())}
    log(f"  AI rationales: {len(results)} reviewed ({errors} errors), {len(problems)} problems caught, "
        f"{tokens['prompt_tokens'] + tokens['completion_tokens']:,} new tokens")
    return results, problems, stats


def apply(scored: pd.DataFrame, reviews: dict) -> pd.DataFrame:
    """Attach reviews and apply the two allowed adjustments (never the score)."""
    out = scored.copy()
    out["ai"] = out["grant_id"].map(lambda g: reviews.get(g))
    adj = []
    for i, r in out.iterrows():
        a = r["ai"]
        note = ""
        if isinstance(a, dict):
            geographic = bool(a.get("excludes_north_carolina") and a.get("geographic_verified"))
            if a["applicant_role"] == "ineligible" and a["eligibility_verified"] and r["track"] == "agency" and not geographic:
                out.at[i, "track"] = "not_eligible"
                note = "moved to 'not eligible': AI review quoted eligibility text that excludes this agency"
            elif geographic and r["track"] == "agency":
                # Flag, do not remove: the model once read a standard "territories may also apply" clause as a
                # limit and would have hidden an HIV program for the South. A missed grant costs more than a
                # minute spent passing a bad match, so staff see it with the quote and decide.
                out.at[i, "confidence"] = DOWNGRADE[r["confidence"]]
                note = (f"check eligibility: AI review quoted a possible geographic limit that excludes North Carolina"
                        f" (confidence lowered from {r['confidence']})")
            elif not a["fits_matched_goal"] and r["confidence"] != "Low":
                out.at[i, "confidence"] = DOWNGRADE[r["confidence"]]
                note = f"confidence lowered from {r['confidence']}: AI review says the match to {r['matched_objective_id']} is weak"
        adj.append(note)
    out["review_adjustment"] = adj
    out = out.sort_values("score", ascending=False, kind="stable").reset_index(drop=True)
    out["rank"] = out.groupby("track").cumcount() + 1
    return out
