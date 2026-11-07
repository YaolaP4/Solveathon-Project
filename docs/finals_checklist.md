# Finals: goals vs. what we have

Source: the finals starter kit ("Federal Funds Matchmaker", sections 1–8) and the Azure access guide.
Status as of Saturday 7 Nov 2026, afternoon. ✅ done · ⏳ in progress · 👥 needs the team · ❌ not doing (with reason)

**Deployment is required.** The deliverables checklist asks for a "working prototype on the provided Azure
environment (public URL works on venue Wi-Fi and on a phone hotspot)", and the de-scope ladder says the
prototype "is expected to run on Azure". It is deployed:
**https://app-ffm-web.salmonmushroom-cf3974d2.eastus2.azurecontainerapps.io**

## Minimum viable demo (kit 8.5: "never cut these")

| Requirement | Status | What we have |
|---|---|---|
| One real agency profile from a real strategic plan | ✅ | Two: NC DHHS (current 2026–2030 plan: 5 goals, 21 objectives, 4 priority areas) and NC DEQ (2025–2029 plan: 7 goals, 26 objectives), each with plan page numbers, 40 keywords, program areas and divisions (`agency/profiles/`, Agency profile page) |
| Real Grants.gov data | ✅ | Live API every day: ~1,460 posted + forecasted listings, full details for each |
| A ranked list with an explanation per item | ✅ | Every record has a 5-signal score breakdown; the top 45 also get an AI reason with checked quotes |
| A human decision button | ✅ | Pursue / Maybe / Pass with name and note, from the list or the detail page; full history kept |
| One evaluation number + one honest failure | ✅ / 👥 | Against the qualifier's 1,037 reviewed grants still live: AUC 0.92 (`docs/tuning_report.md`). Precision@10 on fresh human labels needs two teammates to label the sample (about 20 minutes, Evaluation page). Failures in `docs/finals_field_notes.md` |

## What the team must build (kit section 5)

| Item | Status | Notes |
|---|---|---|
| 5.0 Data contract | ✅ | `docs/data_contract.md`; every lane reads and writes the same JSON paths in Blob |
| 5.1 Agency profile builder | ✅ / 👥 | Hand-built from the plan (the kit's shortcut), every goal cites a page. **Done when a teammate who didn't write it agrees it reflects the plan**: one teammate should read the Agency profile page and sign off |
| 5.2 Ingestion (daily) | ✅ | Broad pull + 40 keyword pulls, paging, retries, never crashes on one bad page; raw responses kept by date |
| 5.3 Normalize and de-duplicate | ✅ | Minimum schema, dates, days to close, closed/archived dropped, de-duplicated by number, incomplete records flagged not dropped |
| 5.4 Scoring and ranking | ✅ | Blended 0–100 (45/25/15/10/5 as the kit suggests), breakdown, best goal, High/Medium/Low. Semantic signal tuned (see Field Notes) |
| 5.5 AI summaries and rationales | ✅ / 👥 | Top 40 agency + top 5 research; "not stated" rule; quotes checked word for word. **Done when a teammate spot-checks 5 summaries against the listing** |
| 5.6 Staff-facing app | ✅ | Shortlist, filters (confidence, status, closing within N days, goal, division, decision, keyword), detail panel, decisions, CSV export, evaluation tab, "last refreshed" status |
| 5.7 Daily refresh job | ✅ | Container Apps Job, 6:00 AM Eastern, same image (MODE=job), idempotent, non-zero exit on failure, run log, alerts file |
| 5.8 Feedback loop (bonus) | ✅ | Evaluation page compares decisions with scores (Pass on High, Pursue on Low) |

## Evaluate (kit section 6)

| Step | Status |
|---|---|
| Pick 20–30 opportunities (top, middle, random) | ✅ The app draws ~30: our top 10, the keyword baseline's top 10, 5 middle, 5 random |
| Two teammates label without seeing the score | 👥 Evaluation → Label opportunities. Labels are blind and shuffled per person |
| Precision@10, recall, baseline comparison, coverage | ✅ Computed live on the Evaluation page as labels arrive |
| At least two failures, and what we changed | ✅ Field Notes: generic-text false positives from embeddings (fixed with off-topic anchors + hybrid), AI quote errors (caught by the checker) |

## Ideas to differentiate (kit 8.1)

| Idea | Status |
|---|---|
| "Missed by keyword search" counter | ✅ Evaluation page |
| Deadline radar (closing ≤10 days, new since yesterday) | ✅ Alerts on the shortlist |
| Goal heat map | ✅ "Funding by goal" page, with objectives that have no open funding highlighted |
| Forecasted watchlist | ✅ Status filter + forecast dates |
| Weight sliders in the UI | ❌ Not built; weights are in the config and shown on every record |
| Feedback-tuned weights | ❌ The decisions-vs-scores report is the first step; tuning is roadmap |
| Second agency profile | ✅ NC DEQ, plus a Statewide view across agencies |

## Deliverables (kit 7.3)

| Deliverable | Status |
|---|---|
| Working prototype on Azure (test on a phone hotspot) | ✅ / 👥 deployed and checked at phone width; someone should open it on a real phone |
| Backup: screen recording + screenshots in the slides | ✅ screenshots on slides 5–6 / 👥 record the live demo (script in the slide notes) |
| 6-minute deck | ✅ 12 slides with speaker notes (Slides artifact; download as PowerPoint or PDF). 👥 Fill the bracketed precision@10 and agreement numbers after labeling |
| Solution Design document | ✅ `docs/solution_design.pdf` (architecture, services, data contract, scoring, threats); full diagrams and threat model in `docs/diagrams/` |
| GenAI Field Notes | ✅ `docs/finals_field_notes.pdf` |
| Repository + README a state developer could pick up | ✅ `README.md`; pull request #10; the repository is public (history scanned: no keys or secrets) |
| No secrets in the repo | ✅ keys only as Container Apps secrets; `.env` ignored by git and by the image build |
| Stakeholder map (provided skill) | ✅ `docs/diagrams/ffm-stakeholder-map/report.html`. 👥 fill in "reviewed by" |

## Azure resources (team subscription `unc-sdis-solveathon-team14`, resource group `rg-ffm-team14`)

Blob Storage `stffm4817` · Azure OpenAI `aoai-ffm-4817` (`embed` = text-embedding-3-small, `chat` = gpt-4.1-mini) ·
Container Registry `acrffm4817` · Container Apps environment `cae-ffm` (+ Log Analytics) · web app `app-ffm-web` ·
job `job-ffm-refresh`. Estimated cost while running: about $2–3 a day, mostly the always-on web app. Delete after judging:
`bash deploy/99_teardown.sh`.

## From the challenge website (read after the starter kit)

| Website requirement | Status |
|---|---|
| Field notes: target user, their goals, and **what you learned from the sponsors that changed your plan** | 👥 Section 1 of `docs/solution_design.md` has a marked placeholder for the Discovery Session notes |
| Pitch to state leadership: could this win a **pilot budget from OSBM**? Centralized, statewide; smaller agencies | ✅ Two agencies, statewide view, OSBM-run pilot in the deck |
| Match on goals, **statutory authority** and program priorities | ⚠️ Goals and priorities done; statutory authority is a listed limitation |
| Submit slides, field notes and repository before 9 a.m. Sunday, with the product link | 👥 Form: Solve-a-thon Final Submission (needs a UNC sign-in) |
| Bonus: coverage metrics, deadline alerts, feedback loop | ✅ Missed-by-keyword counter, 10-day alerts, decisions-vs-scores report |
