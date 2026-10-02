# Failure log

Every failure we find goes here, in this format. Entries F1–F5 were found while building the data layers, before any model run. **Add the model failures (from `data/results/ai_error_log.csv`, the spot-check and `validation_report.md`) after the real run.** The submission needs at least one place where *the AI* was wrong and how we caught it.

Template:

```text
ID / Grant ID:
Observed error:
Why the system made the error:
How we detected it:
Whether we changed the pipeline:
What tradeoff the fix introduced:
```

---

## F1. Keyword matching recommends a grant DHHS cannot apply for

- **Grant:** Tribal Maternal, Infant, and Early Childhood Home Visiting Program (`3f13ec1b-3d98-484f-ac0b-6d8169f62831`)
- **Observed error:** The TF-IDF baseline ranks it **#6 of 1,320**, because its wording matches DHHS's home-visiting and child-and-family goals almost perfectly.
- **Why:** The eligibility text says applicants are "federally recognized Indian tribes (or consortia of tribes), tribal organizations, and urban Indian organizations". A state agency cannot apply. Word overlap can't read eligibility.
- **How detected:** Manual review of the baseline's top 10 (`data/results/keyword_baseline.csv`).
- **Pipeline change:** This is why Layer 2 asks Jev for `applicant_role` and Layer 3 must quote the eligibility text. The keyword method stays only as a baseline to compare against.
- **Tradeoff:** Eligibility now depends on a model's reading of the text, which can itself be wrong. That's why the eligibility quote is checked verbatim, and why only *verified* ineligibility zeroes a score.

## F2. Structured eligibility says "state governments" on grants not meant for states

- **Observed error:** 609 of the 689 NIH grants list `state_governments` as an eligible applicant type. Filtering on that field would keep hundreds of university research grants, and dropping grants without it would lose any grant that describes state eligibility only in its text.
- **How detected:** Counting applicant types against the funding agency during agency selection.
- **Pipeline change:** Structured eligibility is only a signal (Layer 1 flags). The role decision (lead / partner / atypical / ineligible) comes from reading the text in Layers 2–3.
- **Tradeoff:** More grants reach the paid model layers (1,320 instead of a few hundred). The cost is still under $1.

## F3. Placeholder award amounts would have caused large-dollar bias

- **Observed error:** One grant lists an award ceiling of **$999,999,999**, and another lists total funding of **$2,147,483,647** (2^31, a software maximum). Read as money, they would get the maximum financial score.
- **How detected:** Range checks on the award fields. Layer 1 now treats 3 sentinel rows and 114 zero amounts as placeholders (`docs/layer1_report.md`).
- **Pipeline change:** Placeholders and zeros are set to missing. Missing amounts get a neutral fixed score (5/10).
- **Tradeoff:** A real grant that omits its amount is slightly under-ranked on award value.

## F4. "Forecasted" does not mean "upcoming"

- **Observed error:** 234 of the 559 forecasts have a forecasted close date **before** our as-of date (2026-09-30). They were probably already posted under another record, delayed, or dropped.
- **How detected:** Layer 1 date check.
- **Pipeline change:** Kept on the watchlist, since the program may still come back, but flagged as `stale_forecast` and shown as "date passed — check if posted".
- **Tradeoff:** The watchlist may contain some programs that no longer exist. We chose that over silently dropping real ones.

## F5. The strategic plan is out of date

- **Observed error:** The only NCDHHS plan on the OSBM page covers **2023–2025**. Our alignment scores measure fit with that plan, not necessarily with 2026 priorities (for example after federal funding changes).
- **How detected:** Reading the plan's date range.
- **Pipeline change:** None possible with the provided data. Stated as a known limitation.
- **Tradeoff:** Not applicable. Leadership should read "strategic alignment" as alignment with the 2023–2025 plan.

---

## Model failures (fill in after the real run)

Sources: `data/results/ai_error_log.csv` (unverified quotes, invalid outputs, Layer 2 vs Layer 3 disagreements), `data/validation/spotcheck.csv`, and the false-negative list in `data/results/validation_report.md`.
