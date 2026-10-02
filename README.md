# NC Solve-a-thon Grant Prioritization System

> ## 📌 Update log — read this first
>
> ### 2026-10-02: First real run; results, presentation notes, and fixes the results exposed (Pavan)
>
> **Results:** [`data/results/top_results.md`](data/results/top_results.md). **Presentation script and numbers:** [`docs/presentation_notes.md`](docs/presentation_notes.md). **Failures:** [`docs/failure_modes.md`](docs/failure_modes.md) (F1–F8).
>
> - **Run:** 1,662 grants → 359 removed by rules → **1,303 screened by Jev** (about a minute) → 283 to in-depth review → **270 analyzed by DeepSeek V4 Pro** with verified quotes (269/270 and 267/270 found word-for-word) → lists of **28 open program grants, 112 forecasts, 130 research partnerships**. Total AI cost **$3.23**. `python src/pipeline.py` now reproduces everything from `data/cache/` in **6 seconds with no API key**.
> - **Top results:** #1 open is Title X Family Planning (98/100). The watchlist leads with Ryan White HIV Part B / ADAP, MIECHV home visiting, drug-use infectious-disease prevention, and Preschool Development B-5. Two are flagged "may already be open, check Grants.gov now". The keyword baseline ranks Ryan White Part B **#670**.
> - **Layer 3 model changed** from Muse Spark to **DeepSeek V4 Pro**: Meta's provider blocked the account after 62 grants, treating HIV/STI/overdose grant text as policy violations (§13, F6). 13 low-priority grants weren't analyzed because the API key's $3 spending cap was reached; raise the cap and rerun `deep_analysis.py` to finish them (about $0.20).
> - **Fixes the results exposed:** NIH-style research awards now go to a separate research-partnerships list (F7; they had taken 7 of the first top 10); 17 administrative "award transfer" notices are hard-filtered (F8); Jev questions declare `type: choice` (the first real call returned HTTP 400).
> - **Still needed:** two people label `data/validation/labels.csv` (90 grants, blind), then `python src/validation.py evaluate` gives recall with a confidence interval. Also fill in the spot-check sheet `data/validation/spotcheck.csv`.
>
> ### 2026-09-30: Layers 0, 1 and 5 built; Layer 4 reviewed; one-command pipeline (Pavan)
>
> **Every layer now exists.** 43 tests pass (`python -m pytest tests -q`).
>
> | Layer | File | What it does |
> |---|---|---|
> | 0 | `src/clean_data.py` | _Superseded on 10-02 by Mayank's version, see §6._ |
> | 1 | `src/deterministic.py` | _Superseded on 10-02 by Mayank's version (with Pavan's additions), see §7._ |
> | 4 | `src/scoring.py` (Advik) | Reviewed: it fits Layers 1 and 3 as they stand. One change: it now **warns when grants with a failed Layer 3 analysis are left out of the ranking** instead of dropping them silently. |
> | 5 | `src/keyword_baseline.py`, `src/validation.py` | TF-IDF baseline; blind stratified labeling sheet; spot-check sheet; recall and precision with bootstrap CIs, compared against the baseline at the same review budget → `data/results/validation_report.md` |
> | — | `src/report.py`, `src/pipeline.py` | `top_results.md` (submission list with a one-line rationale per grant); `python src/pipeline.py` runs everything |
>
> `src/interim_layer01.py` has been deleted (see the entry below). Layer 2 now reads the real Layer 1 output.
>
> **Also fixed:** the model-cache hash now covers only the parts of `priorities.json` that are sent to a model. Tuning thresholds or Layer 4 weights no longer invalidates the cached answers.
>
> **To finish the submission:**
> 1. **Label now, no API key needed.** Open `data/validation/labels.csv` (90 grants). Two people each fill `labeler_A_relevant` / `labeler_B_relevant` with **Y/N**, independently. Y means "the coordinator should spend time on this: DHHS could lead or partner AND it advances a DHHS goal". Ignore deadline and award size. Where you disagree, agree on a `final_relevant`.
> 2. Put `AI_GATEWAY_API_KEY` in `.env` and run `python src/pipeline.py` (expected cost under $1). Commit `data/cache/` and `data/results/`.
> 3. `python src/validation.py spotcheck`: check the top 10 against our 5 criteria by hand.
> 4. `python src/validation.py evaluate`: produces the recall numbers and false negatives for the video. Record real failures in [`docs/failure_modes.md`](docs/failure_modes.md).
>
> **One open Layer 4 design question for the team:** `atypical` (technically eligible, but the program is designed for e.g. university researchers) gets full eligibility credit, because operational fit is supposed to capture that concern. Check in the spot-check that NIH-style research grants don't reach the top 10. If they do, lower `eligibility_confidence_by_verified_role.atypical` in `priorities.json`.
>
> ### 2026-09-29: Agency chosen, Layers 2–3 built, 8 plan changes (Pavan)
>
> **Agency: NC DHHS.** It has the largest realistic grant pool, and its strategic plan explicitly asks to maximize federal resources. User, criteria and rationale: [`agency/agency_profile.md`](agency/agency_profile.md). Goals, objectives and divisions: [`agency/priorities.json`](agency/priorities.json).
>
> **Layers 2 and 3 are implemented** (`src/semantic_triage.py`, `src/deep_analysis.py`, 23 tests in `tests/`). Until Layers 0–1 exist they read a temporary stand-in (`src/interim_layer01.py`, since removed in the 09-30 update).
>
> **What Layer 0/1 needs to produce:** `data/processed/grants_features.csv` with at least these columns: `grant_id` (= `opportunity_id`), `opportunity_title`, `agency_name`, `summary_description`, `applicant_types`, `applicant_eligibility_description`, `opportunity_assistance_listings`, `funding_instruments`, `is_forecast`, `hard_filtered` (bool). Once that file exists, Layer 2 uses it automatically and `interim_layer01.py` can be deleted.
>
> | # | Change | Why (from the data or rubric) | Who acts | Section |
> |---|---|---|---|---|
> | 1 | Layers 2–3 also predict the **owning DHHS division** and the **applicant role** (lead / partner / atypical / ineligible / unclear). | 609 of 689 NIH grants list "state governments", so structured eligibility can't tell us whether DHHS is the intended applicant. Routing to a division is also the user's actual job. | Done (L2/L3) | §11, §15 |
> | 2 | Layer 2 confidence = **Jev's per-option probabilities**, not a self-reported "confidence" number. | Jev's API returns a probability for every answer; self-reported LLM confidence is poorly calibrated. | Done (L2) | §12 |
> | 3 | Layer 3 must give **verbatim evidence quotes**, which Python checks against the grant text. Failures and Layer 2 vs 3 disagreements go to `ai_error_log.csv`. | The submission requires "one place the AI was wrong and how you caught it". This catches such cases automatically. | Done (L3) | §15 |
> | 4 | **Every model response is cached and committed.** Reruns need no API key. | "No paid tools required": judges can reproduce our ranking for free. | Done (L2/L3) | §32 |
> | 5 | **Forecast watchlist:** the 559 forecasted grants (34%) get their own "coming soon" list instead of a deadline penalty. | They have no close date. The challenge story says money goes "to states that found the posting first". | **Layer 1 + 4** | §7, §29 |
> | 6 | **Fixed `as_of_date`** (`2026-09-30`, in `priorities.json`) for all date math. | The data was pulled on 2026-08-18 and we submit on 09-30. Using "today" would change results between runs. | **Layer 1** | §7 |
> | 7 | **Stratified, blind validation labels**, with recall reported alongside a confidence interval. | Only about 5% of grants are relevant, so a random sample of 100 would contain about 5 relevant grants and give a meaningless recall estimate. | **Layer 5** | §21 |
> | 8 | **Keyword/TF-IDF baseline** kept as a *comparison*, not a feature. | "No bonus points for complexity that does not improve the matches." We need to show that Jev beats keyword matching. | **Layer 5** | §26 |
>
> Also for Layer 0: **1,040 of the 1,662 summaries contain raw HTML** (`<p>`, `&amp;`…). `src/text_utils.strip_html()` already handles it; reuse it.

