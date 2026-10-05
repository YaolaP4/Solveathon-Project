# How we used generative AI

The competition asks which AI tools we used, the key prompts, and at least one place the AI was wrong and how we caught it. Everything below can be checked in the repository.

## Tools and what each did

| Tool | Where | What it did | What it did **not** do |
|---|---|---|---|
| **Jev** (`typesafe-ai/jev`, via Vercel AI Gateway) | Layer 2, `src/semantic_triage.py` | Screened 1,303 grants with 4 multiple-choice questions each (relevance, strategic goal, applicant role, owning division), returning a probability for every answer | Never ranked grants; it only decided which went to in-depth review, and set a grant aside only when highly confident |
| **DeepSeek V4 Pro** (`deepseek/deepseek-v4-pro`, via Vercel AI Gateway) | Layer 3, `src/deep_analysis.py` | Wrote structured judgments for 270 grants (strategic alignment, operational fit, role, division, risks, a one-line rationale) with **verbatim evidence quotes** | Never ranked; Python verifies its quotes, and a fixed formula (`src/scoring.py`) ranks |
| **Muse Spark 1.3 contributor** (Meta, via Vercel AI Gateway) | Layer 3, first attempt | Analyzed the first 62 grants | Was **blocked by the provider** partway through (see below); its 62 answers are kept only as a cross-model check |
| **Claude Code** (Anthropic) | Development | Helped the team design the pipeline, write and review code and tests, investigate the data, and draft documentation and slides | Made no grant judgments in the pipeline. Every number in our results comes from the code and data in the repository, not from a chat |

No AI was used for: cleaning the data, deadlines, award amounts, eligibility hard filters, the final ranking formula, or the USAspending historical-award check. Those are plain Python rules (`src/clean_data.py`, `src/deterministic.py`, `src/scoring.py`, `src/award_history.py`).

Total AI cost of a full run: **$3.23**. Every model answer is saved in `data/cache/`, so the results reproduce without any API key.

## Key prompts

**Jev**, from `prompts/jev_triage.json`. One of the four questions, and the one that matters most:

> *applicant_role:* "What role could a state health and human services agency realistically play? 'State governments' appearing in a long list of eligible applicant types does NOT make the state the intended applicant: research grants often list every applicant type."
> Options: **lead**: a state agency or state health department is an intended lead applicant · **partner**: the lead is usually someone else, but the state is a natural partner or subrecipient · **atypical**: technically eligible, but designed for researchers, universities or small businesses · **ineligible**: excludes state agencies · **unclear**.

**DeepSeek**, from `prompts/deep_analysis.txt` (system instruction, abridged):

> "You never invent facts. Every quote you give must be copied character-for-character from the grant text… A program will check every quote against the source text, and any quote that is not found verbatim will be flagged as an error. You do NOT decide the final ranking and you do NOT judge deadlines or award size."

It returns one JSON object: alignment 0–10 with the matched objective, an evidence quote, applicant role with an eligibility quote, owning division, operational fit 0–10, restrictions, main risk, and a ≤30-word rationale for a budget director.

## Where the AI was wrong, and how we caught it

1. **The review model said DHHS would lead NIH research grants.** DeepSeek labeled **71** research or training grants (R01s, clinical trials) as DHHS-led, because "state governments" appears on their eligibility lists. **7 of our first top 10** were NIH research awards. *Caught by:* reading the top 10, and because Jev, which had explicit role definitions, labeled **none** of those grants as DHHS-led. Our Layer 2 vs Layer 3 disagreement log flagged all of them. *Fix:* an objective rule (the research activity code in the title, such as "R01") moves research grants to a separate "pass to a university partner" list.
2. **It cited a single word as evidence.** For "Partnership for Disaster Health Response System", the model claimed DHHS would lead and quoted only *"states"*. *Caught by:* our quote verifier rejects quotes too short to be evidence, so the role was automatically downgraded to "unclear".
3. **An AI provider blocked public-health text.** Meta's Muse Spark restricted our account for "repeated policy violations" after 62 grants. Our only inputs were public grant announcements, but DHHS grants discuss HIV, STIs, sexual violence and overdoses. *Caught by:* Layer 3 stalled, and a direct test returned the provider's block message. *Fix:* we tested three replacements on the 8 most sensitive grants Muse had analyzed and switched to DeepSeek V4 Pro (8/8 valid answers, 8/8 quotes verified, 100% agreement with Muse on role and division).
4. **Ranked administrative notices as opportunities.** The model rated CDC placeholder records titled only "RFA-TS-18-000" ("Submit application as necessary") as plausible fits. *Caught by:* reading the top 10. *Fix:* a Layer 1 rule removes these 17 award-transfer notices.

Full details, including non-AI failures and two checks that disagreed: `docs/failure_modes.md` (F1–F10) and `data/results/ai_error_log.csv`.
