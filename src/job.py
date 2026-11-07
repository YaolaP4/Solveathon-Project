"""The daily refresh job (MODE=job): ingest -> normalize -> score -> summarize -> alerts -> run log.

    python src/job.py                 # full run (live Grants.gov; Azure OpenAI if configured)
    python src/job.py --replay DATE   # re-run on a saved raw/{DATE}/grants.json (no network for Grants.gov)

Idempotent: every output is overwritten as a whole, caches make re-runs cheap, and a re-run on the
same day replaces that day's files. It logs counts at each stage and exits non-zero on failure, so
Azure marks the Container Apps job execution as Failed.

Writes (data contract, docs/data_contract.md):
    profiles/{agency}.json                 the reviewed agency profile used for this run
    raw/{date}/grants.json                 untouched API responses (ingest)
    opportunities/latest.json              clean records in the minimum schema (+ dated copy)
    scored/{agency}/latest.json            ranked list with score, breakdown, matched goal, AI review (+ dated copy)
    alerts/{agency}/latest.json            new since the previous run, closing in <= 10 days
    eval/keyword_baseline/{date}.json      which ids each Grants.gov keyword search returned
    runs/{timestamp}.json                  run log: counts per stage, errors, duration
"""

import argparse
import sys
import time
import traceback
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

import aoai
import config
import grantsgov
import matcher
import normalize
import rationale
from storage import get_store

ET = ZoneInfo("America/New_York")
ALERT_DAYS = 10


def agency_id(agency: dict) -> str:
    return agency["profile"]["agency_id"]


def profile_document(agency: dict) -> dict:
    """The starter kit's standard profile template, built from agency/priorities.json."""
    p = agency["profile"]
    return {
        "agency_id": p["agency_id"], "agency_name": agency["agency_name"], "mission": agency["mission"],
        "user": agency["user"], "source": {"title": p["plan_title"], "url": p["plan_url"]},
        "reviewed_by": p["reviewed_by"],
        "goals": [{"id": g["id"], "name": g["name"], "description": g["description"], "source": g.get("source", ""),
                   "objectives": g["objectives"]} for g in agency["strategic_priorities"]],
        "program_areas": p["program_areas"], "divisions": agency["divisions"], "keywords": p["keywords"],
        "eligible_applicant_types": p["eligible_applicant_types"], "eligibility_note": p["eligibility_note"],
    }


def _iso(v):
    if v is None or (not isinstance(v, (list, dict)) and pd.isna(v)):
        return None
    return pd.Timestamp(v).strftime("%Y-%m-%d")


def scored_record(r: pd.Series, w: dict, goals: dict, ingested_at: str) -> dict:
    rec = normalize.minimum_record(r, ingested_at)
    g = goals[r["matched_goal_id"]]
    obj = next(o for o in g["objectives"] if o["id"] == r["matched_objective_id"])
    rec.update({
        "rank": int(r["rank"]), "track": r["track"], "score": float(r["score"]), "confidence": r["confidence"],
        "matched_goal": {"id": g["id"], "name": g["name"], "source": g.get("source", "")},
        "matched_objective": {"id": obj["id"], "text": obj["text"], "source": obj.get("source", "")},
        "goal_similarities": r["goal_similarities"], "breakdown": matcher.breakdown(r, w),
        "keywords_matched": list(r["keywords_in_title"]) + list(r["keywords_in_text"]),
        "keywords_in_title": list(r["keywords_in_title"]),
        "research_reason": r["research_mechanism_reason"] if r["research_mechanism"] else "",
        "award_history": r["award_history"] or {},
        "forecast_post_date": _iso(r["forecasted_post_date"]) if r["is_forecast"] else None,
        "forecast_close_date": _iso(r["forecasted_close_date"]) if r["is_forecast"] else None,
        "ai": r["ai"] if isinstance(r["ai"], dict) else None,
        "review_adjustment": r["review_adjustment"],
    })
    return rec