## Overview

This project builds a reproducible grant-prioritization pipeline for the **North Carolina Department of Health and Human Services (NC DHHS)**.

> **Selected agency: NC DHHS.** User: the DHHS federal-grants coordinator. Details: [`agency/agency_profile.md`](agency/agency_profile.md).

The goal is not simply to find grants containing similar keywords. The system should answer a more useful decision-making question:

> **Given hundreds or thousands of federal grant opportunities, which grants are most worth this agency's limited time and attention?**

The system combines:

- deterministic filtering and feature engineering,
- fast semantic classification,
- deeper analysis for high-value or uncertain opportunities,
- transparent scoring,
- and human validation.

The qualifier implementation focuses on **one NC state agency, NC DHHS**, but the architecture is designed so the same pipeline could later be configured for another agency by replacing the agency profile, strategic priorities, and scoring criteria.

---

# 1. Problem Definition

Federal grant databases contain a large number of opportunities, but agency staff cannot realistically investigate every listing in depth.

A grant may appear relevant while actually being:

- closed,
- unavailable to state agencies,
- outside the agency's legal or operational responsibilities,
- poorly aligned with current strategic priorities,
- too small to justify the application effort,
- dependent on unrealistic cost sharing,
- or difficult to implement within the available timeline.

At the same time, simple filters can accidentally remove valuable opportunities.

The goal of this project is therefore to reduce the search space **without losing strong opportunities**, then rank the remaining grants according to their value for the selected agency.

---

# 2. Core Design Philosophy

The system separates different types of reasoning into different layers.

```text
RAW GRANTS
    |
    v
LAYER 0
Data Cleaning / Normalization
    |
    v
LAYER 1
Deterministic Checks
No semantic AI
    |
    v
LAYER 2
Fast Semantic Triage
Jev
    |
    v
LAYER 3
Deep Grant Evaluation
DeepSeek V4 Pro + Python evidence checks
    |
    v
LAYER 4
Transparent Scoring
Python formula
    |
    v
LAYER 5
Validation + Failure Analysis
Human review
    |
    v
FINAL RANKED GRANTS
```

Each layer has a different responsibility.

The system should avoid asking one model to make the entire decision from beginning to end.

---

# 3. Why Separate the Layers?

Separating the architecture provides several advantages.

### Auditability

We can identify exactly why a grant ranked highly or poorly.

### Reproducibility

The same grant and agency configuration should produce consistent structured results.

### Efficiency

Expensive reasoning is only used where it adds value.

### Error Detection

A bad decision in one layer can be inspected independently.

### Explainability

An agency employee should be able to understand the ranking without needing to understand machine learning.

---

# 4. Repository Structure

Project structure (✅ = exists now, others still to build):

```text
solveathon-grants/
│
├── README.md                     ✅
│
├── requirements.txt              ✅
│
├── .env.example                  ✅  (copy to .env, add AI_GATEWAY_API_KEY)
│
│
├── data/
│   ├── raw/
│   │   └── grants.csv            ✅  (starter-kit export, 1,662 grants)
│   ├── processed/
│   │   ├── grants_cleaned.csv    ✅  Layer 0
│   │   └── grants_features.csv   ✅  Layer 1 → input to Layers 2 and 4
│   ├── cache/                    ✅  every model response, committed (see §32)
│   ├── validation/
│   │   ├── labels.csv            ✅  blind labeling sheet (90 grants), filled in by the team
│   │   ├── sample_design.csv     ✅  strata and weights (hidden from labelers)
│   │   └── spotcheck.csv             top-10 / low-rank / deprioritized check sheet
│   └── results/
│       ├── keyword_baseline.csv  ✅  Layer 5 comparison
│       ├── jev_outputs.csv       ✅  Layer 2
│       ├── deep_analysis.csv     ✅  Layer 3
│       ├── ai_error_log.csv      ✅  Layer 3 checks: unverified quotes, L2/L3 disagreements
│       ├── ranked_grants.csv     ✅  Layer 4 open grants
│       ├── watchlist.csv         ✅  Layer 4 forecasted grants
│       ├── top_results.md / .csv ✅  submission list, one-line rationale per grant
│       └── validation_report.md  ✅  Layer 5 metrics
│
├── agency/
│   ├── agency_profile.md         ✅  user, criteria, why DHHS
│   └── priorities.json           ✅  goals, objectives, divisions, as_of_date, all layer settings
│
├── src/
│   ├── pipeline.py               ✅  runs everything: python src/pipeline.py [--mock]
│   ├── clean_data.py             ✅  Layer 0
│   ├── deterministic.py          ✅  Layer 1
│   ├── semantic_triage.py        ✅  Layer 2
│   ├── deep_analysis.py          ✅  Layer 3
│   ├── scoring.py                ✅  Layer 4 deterministic ranking
│   ├── keyword_baseline.py       ✅  Layer 5 baseline
│   ├── validation.py             ✅  Layer 5: sample / spotcheck / evaluate
│   ├── report.py                 ✅  top_results.md
│   ├── clients.py                ✅  Jev + Layer 3 chat-model API clients (+ mock clients)
│   ├── llm_cache.py              ✅
│   ├── text_utils.py             ✅  HTML stripping, verbatim-quote check
│   └── config.py                 ✅
│
├── tests/                        ✅  61 tests
│   ├── test_layer01.py           (Mayank)
│   ├── test_layers23.py
│   ├── test_scoring.py           (Advik)
│   ├── test_layer5.py
│   └── test_no_secrets.py        no API key can be committed
│
├── prompts/
│   ├── jev_triage.json           ✅
│   └── deep_analysis.txt         ✅
│
└── docs/
    ├── layer1_report.md          ✅  Layer 1 audit counts
    └── failure_modes.md          ✅  failure log
```

---

# 5. Agency Configuration

