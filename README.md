# NC Solve-a-thon Grant Prioritization System

## Overview

This project builds a reproducible grant-prioritization pipeline for a selected North Carolina state agency.

The goal is not simply to find grants containing similar keywords. The system should answer a more useful decision-making question:

> **Given hundreds or thousands of federal grant opportunities, which grants are most worth this agency's limited time and attention?**

The system combines:

- deterministic filtering and feature engineering,
- fast semantic classification,
- deeper analysis for high-value or uncertain opportunities,
- transparent scoring,
- and human validation.

The qualifier implementation will focus on **one selected NC state agency**, but the architecture is designed so the same pipeline could later be configured for another agency by replacing the agency profile, strategic priorities, and scoring criteria.

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
Stronger model / detailed reasoning
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

A proposed project structure:

```text
solveathon-grants/
│
├── README.md
│
├── requirements.txt
│
├── .env.example
│
│
├── data/
│   ├── raw/
│   │   └── grants.csv
│   ├── processed/
│   │   └── grants_cleaned.csv
│   └── results/
│       ├── ranked_grants.csv
│       ├── jev_outputs.csv
│       └── validation_sample.csv
│
├── agency/
│   ├── agency_profile.md
│   ├── strategic_plan.txt
│   └── priorities.json
│
├── src/
│   ├── clean_data.py
│   ├── deterministic.py
│   ├── semantic_triage.py
│   ├── deep_analysis.py
│   ├── scoring.py
│   ├── validation.py
│   └── pipeline.py
│
├── prompts/
│   ├── jev_triage.txt
│   └── deep_analysis.txt
│
├── notebooks/
│   └── analysis.ipynb
│
└── docs/
    ├── methodology.md
    ├── failure_modes.md
    └── presentation_notes.md
```

---

# 5. Agency Configuration

The first major project decision is choosing one NC state agency.

The pipeline should not hard-code every agency-specific decision into the Python source.

Instead, agency information should be stored as configuration.

Example:

```json
{
  "agency_name": "NC Department of Public Instruction",

  "mission": "Support public schools and improve educational outcomes across North Carolina.",

  "strategic_priorities": [
    {
      "id": "P1",
      "name": "Student Outcomes",
      "description": "Improve academic performance and student success."
    },
    {
      "id": "P2",
      "name": "Data-Informed Decision Making",
      "description": "Improve statewide education analytics, data systems, and evidence-based policymaking."
    },
    {
      "id": "P3",
      "name": "Educator Workforce",
      "description": "Improve recruitment, development, and retention of educators."
    },
    {
      "id": "P4",
      "name": "Technology Modernization",
      "description": "Modernize educational technology and operational systems."
    }
  ]
}
```

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
days_until_close = close_date - current_date
```

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

## Proposed Tool

Jev

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

Example conceptual input:

```text
AGENCY:
NC Department of Public Instruction

PRIORITIES:
- student achievement
- educator workforce
- statewide data systems
- education technology
- school safety

GRANT TITLE:
...

GRANT DESCRIPTION:
...

ELIGIBILITY:
...
```

Desired structured output:

```json
{
  "domain_relevance": "strong",
  "matched_priority": "P2",
  "strategic_alignment": 9,
  "eligibility": "likely",
  "confidence": 0.93
}
```

---

# 11. Layer 2 Outputs

The semantic triage layer should avoid producing one unexplained final score.

Instead, it produces multiple independent signals.

Proposed schema:

```json
{
  "domain_relevance": "none | weak | moderate | strong",

  "strategic_alignment": 0,

  "matched_priorities": [
    "P1",
    "P3"
  ],

  "eligibility_assessment":
    "eligible | likely | uncertain | unlikely | ineligible",

  "implementation_fit":
    "low | medium | high",

  "confidence": 0.0
}
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

Example structured output:

```json
{
  "strategic_alignment": 9,

  "strategic_reason":
    "Supports statewide longitudinal education data and evidence-based policymaking.",

  "eligibility_status": "eligible",

  "eligibility_evidence":
    "State educational agencies are explicitly listed as eligible applicants.",

  "implementation_fit": 8,

  "deadline_feasibility": 6,

  "major_risk":
    "Application deadline is less than one month away.",

  "recommended_for_review": true
}
```

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

# 17. Proposed Scoring Framework

The exact scoring weights should be finalized after selecting the agency.

A possible starting point:

```text
Strategic Alignment       35%
Operational Fit           20%
Financial Value           15%
Deadline Feasibility      15%
Eligibility Confidence    15%
```

Example:

```python
final_score = (
    strategic_alignment * 0.35
    + operational_fit * 0.20
    + financial_value * 0.15
    + deadline_feasibility * 0.15
    + eligibility_confidence * 0.15
)
```

---

# 18. Eligibility as a Gate

Eligibility may deserve special treatment.

If a grant is confirmed to be legally unavailable to the agency, its financial or strategic attractiveness becomes irrelevant.

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
8.55 / 10
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

---

# 21. Validation Sample

Create a manually reviewed sample of grants.

For example:

```text
100–150 randomly selected grants
```

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
"educator retention"

Grant:
"reducing K–12 teacher attrition"
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
strategic_alignment_score
operational_fit_score
financial_value_score
deadline_score
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
Jev

Purpose:
Initial semantic grant triage.

Input:
Agency description
Strategic priorities
Grant title
Grant description
Eligibility description

Output:
Domain relevance
Matched strategic priority
Eligibility assessment
Implementation fit
Confidence

Decision authority:
Jev does not produce the final ranking.

Final scoring:
Performed deterministically in Python.
```

---

# 35. Deep Model Documentation

If a stronger language model is used for Layer 3:

```text
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
Strong general-purpose LLM and/or manual review
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

- [ ] Choose the target NC agency.
- [ ] Define the target agency employee/user.
- [ ] Extract strategic priorities.
- [ ] Finalize 3–5 grant evaluation criteria.
- [ ] Determine hard filters.
- [ ] Determine scoring weights.
- [ ] Define Jev output schema.
- [ ] Determine Jev confidence thresholds.
- [ ] Decide whether TF-IDF improves performance.
- [ ] Choose the deep-analysis model.
- [ ] Create a validation sample.
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
