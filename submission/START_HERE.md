# Start here: NC DHHS Grant Finder (UNC Solve-a-thon 2026 qualifier)

A reproducible pipeline that ranks 1,662 federal grant listings for the NC Department of Health and Human Services against five agency-specific criteria.

## Read these first
1. `submission/top_results.pdf`: our results (top 10 open + top 5 upcoming grants), each with a one-line rationale and a check against our 5 criteria.
2. `submission/ai_usage.md`: how we used generative AI, the key prompts, and where the AI was wrong and how we caught it.
3. `submission/slide_guide.md`: a plain-language walk through our presentation.
4. `README.md`: the full design document, from Layer 0 to Layer 5, with an update log.

## How we got there (the code)
| Step | File | What it does |
|---|---|---|
| Layer 0 | `src/clean_data.py` | Cleans the Grants.gov export (dates, numbers, HTML) |
| Layer 1 | `src/deterministic.py` | Plain rules: removes closed, archived and paperwork listings; scores deadline and award size; flags forecasts and research grants. Audit: `docs/layer1_report.md` |
| Layer 2 | `src/semantic_triage.py` + `prompts/jev_triage.json` | Jev screens every grant with 4 multiple-choice questions |
| Layer 3 | `src/deep_analysis.py` + `prompts/deep_analysis.txt` | DeepSeek reviews the 283 kept grants; Python verifies every quote |
| Layer 4 | `src/scoring.py` | Published formula (30/25/15/15/15) ranks the grants into three lists |
| Layer 5 | `src/award_history.py`, `src/validation.py`, `src/keyword_baseline.py` | Checks: federal award history (USAspending.gov), hand labels, keyword-search comparison |

Our agency profile, criteria and weights are in `agency/agency_profile.md` and `agency/priorities.json`.

## Evidence and failures
- `data/results/award_history_report.md`: who actually won these programs in FY2022–25.
- `data/results/validation_report.md`: recall against our hand labels and the keyword baseline.
- `docs/failure_modes.md`: 10 documented failures and what we changed.

## Reproduce it
```bash
pip install -r requirements.txt
python src/pipeline.py        # reruns everything from saved model answers in about 11 s, no API key needed
python -m pytest tests -q     # 71 tests
```