**Selected agency: NC Department of Health and Human Services (NCDHHS).** For the reasoning, the user and the draft criteria, see [`agency/agency_profile.md`](agency/agency_profile.md).

The pipeline does not hard-code agency-specific decisions into the Python source. Agency information is stored as configuration in [`agency/priorities.json`](agency/priorities.json):

```json
{
  "agency_name": "North Carolina Department of Health and Human Services (NCDHHS)",
  "mission": "... provides essential services to improve the health, safety, and well-being of all North Carolinians.",
  "user": "The NCDHHS federal-grants coordinator who ...",
  "as_of_date": "2026-09-30",

  "strategic_priorities": [
    {"id": "G1", "name": "Health Access", "objectives": [{"id": "G1.O1", "text": "..."}, "..."]},
    {"id": "G2", "name": "Child and Family Well-Being", "...": "..."},
    {"id": "G3", "name": "Behavioral Health and Resilience", "...": "..."},
    {"id": "G4", "name": "Strong and Inclusive Workforce", "...": "..."},
    {"id": "G5", "name": "Operational Excellence", "...": "..."}
  ],

  "divisions": [
    {"id": "DPH", "name": "Division of Public Health", "scope": "..."},
    {"id": "DMHDDSUS", "name": "Division of Mental Health, Developmental Disabilities and Substance Use Services", "scope": "..."},
    "... 13 divisions/offices in total"
  ],

  "layer2_routing": {"deprioritize_if_p_none_at_least": 0.85, "...": "..."}
}
```

The five goals and their 20 objectives come from the NCDHHS Strategic Plan 2023–2025.

This makes the underlying architecture reusable.

For another agency, we replace the agency configuration rather than rewriting the entire system.

---

# 6. Layer 0 — Data Cleaning and Normalization

## Purpose

Convert the raw grant dataset into a consistent machine-readable format.

This layer performs **no judgment about whether a grant is good or relevant**.

It only standardizes the data.

## Tasks

Examples include:

- convert dates into datetime objects,
- convert award amounts into numeric fields,
- normalize boolean fields,
- handle missing values,
- combine relevant text fields,
- create unique IDs,
- remove duplicate records,
- normalize applicant type strings,
- detect malformed or incomplete records.

## Example

```python
import pandas as pd

df = pd.read_csv("data/raw/grants.csv")

df["close_date"] = pd.to_datetime(
    df["close_date"],
    errors="coerce"
)

numeric_columns = [
    "award_floor",
    "award_ceiling",
    "estimated_total_program_funding"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

df["grant_text"] = (
    df["opportunity_title"].fillna("")
    + "\n"
    + df["summary_description"].fillna("")
    + "\n"
    + df["applicant_eligibility_description"].fillna("")
)
```

## Output

```text
data/processed/grants_cleaned.csv
```

