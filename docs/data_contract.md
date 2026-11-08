# Data contract

Every part of the system reads and writes JSON in one Blob Storage container (`ffm-data`). On a laptop the
same paths live under `data/store/` (see `src/storage.py`). Agreeing on these shapes is what lets the job,
the app and the evaluation work independently.

| Path | Written by | Read by | Contents |
|---|---|---|---|
| `profiles/{agency}.json` | job (from the reviewed `agency/profiles/{agency}.json`) | app | Mission, goals and objectives with plan page citations (NC DHHS: 5 goals, 21 objectives, 4 priority areas; NC DEQ: 7 goals, 26 objectives), program areas, 40 keywords, eligible applicant type, divisions |
| `raw/{yyyy-mm-dd}/grants.json` | job: ingest | job: replay | Untouched Grants.gov search results for the day + which ids each keyword search returned |
| `details/{id}.json`, `details/index.json` | job: ingest | job | Untouched `fetchOpportunity` responses (cached; refetched when the listing changes or after 7 days) |
| `opportunities/latest.json` | job: normalize | anyone | Clean records in the minimum schema (below) |
| `scored/{agency}/latest.json` (+ `{date}.json`) | job: score + summarize | app | Ranked records with score, breakdown, matched goal/objective, confidence, track, AI review, award history; AI check log |
| `alerts/{agency}/latest.json` | job | app | Ids new since the previous run; strong matches closing in 10 days or fewer |
| `decisions/{agency}.json` | app | app, evaluation | Pursue / Maybe / Pass per opportunity: who, when, note, score at the time (full history kept) |
| `eval/{agency}/sample.json` | app (once per agency) | app | The fixed labeling sample, why each item is in it, and a snapshot of what labelers see |
| `eval/{agency}/labels.json` | app | app | Relevant / not relevant / unsure per item per labeler |
| `eval/keyword_baseline/{date}.json` | job | app | Which ids Grants.gov's own keyword search returns for each profile keyword |
| `runs/{timestamp}.json`, `runs/latest.json` | job | app | Run log: counts per stage and per agency, errors, duration, status |
| `runs/last_attempt.json` | job (success or failure) | app | The most recent attempt; a failure shows a red warning in the app |
| `cache/embeddings/*`, `cache/rationales/*`, `cache/aln_history.json` | job | job | Caches so daily re-runs only pay for new or changed records |

## Minimum opportunity schema (`opportunities/latest.json`)

`id, source, number, title, agency, top_agency, status (posted | forecasted), open_date, close_date
(date | "rolling" | "no close date"), days_to_close, eligibility (applicant-type codes), eligibility_text,
category, award_ceiling, award_floor, total_funding, expected_awards, cost_sharing (True | False | Unknown),
assistance_listings, funding_instruments, description (plain text), url (official Grants.gov page),
ingested_at, low_quality, quality_issues[]`

Records missing key fields are **flagged** (`low_quality`, `quality_issues`), never silently dropped.

## Scored record (`scored/{agency}/latest.json` → `records[]`)

Everything in the minimum schema, plus:

```json
{
  "rank": 3, "track": "agency | research | not_eligible", "score": 75.8, "confidence": "High | Medium | Low",
  "matched_goal": {"id": "G3", "name": "Behavioral Health and Resilience", "source": "Strategic Plan ..., pp. 12-13"},
  "matched_objective": {"id": "G3.O1", "text": "...", "source": "Plan p. 12"},
  "breakdown": [{"signal": "semantic", "label": "Plan alignment (semantic)", "value": 0.83, "weight": 0.45,
                 "points": 37.4, "max_points": 45.0, "reason": "closest objective G3.O1: ..."}],
  "keywords_matched": ["behavioral health"], "award_history": {"verdict": "...", "nc_dhhs_usd": 0},
  "ai": {"summary": "...", "why_it_matches": "...", "evidence_quote": "...", "evidence_verified": true,
         "applicant_role": "lead", "eligibility_notes": "...", "eligibility_quote": "...", "eligibility_verified": true,
         "owning_division": "DMHDDSUS", "deadline_note": "...", "risk_or_gap": "...", "fits_matched_goal": true},
  "review_adjustment": "", "new_since_last_run": false, "closing_soon": false
}
```

## Decision record (`decisions/{agency}.json`)

```json
{"decisions": {"<opportunity id>": [
  {"decision": "Pursue", "by": "PP", "note": "Route to DMH/DD/SUS", "at": "2026-11-07T19:02:11+00:00",
   "score_at_decision": 75.8, "confidence_at_decision": "High", "run_id": "2026-11-07T18-40-03Z"}]}}
```

Writes use the blob's ETag (optimistic concurrency), so two people deciding at the same moment never
overwrite each other.
