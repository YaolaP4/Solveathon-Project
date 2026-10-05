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

## F6. A commercial AI provider blocked legitimate public-health work

- **Observed error:** Partway through Layer 3, Meta's provider (Muse Spark 1.3 contributor) **restricted our account for "repeated policy violations"**. Every later request failed, including a test that only said "Reply with the word OK".
- **Why:** Our only inputs were public Grants.gov announcements and the DHHS strategic plan. DHHS grants routinely discuss HIV, STIs, sexual violence, overdoses and child abuse, and the provider's safety filter evidently counted that as violations. 62 of 298 grants had already been analyzed.
- **How detected:** Layer 3 progress stalled, and a direct test request returned HTTP 403 with the provider's message.
- **Pipeline change:** We tested three replacement models on the 8 most sensitive grants Muse had analyzed (valid output, verified quotes, agreement with Muse, cost) and switched to **DeepSeek V4 Pro**: 8/8 valid, 8/8 quotes verified, 100% agreement with Muse on applicant role and division. The switch was one setting, because the model is configurable and every answer is cached.
- **Tradeoff:** Higher cost (~$2.50 instead of ~$0.30 for 298 grants) for a more capable model that doesn't refuse this subject matter. **For a real DHHS deployment this is a vendor risk:** the agency's normal vocabulary can trip a vendor's safety filter, so the system must not depend on one AI provider.

## F7. The in-depth model said DHHS would "lead" NIH research grants

- **Observed error:** DeepSeek V4 Pro (Layer 3) labeled **71 research or training grants** (NIH R01/R34/R61, CDC/FDA U01 …) as ones DHHS would *lead*, because "state governments" appears on their eligibility lists. With full eligibility credit, **7 of the first top-10 "apply now" grants were NIH research awards**, which a state grants coordinator can't realistically pursue as lead applicant.
- **Why:** The Layer 3 prompt lists the role options but, unlike the Jev prompt, never defines them. "Lead" was read as "legally allowed to apply".
- **How detected:** (1) Reading the top 10, where the model's own "main risk" text said "requires an academic partner". (2) The Layer 2 vs Layer 3 disagreement log: Jev labeled **0** of those grants as DHHS-led (65 partner, 61 atypical, 4 ineligible).
- **Pipeline change:** An objective Layer 1 rule, `research_mechanism` (NIH opportunity, or a research/training activity code such as R01, K99, U01 or P50 in the title; deliberately not CDC's U60 state cooperative agreements). Layer 4 moves these 130 grants to a separate **research-partnerships** list for university partners.
- **Tradeoff:** A rare research award DHHS *could* lead now sits on the research list instead of the apply-now list. The prompt itself still lacks role definitions; fixing it means re-running Layer 3 (about $3).

## F8. Administrative paperwork listed as funding opportunities

- **Observed error:** 17 records are not opportunities at all: 15 CDC placeholders titled only "RFA-XX-18-000" ("Submit application as necessary [for Type 6 Applications]", close date 2030), plus NIH successor-in-interest / change-of-recipient notices. They exist only to transfer an existing award. Several reached the top 10, because the AI rated a vague "public health" placeholder as a plausible fit.
- **How detected:** Reading the top 10 (entries titled "RFA-TS-18-000", "RFA-OE-18-000"). The AI's own risk note said "the announcement provides almost no programmatic detail". These records also caused most of the unverified quotes, since there's nothing real to quote.
- **Pipeline change:** Layer 1 hard-filters them (`administrative_award_transfer_notice`). The test pins the count at 17.
- **Tradeoff:** None for a grants coordinator; nobody can win new money through these notices.

## F9. Two independent checks disagreed: Jev vs. the historical-award check (Jev was right)

- **Observed:** The USAspending check (`data/results/award_history_report.md`) flagged **24** grants Jev set aside as having "state-agency award history", which made them possible false negatives. The most striking one is **"HIV Care Grant Program - Part B … Pacific Islands Jurisdictions" (HRSA-27-064)**: Jev rated it *strong* relevance but *ineligible* (p = 0.94), while NC DHHS received **$187.6M** under its assistance listing (93.917) in FY2022–25.
- **Why they disagree:** An assistance listing is shared by every funding notice under it. HRSA-27-064 is the Pacific-territories version of Ryan White Part B; its eligibility text reads "Domestic territories, and freely associated states". NC's own version, HRSA-27-063, is #1 on our watchlist. **Jev read the notice correctly; the listing-level history could not tell the two notices apart.**
- **The other 23, from titles and eligibility:** the NIH/CDC/FDA small-business (SBIR) parent notice, which spans 41 listings; two tribal-only programs; three research programs (NIOSH mining robotics, a mesothelioma tissue bank, World Trade Center research careers); and 17 programs outside DHHS's field that states do win (Gulf RESTORE Act, conservation, outdoor recreation, invasive species, urban forestry, specialty crops, battlefield land, defense research, construction technology, specialized education). **None looked like a genuine DHHS miss.**
- **How detected:** Building the historical-award check and comparing it against Layer 2's routing, then reading the eligibility text of each flagged grant.
- **Pipeline change:** None to the ranking. The report carries the caveat that history is per listing, not per notice, and marks grants spanning more than 3 listings.
- **Tradeoff / lesson:** The award history is a useful *objective* signal: grants Jev set aside had state-agency history **2%** of the time, against **25%** for grants it sent on. But it can't replace reading the specific notice.

## F10. Most of the "apply now" list isn't money DHHS has won before

- **Observed:** Of our **top 10 open** grants, only **1** (Title X, $14.7M to NC DHHS in FY2022–25) has a history of awards to NC DHHS. #2 (Public Health Crisis Response) has no awards at all in FY2022–25: it's a new roster mechanism that pays only during emergencies. Of the **top 5 watchlist** grants, **4** do: Ryan White Part B $187.6M, Preschool Development B-5 $36.3M, HIV Behavioral Surveillance $30.2M, MIECHV $21.1M.
- **Why:** Most of the state programs DHHS traditionally wins either closed between the August 18 data pull and September 30, or are forecasts. The open list is what's left.
- **How detected:** The historical-award check (USAspending.gov), an objective source that's independent of both AI models.
- **Pipeline change:** None yet. With more time, award history could become a scoring input (for example, a bonus for programs states actually win). It's deliberately kept as validation here, so the check stays independent of the ranking it checks.

## Label uncertainty (validation)

- The first 31 labels come from **one team member, not a grants expert** (`data/validation/labels.csv`, labeler A). Jev's only "miss" among them, *"Expanding global health security through local partnerships in Ethiopia"* (labeled relevant), is arguably a labeling call rather than a model error: it's an overseas CDC program. We kept the label as given. Recall numbers from 8 relevant grants have wide intervals and should be read as a first check.

---

## More model failures (add from the labeled sample once it is done)

Sources: `data/results/ai_error_log.csv` (unverified quotes, invalid outputs, Layer 2 vs Layer 3 disagreements), `data/validation/spotcheck.csv`, and the false-negative list in `data/results/validation_report.md`.