def run(replay: str | None = None, log=print) -> dict:
    t0 = time.time()
    store = get_store()
    agency = config.load_agency()
    aid = agency_id(agency)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    today = (replay or now.astimezone(ET).strftime("%Y-%m-%d"))
    run_id = now.strftime("%Y-%m-%dT%H-%M-%SZ")
    stages, errors = {}, []
    log(f"Daily refresh {run_id} for {aid} (storage: {store.describe()}, Azure OpenAI: "
        f"{'on' if aoai.available() else 'off'})")

    # 0. Profile (one-time seed, refreshed from the reviewed repo file every run)
    store.write_json(f"profiles/{aid}.json", profile_document(agency), indent=2)

    # 1. Ingest
    log("1/5 ingest")
    if replay:
        raw = store.read_json(f"raw/{replay}/grants.json")
        if raw is None:
            raise SystemExit(f"no raw/{replay}/grants.json to replay")
        hits = raw["hits"]
        details = {h["id"]: store.read_json(f"details/{h['id']}.json") for h in hits}
        details = {k: v for k, v in details.items() if v}
        kw_hits = raw.get("keyword_hits", {})
        stages["ingest"] = {"pulled": len(hits), "replayed_from": replay}
    else:
        ing = grantsgov.ingest(store, agency["profile"]["keywords"], today, log)
        hits, details, kw_hits = ing["hits"], ing["details"], ing["keyword_hits"]
        stages["ingest"] = ing["stats"]
        errors += ing["errors"]
    if len(hits) < 50:
        raise RuntimeError(f"only {len(hits)} opportunities pulled; refusing to overwrite yesterday's results")

    # 2. Normalize
    log("2/5 normalize")
    live, nstats = normalize.normalize(hits, details, today, agency)
    stages["normalize"] = nstats
    ingested_at = now.isoformat()
    store.write_json("opportunities/latest.json", [normalize.minimum_record(r, ingested_at) for _, r in live.iterrows()])
    log(f"  {nstats['records_out']} live records ({nstats['posted']} posted, {nstats['forecasted']} forecasted), "
        f"{nstats['dropped_closed_or_admin']} closed/admin dropped, {nstats['duplicates_dropped']} duplicates, "
        f"{nstats['low_quality']} flagged low quality")

    # 3. Score
    log("3/5 score")
    scored, meta = matcher.score(live, agency, store, log)
    stages["score"] = {**meta, "scored": len(scored),
                       "by_track": scored["track"].value_counts().to_dict(),
                       "by_confidence_agency_track": scored.loc[scored["track"] == "agency", "confidence"].value_counts().to_dict()}

    # 4. Summarize (top N only)
    log("4/5 AI rationales")
    reviews, problems, rstats = rationale.review(scored, agency, store, log)
    scored = rationale.apply(scored, reviews)
    stages["summarize"] = {**rstats, "problems_caught": len(problems)}

    # 5. Publish: scored list, alerts, keyword baseline, run log
    log("5/5 publish")
    w = meta["weights"]
    goals = {g["id"]: g for g in agency["strategic_priorities"]}
    records = [scored_record(r, w, goals, ingested_at) for _, r in scored.iterrows()]
    previous = store.read_json(f"scored/{aid}/latest.json", default=None)
    prev_ids = set(previous["seen_ids"]) if previous and previous.get("seen_ids") else None
    prev_ids_all = prev_ids if prev_ids is not None else set()
    for rec in records:
        rec["new_since_last_run"] = prev_ids is not None and rec["id"] not in prev_ids_all
        rec["closing_soon"] = rec["days_to_close"] is not None and 0 <= rec["days_to_close"] <= ALERT_DAYS
    doc = {
        "agency_id": aid, "run_id": run_id, "generated_at": now.isoformat(), "as_of": today,
        "method": meta, "counts": stages["score"]["by_track"], "seen_ids": [r["id"] for r in records],
        "previous_run_id": previous.get("run_id") if previous else None,
        "ai_checks": problems, "ai_stats": rstats, "records": records,
    }
    store.write_json(f"scored/{aid}/latest.json", doc)
    store.write_json(f"scored/{aid}/{today}.json", doc)
    alerts = {"run_id": run_id, "generated_at": now.isoformat(),
              "new_since_last_run": [r["id"] for r in records if r["new_since_last_run"] and r["track"] == "agency"],
              "closing_soon": [r["id"] for r in records if r["closing_soon"] and r["track"] == "agency"
                               and r["confidence"] in ("High", "Medium")],
              "first_run": prev_ids is None}
    store.write_json(f"alerts/{aid}/latest.json", alerts)
    store.write_json(f"eval/keyword_baseline/{today}.json", {"date": today, "keyword_hits": kw_hits})
    store.write_json("eval/keyword_baseline/latest.json", {"date": today, "keyword_hits": kw_hits})

    run_log = {"run_id": run_id, "agency_id": aid, "started_at": now.isoformat(),
               "finished_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
               "duration_s": round(time.time() - t0, 1), "status": "succeeded", "replay": replay,
               "counts": {"pulled": stages["ingest"].get("pulled"), "live": nstats["records_out"],
                          "new": len(alerts["new_since_last_run"]), "scored": len(scored),
                          "ai_reviewed": rstats.get("reviewed", 0), "errors": len(errors)},
               "stages": stages, "errors": errors[:50]}
    store.write_json(f"runs/{run_id}.json", run_log)
    store.write_json("runs/latest.json", run_log)
    log(f"Done in {run_log['duration_s']} s: {run_log['counts']}")
    return run_log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replay", help="re-run on raw/{DATE}/grants.json instead of calling Grants.gov")
    a = ap.parse_args()
    try:
        run(a.replay)
        return 0
    except BaseException as e:  # record the failure so the app's status page shows it, then fail the job
        traceback.print_exc()
        try:
            now = datetime.now(timezone.utc).replace(microsecond=0)
            get_store().write_json(f"runs/{now.strftime('%Y-%m-%dT%H-%M-%SZ')}.json",
                                   {"run_id": now.isoformat(), "status": "failed", "error": str(e)[:500],
                                    "finished_at": now.isoformat()})
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