> **Implemented: `python src/clean_data.py`** (Mayank's version, adopted 2026-10-02). Parses dates and numbers, normalizes booleans (a blank `is_cost_sharing` stays *unknown*, not False), drops duplicate ids (0 in this data), and adds `grant_id`, `summary_text` (HTML stripped; 1,040 summaries contain HTML) and `grant_text`. **The original text columns are kept byte-for-byte as exported**, so the prompts sent to Jev and the Layer 3 model are built from the original text and the cached answers stay valid even if the cleaning code changes. Zero and placeholder amounts are judged in Layer 1, not here.

---

# 7. Layer 1 — Deterministic Checks

## Purpose

Extract objective facts using ordinary Python.

This layer should contain **no semantic AI reasoning**.

If something can be determined directly from the data, it should be handled here rather than asking a model.

---

## Example Features

### Deadline

```text
days_until_close = close_date - as_of_date
```

> **Update (2026-09-29): use the fixed `as_of_date` from `agency/priorities.json` (`2026-09-30`), never `today()`.** The data was exported on 2026-08-18 and we submit on 2026-09-30. A fixed date gives the same result on every run and avoids recommending grants that closed before we submit.

> **Update (2026-09-29): forecasts are a separate track, not a missing deadline.** 559 of the 1,662 records (34%) have `is_forecast = True`. For these, `close_date` is always empty and `forecasted_close_date` / `forecasted_post_date` are usually filled. Do **not** hard-filter them or give them a zero deadline score. Add a `track` column (`open` / `forecast`). Layers 2–3 already triage both tracks, and Layer 4 should rank forecasts into a separate `watchlist.csv` ("prepare for these now").

Possible flags:

```text
expired
deadline_under_7_days
deadline_under_14_days
deadline_under_30_days
deadline_comfortable
```

---

### Funding

Extract:

```text
award_floor
award_ceiling
estimated_total_program_funding
expected_number_of_awards
```

Derived features could include:

```text
average_possible_award
funding_known
large_award
```

---

### Cost Sharing

Determine whether matching funds are required.

```text
requires_cost_share = True / False / Unknown
```

---

### Structured Eligibility

Read structured applicant categories.

Examples:

```text
state_government_listed
local_government_listed
universities_listed
nonprofits_listed
other_listed
```

IMPORTANT:

Structured eligibility should be considered a **signal**, not necessarily a final decision.

A grant should not automatically be removed simply because:

```text
state_government_listed == False
```

The detailed eligibility description may still allow the chosen agency.

---

### Missing Data

Flags such as:

```text
missing_description
missing_deadline
missing_award_amount
missing_eligibility_description
```

---

## Safe Hard Filters

Hard filtering should be conservative.

Examples of potentially safe removals:

```text
grant is already closed
grant status explicitly says cancelled
record is a duplicate
```

Most other characteristics should become features rather than immediate deletion rules.

> **Implemented: `python src/deterministic.py`** (Mayank's version, adopted 2026-10-02, plus three additions from Pavan's) → `data/processed/grants_features.csv` and the audit report [`docs/layer1_report.md`](docs/layer1_report.md). Settings live in `priorities.json → layer1`. Before writing, it checks its own output against the contract Layers 2 and 4 depend on, and stops if anything is wrong.
>
> - **Hard filters (342; rows stay in the file with a `hard_filter_reason`):** open grant closed before `as_of_date` (330); posted grant past its archive date (12, the "Funding Opportunity is Archived" records). Nothing else is filtered.
> - **`deadline_score`, 0–10:** piecewise-linear anchors (0 days → 0, 7 → 2, 14 → 4, 30 → 7, 60+ → 10). Blank for forecasts and for the 109 open grants with no real close date, so Layer 4's missing-deadline rule applies. Close dates in year 2090 or later are treated as placeholders (11). 66 of the 109 are flagged `rolling_deadline` ("proposals accepted anytime").
> - **`financial_value_score`, 0–10:** log scale from $100K → 0 to $10M → 10, on the award ceiling, else total funding ÷ expected awards, else total funding (capped at 7, because a program total is not one applicant's award). An unknown amount (580 grants) scores 5. Zero amounts (114 rows) and sentinel amounts ($999,999,999, 2^31, 9,999 awards; 3 rows) are treated as placeholders, not money.
> - **Forecast track:** `forecast_close_passed` (234 stale forecasts), `forecast_check_now` (88 forecasts whose post date has passed, so they may already be open: "check Grants.gov now").
> - **Signals, never filters:** structured applicant flags, `broad_eligibility` (694 grants list 12 or more applicant types), text checks for tribal-, university- or individuals-only eligibility, cost-sharing percentage parsed from text, HHS assistance listings (93.x), and possible reposts.
>
> Result: **1,320 grants go to Layer 2 (761 open, 559 forecast).**

---

# 8. Why Layer 1 Should Be Conservative

The largest risk in early filtering is a **false negative**.

Example:

```text
A genuinely valuable grant
        |
        v
incorrectly rejected in Layer 1
        |
        v
never analyzed again
```

That error is much worse than allowing an irrelevant grant through.

Therefore the early pipeline should prioritize:

> **Recall over precision.**

It is acceptable for Layer 2 to receive extra irrelevant opportunities.

It is not acceptable for Layer 1 to silently eliminate excellent opportunities.

---

# 9. Layer 2 — Fast Semantic Triage

## Tool

Jev (`typesafe-ai/jev`, via the Vercel AI Gateway `/v1/evaluate` endpoint). **Implemented in `src/semantic_triage.py`.**

```bash
python src/semantic_triage.py           # real run: needs AI_GATEWAY_API_KEY, or a filled cache
python src/semantic_triage.py --mock    # dry run with fake answers (outputs go to data/results/mock/)
```

## Purpose

Layer 2 handles questions that require understanding meaning rather than simply reading structured fields.

Examples:

- Is the grant related to the agency's responsibilities?
- Which strategic priority does it align with?
- Is the connection strong or superficial?
- Does free-text eligibility appear to include the agency?
- Is the opportunity clearly irrelevant?
- Is the result uncertain enough to require deeper review?

---

# 10. Why Jev Fits This Layer

Jev is intended for fast structured classification and decision tasks.

Instead of asking it to generate long explanations, the system asks for a small number of structured outputs.

Jev does not take a free-form prompt. It takes a structured **`state`** (the facts) plus typed **`choice` questions**, each with a fixed set of options, and it answers every question in one round trip. **For each question it returns a probability for every option.**

Input `state` (built per grant in `grant_state()`):

```json
{
  "task": "You are triaging federal grant opportunities for NCDHHS. Mission: ... The person using these results is ...",
  "grant": {
    "title": "...", "federal_agency": "...", "assistance_listings": "93.243|...",
    "funding_instruments": "...", "applicant_types": "...",
    "eligibility_text": "...", "summary": "... (HTML stripped, ≤3,000 chars)"
  }
}
```

The questions are stored in [`prompts/jev_triage.json`](prompts/jev_triage.json); goal and division options are filled from `priorities.json`.

---

# 11. Layer 2 Outputs

The semantic triage layer should avoid producing one unexplained final score.

Instead, it produces multiple independent signals.

**Implemented questions** (all `choice`, each returning a probability per option):

| Question | Options | Why |
|---|---|---|
| `domain_relevance` | none / weak / moderate / strong | Is the *funded activity* DHHS's kind of work? |
| `matched_goal` | G1–G5 / none | Which strategic goal it advances |
| `applicant_role` | lead / partner / atypical / ineligible / unclear | Replaces the earlier "eligibility" field. "Atypical" means technically eligible but designed for someone else (e.g. an NIH R01 grant that lists every applicant type) |
| `owning_division` | 13 DHHS divisions / none | Who would own the application: the coordinator's routing decision |

> **Update (2026-09-29).** We dropped `confidence` (a self-reported number is poorly calibrated) and `implementation_fit` (Layer 3 judges operational fit with evidence). We added `applicant_role` and `owning_division`.

Output `data/results/jev_outputs.csv`, one row per grant:

```text
grant_id, opportunity_title, track (open/forecast),
domain_relevance, domain_relevance_p, domain_relevance_probs (JSON of all options),
matched_goal,  matched_goal_p,  matched_goal_probs,
applicant_role, applicant_role_p, applicant_role_probs,
owning_division, owning_division_p, owning_division_probs,
expected_relevance      # none=0, weak=1/3, moderate=2/3, strong=1, weighted by probability
p_lead_or_partner
triage_priority         # expected_relevance × (0.5 + 0.5 × p_lead_or_partner); orders the Layer 3 queue only
route, route_reason     # deep_review / deprioritized
model, prompt_version, from_cache
```

---

# 12. Confidence-Aware Routing

Jev should not simply decide:

```text
KEEP
or
DELETE
```

Instead, confidence should determine what happens next.

Example:

```text
Strong relevance + high confidence
          |
          v
      Deep Review

Moderate relevance
          |
          v
      Deep Review

Low confidence
          |
          v
      Deep Review

Strong irrelevance + extremely high confidence
          |
          v
     Deprioritized
```

The system should preserve deprioritized grants so they can later be sampled during validation.

> **Update (2026-09-29): confidence = Jev's own probabilities.** A grant is deprioritized **only** if one of these holds (cutoffs are in `priorities.json → layer2_routing`):
>
> ```text
> P(domain_relevance = none)          ≥ 0.85
> P(domain_relevance ∈ {none, weak})  ≥ 0.95
> P(applicant_role = ineligible)      ≥ 0.90
> ```
>
> Everything else goes to Layer 3, including every uncertain case. These cutoffs are deliberately conservative starting values. **Layer 5 should tune them on the labeled sample** to hit a recall target (e.g. ≥ 95% of human-labeled relevant grants reach Layer 3). If Jev's answer is missing, the grant goes to deep review and is never dropped.

---

# 13. Layer 3 — Deep Evaluation

## Purpose

Layer 3 performs more careful analysis on grants that are:

- highly promising,
- ambiguous,
- high-value,
- or uncertain.

This layer may use:

- a stronger general-purpose language model,
- detailed manual analysis,
- or a combination of both.

> **Implemented in `src/deep_analysis.py`.** **Model: DeepSeek V4 Pro** (`deepseek/deepseek-v4-pro`, via the Vercel AI Gateway's OpenAI-compatible chat endpoint, temperature 0). It runs on every grant Layer 2 routes to `deep_review`, highest `triage_priority` first. `layer3.max_grants` in `priorities.json` can cap it; grants over the cap are logged, never silently dropped. The model is a single setting (`DEEP_MODEL` in `src/config.py` or `.env`).
>
> **Why not Muse Spark, the original plan (2026-10-02).** We started on Meta's cheap Muse Spark 1.3 "contributor" model. After 62 of 298 grants, Meta's provider **restricted the account for "repeated policy violations"**. The inputs were ordinary public Grants.gov text, but DHHS grants routinely discuss HIV, STIs, sexual violence and overdoses, and the provider's safety filter evidently treated that as a violation. We chose a replacement by testing three affordable models on the 8 most sensitive grants Muse had already analyzed:
>
> | Model | Valid JSON | Quotes verified | Agreement with Muse (role / division) | Est. cost, 298 grants |
> |---|---|---|---|---|
> | **DeepSeek V4 Pro (chosen)** | 8/8 | 8/8 | **100% / 100%** | ~$2.50 |
> | DeepSeek V4 Flash | 8/8 | 8/8 | 88% / 100% | ~$0.30 |
> | GLM 5.3 Flash | 8/8 | 7/8 | 88% / 100% | ~$0.20 |
>
> None refused the sensitive grants. The 62 Muse answers stay in `data/cache/layer3_deep/` as a cross-model check (see `docs/presentation_notes.md`). Lesson for a real deployment: **a public-health agency's normal subject matter can trip a commercial model's safety filter**, so the pipeline must be able to swap models. This one could, because the model is a single setting and the results were cached.
>
> ```bash
> python src/deep_analysis.py           # real run (reads data/results/jev_outputs.csv)
> python src/deep_analysis.py --mock    # dry run on mock Layer 2 output
> ```

The purpose is not to reprocess all grants.

It should examine only a smaller candidate set.

Example:

```text
1,662 grants
    |
    v
1,300 after objective cleanup
    |
    v
200 potentially relevant after semantic triage
    |
    v
40–75 grants receive deep analysis
    |
    v
Top 10–20 recommendations
```

Exact numbers will depend on the chosen agency and dataset.

---

# 14. Questions for Deep Evaluation

The deeper analysis should answer more sophisticated questions.

### Strategic Evidence

What specific agency priority does this grant support?

### Eligibility

What text specifically indicates the agency can or cannot apply?

### Operational Fit

Could the agency realistically administer the program?

### Funding Value

Does the potential financial return justify the application effort?

### Deadline Feasibility

Can the agency realistically prepare an application?

### Restrictions

Are there:

- matching requirements,
- partnership requirements,
- geographic restrictions,
- special applicant conditions,
- unusual reporting requirements?

### Risks

What could make this grant less valuable than it initially appears?

---

# 15. Evidence Extraction

A major goal of Layer 3 should be to generate evidence, not just opinions.

**Implemented output schema** (prompt: [`prompts/deep_analysis.txt`](prompts/deep_analysis.txt)):

```json
{
  "strategic_alignment": 9,
  "matched_goal": "G3",
  "matched_objective": "G3.O4",
  "strategic_reason": "Funds medication treatment for opioid use disorder, a named G3 strategy.",
  "strategic_evidence_quote": "<copied verbatim from the grant summary>",

  "applicant_role": "lead",
  "eligibility_evidence_quote": "<copied verbatim from the eligibility text>",
  "owning_division": "DMHDDSUS",

  "operational_fit": 8,
  "operational_reason": "...",
  "restrictions": ["cost sharing 20%", "..."],
  "major_risk": "...",
  "recommended_for_review": true,
  "one_line_rationale": "≤30 words for the budget director (used in the submitted top-results list)"
}
```

> **Update (2026-09-29): deadlines and award size were removed from Layer 3.** `deadline_feasibility` and financial value are objective, so Layer 1 computes them and Layer 4 scores them. The model only judges what requires reading.

## Python checks on the model's answers (the "caught the AI being wrong" mechanism)

Every Layer 3 answer is checked before anyone trusts it. Every failure is written to **`data/results/ai_error_log.csv`**:

| Check | What happens |
|---|---|
| **Verbatim quotes**: each quote must appear in the grant text (ignoring case, whitespace, HTML, curly quotes; `...` fragments must appear in order) | `strategic_quote_verified` / `eligibility_quote_verified` columns. If the model claims `lead`/`partner` but its eligibility quote isn't in the text, **`applicant_role_verified` is downgraded to `unclear`** |
| **Schema validation**: scores 0–10, goal/objective/division ids exist in `priorities.json`, objective belongs to the goal | One automatic retry that tells the model what was wrong; if the answer is still invalid, the grant is marked `invalid_output` |
| **Layer 2 vs Layer 3 disagreement** | Jev said none/weak but Layer 3 scored alignment ≥ 7 (**a possible Layer 2 false negative**); Jev said strong but Layer 3 scored ≤ 3; role or division mismatch |

Layer 4 should score from the **verified** fields (`applicant_role_verified`, and penalize `strategic_quote_verified = False`). The error log feeds `docs/failure_modes.md` and the "where the AI was wrong" part of the submission.

---

# 16. Layer 4 — Transparent Scoring

## Key Principle

The AI should produce structured judgments.

**Python should calculate the final ranking.**

This keeps the ranking transparent and reproducible.

We should avoid:

```text
"LLM, rank all grants from best to worst."
```

Instead:

```text
AI -> features
Python -> final score
```

---

# 17. Scoring Framework

**Implemented in `src/scoring.py`.** The final ranking is deterministic: AI supplies structured judgments, Layer 1 supplies objective features, and Python applies fixed weights from `agency/priorities.json → layer4_scoring`.

```text
Strategic Alignment       30%
Operational Fit           25%
Financial Value           15%
Deadline Feasibility      15%
Eligibility Confidence    15%
                          ----
                          100%
```

Strategic alignment and operational fit carry **55% together** because the first question is whether a grant meaningfully advances NCDHHS priorities and can realistically be administered. Financial value, deadline feasibility, and eligibility confidence remain material without overpowering mission fit.

```python
final_score = (
    strategic_alignment * 0.30
    + operational_fit * 0.25
    + financial_value_score * 0.15
    + deadline_score * 0.15
    + eligibility_confidence_score * 0.15
)
```

Scores are reported on a **0–100 scale**.

### Missing deadline rule

A missing deadline is not treated as a zero. For an **open** grant with no deadline in the dataset, Layer 4 drops the deadline component, re-normalizes the remaining 85% of available weight, then subtracts a **3-point uncertainty penalty** from the 100-point score. This means a perfect grant with a known feasible deadline scores 100, while an otherwise perfect open grant with an unknown deadline scores 97.

Forecast grants are different: they are expected to lack a normal close date. Layer 4 drops the deadline component, re-normalizes the other criteria, applies **no missing-deadline penalty**, and sends them to `watchlist.csv`.

**Rolling deadlines (added 2026-10-02).** "Proposals accepted anytime" is a *known, flexible* deadline, not an unknown one, so it has its own penalty settings in `priorities.json → layer4_scoring`:

| Kind of open grant with no close date | Count | Penalty | Why |
|---|---:|---:|---|
| Deadline genuinely unknown | 31 | −3 | uncertainty |
| Rolling, no time pressure (mostly NSF "accepted anytime") | 57 | −2 | flexible, so a similar grant with a real deadline should be handled first |
| Rolling but **first come, first served** ("until all available funds have been expended", "processed as received"; all EDA) | 9 | 0 | no real flexibility, since the money can run out. Flagged in the report as "apply early" |

Effect (tested in `tests/test_scoring.py`): a rolling grant ranks **below** an otherwise-similar grant with a workable deadline (81.5 vs 86) but **above** a slightly weaker grant that has a comfortable deadline (79). Rolling grants are never filtered out; they go through Jev and the deep analysis like every other grant.

### Evidence rule

Layer 4 uses Layer 3's evidence-checked fields. If the strategic evidence quote could not be verified against the grant text, Layer 4 subtracts a configurable **5-point evidence penalty** rather than silently trusting the model's strategic score.

---

# 18. Eligibility as a Gate

Eligibility has special treatment.

Layer 4 uses the **verified applicant role and verified eligibility quote** from Layer 3. `lead`, `partner`, and `atypical` all receive full eligibility-confidence credit when the evidence is verified; whether NCDHHS is a natural lead applicant is already reflected in operational fit and should not be double-penalized. `unclear` receives partial credit.

If a grant is confirmed with verified evidence to be legally unavailable to the agency, its financial or strategic attractiveness becomes irrelevant.

Therefore:

```text
Confirmed ineligible
        |
        v
Final score = 0
```

However:

```text
Eligibility uncertain
        |
        v
Do NOT automatically reject
```

Uncertain eligibility should trigger deeper review.

---

# 19. Example Scoring Breakdown

```text
Grant:
Federal Education Data Infrastructure Program

Strategic Alignment          9/10
Operational Fit              8/10
Financial Value              8/10
Deadline Feasibility         7/10
Eligibility Confidence      10/10

Final Score:
84.5 / 100
```

Output explanation:

```text
Strong alignment with the agency's data modernization strategy,
explicit state-agency eligibility, significant potential funding,
and realistic implementation scope.
```

---

# 20. Layer 5 — Validation

Validation is a core part of the project.

We should not assume the system works merely because the outputs look reasonable.

The pipeline should be manually tested.

> **Implemented (2026-09-30): `src/validation.py`**, three commands:
>
> ```bash
> python src/validation.py sample      # blind stratified labeling sheet (already generated: data/validation/labels.csv)
> python src/validation.py spotcheck   # after the real run: top 10, top 5 watchlist, 5 low-ranked, 5 deprioritized
> python src/validation.py evaluate    # → data/results/validation_report.md
> ```
>
> - **Sample design:** 90 grants drawn from the 1,320 that reach Layer 2. Three strata by **keyword-baseline rank**: top 100, ranks 101–400, and 401+, with 30 from each and a fixed seed. Strata come from the baseline, not from Jev, so the sample doesn't depend on the model being evaluated and can be labeled **before** any API run. The sheet is shuffled and shows no stratum or model output. `sample` refuses to overwrite a sheet that already has labels.
> - **The label:** "Should the coordinator spend time on this?" Y means DHHS could lead or partner AND the grant advances a DHHS goal. Deadline and award size are excluded; they're handled deterministically.
> - **`evaluate` reports:** inter-labeler agreement (Cohen's κ); Layer 2 recall and precision **weighted by stratum size**, with 95% stratified-bootstrap intervals; the keyword baseline given **the same review budget** (its top-K, where K = the number Jev sends to deep review); every Layer 2 false negative; Layer 3 `recommended_for_review` vs the labels; and a summary of the AI error log.

---

# 21. Validation Sample

Create a manually reviewed sample of grants.

For example:

```text
100–150 randomly selected grants
```

> **Update (2026-09-29): stratify the sample, and label blind.** Only about 5% of grants are relevant to DHHS, so a purely random sample of 100 contains about 5 relevant grants. A recall estimate from 5 grants is meaningless: finding 4 of 5 gives a 95% confidence interval of about 38–96%. Instead:
>
> 1. **Stratify** (for example: 40 from Layer 2's `deep_review` set with high `triage_priority`, 40 from lower-priority `deep_review`, 40 from `deprioritized`, 20 from the hard-filtered set) and weight by stratum size when estimating recall.
> 2. **Label blind.** Two teammates label each grant using only the grant text and our criteria, *before* looking at any model output. Record where the two labelers disagree; that's our measure of how ambiguous the task is.
> 3. **Report recall with a confidence interval** (e.g. Wilson interval), not a single number.
> 4. The `deprioritized` stratum is where Layer 2 false negatives hide. Look at every "relevant" label found there.

Each grant receives a human label.

Example:

```text
Grant A
Human: Relevant
Jev: Relevant
Result: Correct

Grant B
Human: Irrelevant
Jev: Irrelevant
Result: Correct

Grant C
Human: Relevant
Jev: Irrelevant
Result: False Negative
```

---

# 22. Metrics

Because the first semantic layer is primarily used to prevent missed opportunities, the most important metric may be:

## Recall

```text
Relevant grants correctly retained
----------------------------------
All actually relevant grants
```

Example:

```text
Actual relevant grants: 30
System retained:         29

Recall = 29 / 30 = 96.7%
```

---

## Precision

```text
Actually relevant retained grants
---------------------------------
All grants retained
```

Precision is useful but less critical during early triage.

---

## False Negative Rate

Especially important:

```text
Good grants accidentally rejected
---------------------------------
All good grants
```

We should explicitly examine false negatives.

---

# 23. Why Recall Matters More Than Accuracy

Imagine:

```text
1,500 irrelevant grants
100 relevant grants
```

A model that simply marks everything irrelevant would achieve:

```text
93.75% accuracy
```

but would be completely useless.

Therefore overall accuracy is not enough.

We care much more about whether the pipeline successfully preserves valuable opportunities.

---

# 24. Failure Analysis

The submission should intentionally document examples where the system fails.

Potential failure modes include:

### Structured Eligibility Errors

The dataset may label:

```text
applicant_type = other
```

while the detailed eligibility text explicitly includes state agencies.

### Semantic Ambiguity

A grant may use language different from the agency strategic plan but still support the same objective.

Example:

```text
Agency:
"grow the Direct Care workforce" (DHHS G4.O1)

Grant:
"training and retaining home health aides and personal care assistants"
```

### Broad Grant Descriptions

Some opportunities may sound relevant but only apply to a narrow program outside the agency's authority.

### Missing Information

Some grants may omit critical award or eligibility information.

### Deadline Distortion

An excellent grant might score highly despite having too little time to realistically apply.

### Large-Dollar Bias

A large award should not automatically outrank a smaller but much better-aligned opportunity.

---

# 25. Failure Log

We should maintain:

```text
docs/failure_modes.md
```

Each discovered failure should contain:

```text
Grant ID:
Observed error:
Why the system made the error:
How we detected it:
Whether we changed the pipeline:
What tradeoff the fix introduced:
```

---

# 26. Optional Lexical Similarity Layer

If useful, we may add a lightweight non-generative NLP signal using:

- TF-IDF,
- BM25,
- or another lexical retrieval method.

This would not replace Jev.

Instead it could provide another independent relevance signal.

Example:

```text
Agency strategic plan
        |
        v
TF-IDF representation

Grant description
        |
        v
TF-IDF representation

        |
        v
Cosine similarity
```

Advantages:

- very fast,
- reproducible,
- no API dependency,
- easy to explain.

Limitation:

Lexical matching does not always understand synonyms or deeper semantic meaning.

Therefore it should remain a supporting feature rather than the primary semantic classifier.

> **Update (2026-09-29): build this as a baseline to compare against, not as a feature** (`src/keyword_baseline.py`, Layer 5). Rank all grants by TF-IDF similarity to the strategic-plan text. On the labeled sample, compare its recall and precision against Jev's routing. The rubric gives "no bonus points for complexity that does not improve the matches", so this comparison is our evidence that the AI layer earns its place. If the baseline turns out to be as good, that's an honest finding and worth reporting too.

---

# 27. Why We Are Not Starting With Embeddings

Embeddings could be useful, but they are not automatically necessary.

The dataset contains only a relatively small number of grants.

Adding:

```text
TF-IDF
+ embeddings
+ Jev
+ another LLM
+ custom ranking
```

may increase system complexity without improving recommendations.

The initial architecture will prioritize the simplest pipeline that performs well.

Embeddings can be added later if validation shows that the semantic triage layer is missing important conceptual matches.

---

# 28. Proposed Full Pipeline

```text
                     GRANTS.GOV DATA
                           |
                           v
                 DATA CLEANING
                           |
                           v
              DETERMINISTIC FEATURES
                           |
       +-------------------+-------------------+
       |                                       |
       v                                       v
 expired/cancelled                       viable records
       |                                       |
       v                                       v
 archive                               JEV SEMANTIC TRIAGE
                                               |
                         +---------------------+--------------------+
                         |                     |                    |
                         v                     v                    v
                clearly irrelevant        uncertain            relevant
                         |                     |                    |
                         v                     +---------+----------+
                  deprioritized                         |
                                                       v
                                                DEEP ANALYSIS
                                                       |
                                                       v
                                             STRUCTURED FEATURES
                                                       |
                                                       v
                                              PYTHON SCORING
                                                       |
                                                       v
                                                RANKED RESULTS
                                                       |
                                                       v
                                             HUMAN VALIDATION
                                                       |
                                                       v
                                                FINAL TOP 10
```

---

# 29. Final Grant Output

The primary final output should be a ranked table.

Example:

| Rank | Grant | Score | Deadline | Max Award | Priority Match | Main Risk | Why It Matches |
|---|---|---:|---|---:|---|---|---|
| 1 | Grant A | 91 | Oct. 30 | $2.5M | Data Modernization | Short deadline | Strong strategic and operational fit |
| 2 | Grant B | 88 | Dec. 1 | $1.2M | Workforce | Cost sharing | Directly supports educator retention |
| 3 | Grant C | 85 | Nov. 15 | $5M | Technology | Complex implementation | Strong statewide infrastructure potential |

The final ranked file may be stored as:

```text
data/results/ranked_grants.csv
```

> **Update (2026-09-29): two lists, not one.**
>
> - **Top open opportunities** (`ranked_grants.csv`): grants you can apply for now.
> - **Watchlist** (`watchlist.csv`): the best *forecasted* grants, ranked on the same criteria except deadline, with the forecasted post/close dates. The message to the user is "start preparing now; these open soon." This is the "find it first" advantage from the challenge brief.
>
> Every row also carries the **owning division** and a **verified eligibility quote**, so the coordinator knows who to forward it to and why we believe DHHS can apply.

---

# 30. Recommended Output Fields

Each final grant should include:

```text
rank
grant_id
grant_title
federal_agency
deadline
days_until_close
award_floor
award_ceiling
cost_sharing
eligibility_status
strategic_priority
strategic_alignment
operational_fit
financial_value_score
deadline_score
eligibility_confidence_score
missing_deadline_penalty
strategic_evidence_penalty
score_status
final_score
reason
main_risk
source_url
```

---

# 31. Explainability

Every recommended grant should answer:

```text
Why is this here?
```

A user should not need to inspect code or AI prompts to understand the recommendation.

Example:

```text
Rank #2

Why:
The grant directly supports the agency's statewide data modernization
priority, explicitly allows state education agencies to apply, provides
up to $1.2M in funding, and does not require cost sharing.

Main concern:
The application deadline is only 24 days away.
```

---

# 32. Reproducibility

Running:

```bash
python src/pipeline.py
```

should eventually reproduce the final ranking from:

```text
raw grants
+
agency configuration
+
stored prompts
+
scoring weights
```

> **Update (2026-09-29): model responses are cached and committed.** Every Jev and Layer 3 model response is saved in `data/cache/<layer>/` as JSON, together with the model id, prompt-version hash, request hash and retrieval time. On a rerun, the pipeline reads the cache instead of calling the API, so **anyone (including judges) can reproduce our exact ranking with no API key and no cost.** Editing a prompt or `priorities.json` changes the hash, and only the affected calls are re-run. `--mock` runs write to `data/cache_mock/` and `data/results/mock/`, which are git-ignored and can never be mixed with real results.

Important parameters should not be hidden inside notebooks.

They should be stored in:

```text
config files
environment variables
or clearly documented constants
```

---

# 33. AI Transparency

Any use of generative AI or semantic models should be documented.

For every model we should record:

```text
Model:
Purpose:
Input fields:
Output schema:
Prompt:
Confidence handling:
Known limitations:
```

Prompt templates should be stored under:

```text
/prompts
```

rather than buried inside Python scripts.

---

# 34. Example AI Documentation

```text
Tool:
Jev (typesafe-ai/jev), Vercel AI Gateway /v1/evaluate

Purpose:
Initial semantic grant triage.

Input:
Agency mission and user (from priorities.json)
Grant title, federal agency, assistance listings, funding instrument
Structured applicant types
Eligibility text, summary (HTML stripped, ≤3,000 chars)

Output (4 choice questions, probability for every option):
Domain relevance
Matched strategic goal
Applicant role (lead / partner / atypical / ineligible / unclear)
Owning DHHS division

Confidence handling:
Jev's own per-option probabilities. Deprioritize only above conservative
cutoffs; everything uncertain goes to Layer 3.

Decision authority:
Jev does not produce the final ranking.

Final scoring:
Performed deterministically in Python.
```

---

# 35. Deep Model Documentation

If a stronger language model is used for Layer 3:

```text
Model:
DeepSeek V4 Pro (deepseek/deepseek-v4-pro), Vercel AI Gateway, temperature 0.
Replaced Muse Spark 1.3 contributor after Meta's provider blocked the account
(safety filter vs. HIV/STI/overdose grant text; see Section 13). Every input is
public Grants.gov and strategic-plan text.

Output checks:
Verbatim-quote verification, schema validation with one retry,
Layer 2 vs Layer 3 disagreement log → data/results/ai_error_log.csv

Purpose:
Analyze difficult or highly ranked candidate grants.

The model may extract:
- eligibility evidence,
- strategic-plan evidence,
- implementation concerns,
- funding restrictions,
- risks,
- recommendation rationale.

The model should not independently determine the final ranking.
```

---

# 36. Human Review

The final system is intended as:

> **Decision support, not automated decision replacement.**

The recommended workflow for an agency employee would be:

```text
System processes grants
        |
        v
System returns top opportunities
        |
        v
Employee reviews evidence and risks
        |
        v
Employee decides whether to investigate/apply
```

---

# 37. Potential Future Interface

If time allows, the pipeline could later be wrapped in a simple interface.

Possible options:

- Streamlit,
- Flask,
- React frontend,
- command-line application,
- scheduled report generator.

Example user workflow:

```text
Select Agency
      |
      v
Run Grant Search
      |
      v
See Ranked Opportunities
      |
      v
Click Grant
      |
      v
See:
- why it matched
- strategic priority
- funding
- deadline
- eligibility
- risks
```

The UI is optional.

The ranking methodology is the core project.

---

# 38. Evaluation Questions

During development we should repeatedly ask:

### Understanding

Do we understand what the selected agency actually does?

### Framing

Do our criteria reflect what would make a grant valuable to this specific agency?

### Solving

Does the architecture reliably surface relevant opportunities?

### Evaluating

Do we know where the system fails?

### Impact

Would an actual agency employee save time by using this?

---

# 39. Development Plan

## Phase 1 — Agency Selection

- inspect candidate agency strategic plans,
- compare agency priorities against the grant dataset,
- choose an agency with meaningful available opportunities,
- identify the hypothetical end user.

---

## Phase 2 — Define Success Criteria

Create 3–5 clear agency-specific evaluation criteria.

Possible examples:

```text
Eligibility
Strategic Alignment
Operational Fit
Financial Value
Deadline Feasibility
```

Determine which criteria are:

```text
hard gates
vs.
weighted scores
```

---

## Phase 3 — Build Data Pipeline

Implement:

```text
clean_data.py
deterministic.py
```

Generate objective grant features.

---

## Phase 4 — Implement Jev Triage

Implement:

```text
semantic_triage.py
```

Create structured outputs and confidence-aware routing.

---

## Phase 5 — Validate Jev

Manually label a sample of grants.

Measure:

```text
recall
precision
false negatives
```

Adjust routing thresholds based on results.

---

## Phase 6 — Deep Analysis

Run deeper analysis only on promising or uncertain candidates.

Store structured evidence.

---

## Phase 7 — Final Scoring

Implement:

```text
scoring.py
```

Finalize weights and generate rankings.

---

## Phase 8 — Human Validation

Review:

```text
top-ranked grants
middle-ranked grants
bottom-ranked grants
random rejected grants
```

Look especially for missed strong opportunities.

---

## Phase 9 — Failure Analysis

Document at least one meaningful failure.

Ideally several.

---

## Phase 10 — Presentation

Build the 5-minute story around:

```text
Problem
↓
Agency/User
↓
Definition of good grant
↓
Architecture
↓
Top results
↓
Validation
↓
Failure
↓
Impact
```

---

# 40. Presentation Narrative

A possible final pitch:

> State agencies face thousands of grant opportunities but limited staff time to evaluate them.
>
> We built a grant prioritization system for [AGENCY] that combines deterministic filtering, fast semantic triage, deeper analysis, and transparent scoring.
>
> Rather than asking an AI model to choose grants directly, the system separates objective facts from semantic judgments and uses a reproducible scoring framework.
>
> The system reduces the original grant dataset to a small set of high-priority opportunities while preserving uncertain cases for deeper review.
>
> We manually validated the recommendations and specifically tested for false negatives.
>
> We also identified cases where structured Grants.gov eligibility fields were incomplete, demonstrating why simple filtering alone is insufficient.
>
> The final result is not an automated grant-selection system. It is a decision-support tool that helps agency employees determine where to spend their limited review time.

---

# 41. Key Project Principle

The project should optimize for:

> **Finding valuable grants without hiding why they were selected.**

Not:

> **Building the most complicated AI system possible.**

A strong submission should demonstrate:

```text
good agency understanding
+
good data engineering
+
appropriate semantic reasoning
+
transparent decision logic
+
real validation
+
honest failure analysis
```

---

# 42. Current Proposed Stack

### Language

```text
Python
```

### Data

```text
pandas
numpy
```

### Deterministic Analysis

```text
Python
pandas
```

### Optional Lexical Matching

```text
scikit-learn TF-IDF
```

### Fast Semantic Triage

```text
Jev
```

### Deep Analysis

```text
DeepSeek V4 Pro (Vercel AI Gateway) + Python evidence checks
```

### Final Ranking

```text
Python
```

### Validation

```text
pandas
scikit-learn metrics
manual labeling
```

### Optional Interface

```text
Streamlit
```

---

# 43. Important Design Decisions Still To Make

Before implementation is finalized:

- [x] Choose the target NC agency. → **NCDHHS**
- [x] Define the target agency employee/user. → **DHHS federal-grants coordinator** (draft, `agency/agency_profile.md`)
- [x] Extract strategic priorities. → 5 goals, 20 objectives, 13 divisions in `priorities.json`
- [ ] Finalize 3–5 grant evaluation criteria. (draft in `agency/agency_profile.md`; team to confirm)
- [x] Determine hard filters. → closed or archived before `as_of_date` only (§7)
- [x] Determine scoring weights. → Layer 4, `priorities.json → layer4_scoring` (§17)
- [x] Define Jev output schema. → §11
- [ ] Determine Jev confidence thresholds. (conservative defaults set; tune on labeled sample)
- [ ] Decide whether TF-IDF improves performance. (baseline built; `validation.py evaluate` answers this once labels exist)
- [x] Choose the deep-analysis model. → DeepSeek V4 Pro (Muse Spark was blocked; §13)
- [x] Create a validation sample. → `data/validation/labels.csv`, 90 grants, stratified + blind (§20)
- [ ] **Label the validation sample** (two labelers, Y/N)
- [ ] Run Layers 2–3 for real once `AI_GATEWAY_API_KEY` is in `.env`, and commit `data/cache/`.
- [ ] Determine the final number of grants shown.
- [ ] Build the presentation narrative.

---

# 44. Success Criteria

The project will be considered successful if:

1. The pipeline can process the full grant dataset automatically.

2. Objective information is handled deterministically rather than unnecessarily delegated to AI.

3. Semantic matching successfully identifies grants related to agency priorities.

4. Early filtering achieves high recall for genuinely relevant opportunities.

5. The final scoring method is understandable and reproducible.

6. Each recommended grant includes evidence explaining why it was selected.

7. At least one genuine system failure is identified and documented.

8. A nontechnical agency decision-maker could understand and use the final ranked list.

---

# 45. Final Goal

The final product should transform:

```text
"Here are more than a thousand grants."
```

into:

```text
"Here are the 10 opportunities most worth your attention,
why each one matters,
what evidence supports the match,
and what risks you should check before applying."
```

That is the core purpose of the system.
