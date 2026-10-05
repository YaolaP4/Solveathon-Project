# Validation report

Labeled and resolved: **31** grants (0 awaiting adjudication). Label = 'the coordinator should spend time on this'.

> **31 of 31 labels come from a single labeler** (a team member, not a grants expert), so labeler agreement cannot be measured and the labels themselves are uncertain. With this few labels, the intervals below are wide; read them as a first check, not a measurement.

## Do humans agree?

- No double-labeled grants yet.
- Disagreements show how ambiguous 'relevant' is; they cap how well any method can score.

## Labeled sample by stratum

| stratum         |   labeled |   relevant |   population |
|:----------------|----------:|-----------:|-------------:|
| S1_top100       |        12 |          6 |          100 |
| S2_rank101_400  |         9 |          2 |          300 |
| S3_rank401_plus |        10 |          0 |          903 |

## Layer 2 (Jev) vs keyword baseline

Jev sends **283** grants to deep review. The baseline is given the same budget (its top 283 by TF-IDF similarity). Recall = share of relevant grants that reach Layer 3. Estimates are weighted by stratum size; intervals are 95% stratified bootstrap.

| Method | Recall | 95% CI | Precision | 95% CI |
|---|---|---|---|---|
| Jev routing | **93%** | 67%–100% | 29% | 9%–69% |
| Keyword baseline (same budget) | 71% | 33%–100% | 28% | 9%–53% |

## Layer 2 false negatives (relevant but deprioritized) - inspect every one

- `V041` Expanding global health security through local partnerships in Ethiopia — Jev: weak (p=0.94), role atypical; P(unrelated or weak)=1.00

## Layer 3 recommendation vs human label

- 11 labeled grants were deep-analyzed; `recommended_for_review` matches the human label on 73% (unweighted).
- Recommended but labeled not relevant: 1; labeled relevant but not recommended: 2.

## Where the AI was wrong (automatic checks, `ai_error_log.csv`)

| check                        | severity   |   count |
|:-----------------------------|:-----------|--------:|
| api_error                    | high       |      13 |
| layer2_vs_layer3_division    | low        |      56 |
| layer2_vs_layer3_relevance   | high       |      48 |
| layer2_vs_layer3_relevance   | medium     |      11 |
| layer2_vs_layer3_role        | medium     |      89 |
| unverified_eligibility_quote | high       |       1 |
| unverified_eligibility_quote | medium     |       1 |
| unverified_strategic_quote   | high       |       1 |

Examples:

- **unverified_eligibility_quote** — Partnership for Disaster Health Response System: claimed role 'lead' but its quote was not found in the eligibility text ('states'); role downgraded to 'unclear'
- **layer2_vs_layer3_relevance** — Improving Protection against Influenza and Other Respiratory Pathogens: the US Flu VE Network: Jev said 'weak' (p=0.51) but deep model scored alignment 7/10 - a possible Layer 2 false negative
- **layer2_vs_layer3_relevance** — Navigator Emergency Department Diversion Models for Non-Urgent Mental Health Concerns (R34 Clinical Trial Required): Jev said 'weak' (p=0.51) but deep model scored alignment 7/10 - a possible Layer 2 false negative
- **layer2_vs_layer3_relevance** — Development and Testing of Novel Interventions to Improve HIV Prevention, Treatment, and Program Implementation for People Who Use Substances (R34 Clinical Trial Required): Jev said 'weak' (p=0.5) but deep model scored alignment 7/10 - a possible Layer 2 false negative
- **layer2_vs_layer3_relevance** — Notice of Intent to Publish a Forecast for EmbraceHealth Clinical Research Network to Reduce Health Disparities – Research Sites: Jev said 'weak' (p=0.63) but deep model scored alignment 9/10 - a possible Layer 2 false negative
