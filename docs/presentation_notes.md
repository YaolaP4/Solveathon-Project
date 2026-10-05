# Presentation notes: 5-minute recorded video to NC DHHS leadership

Every number here comes from committed outputs, as of the 2026-10-05 run. Sources: `data/results/top_results.md`, `award_history_report.md`, `validation_report.md`, `ai_error_log.csv`, and `docs/layer1_report.md`. **If you rerun anything, recheck the numbers before recording. Don't round up, and don't claim more than is written here.** The rubric rewards an honest evaluation over claimed perfection.

Audience: a **non-technical budget director**. Lead with what to do, then why to trust it. Keep the technology to one slide.

---

## 1. Who the user is and what "good" means (0:00–0:40)

- **User:** the NC DHHS federal-grants coordinator. Every week they decide which new federal postings deserve a division's time, and route each one to the division that would own it.
- **A good match for DHHS**, from the DHHS 2023–2025 Strategic Plan (`agency/agency_profile.md`):
  1. DHHS can **lead or be a named partner**: eligibility is a gate.
  2. It advances a **named strategic-plan goal** (health access, child & family well-being, behavioral health, workforce, operational excellence).
  3. A **DHHS division already does this work** and could run it.
  4. There's **realistic time to apply**.
  5. The **award is worth the effort**: cost share flagged, award size on a log scale so a giant award can't drown out a better fit.

## 2. The problem (in one sentence)

Grants.gov posts hundreds of opportunities a week, and the starter data alone has **1,662**. Nobody can read them all, and money goes to the states that find the right postings first.

## 3. What we found: say this first (0:40–1:40)

**Apply now (open):**
- **Title X Family Planning Services**: 98/100. Division of Public Health. Up to $22M per award, 103 days to apply. **NC DHHS has won $14.7M under this program in FY2022–25** (USAspending.gov).

**Prepare now (forecast watchlist), where most of the proven money is:**

| Forecast grant | Score | Owner | NC DHHS awards FY2022–25 |
|---|---|---|---|
| Ryan White HIV/AIDS Part B + AIDS Drug Assistance Program | 96 | Public Health | **$187.6M** |
| Maternal, Infant & Early Childhood Home Visiting (MIECHV) | 96 | Child & Family Well-Being | **$21.1M** |
| Preventing Infectious-Disease Consequences of Drug Use | 94 | Public Health | — |
| Preschool Development Grant Birth–5 | 94 | Child Development & Early Ed | **$36.3M** |
| National HIV Behavioral Surveillance | 93 | Public Health | **$30.2M** |

Action line for leadership: *"Ryan White Part B and Preschool Development B-5 had forecast post dates that have already passed. They may be open on Grants.gov right now. Check today."*

Say plainly: *"As of September 30, most programs DHHS traditionally wins are forecasts rather than open listings. Many closed between the August 18 data pull and now. That's why the watchlist matters: it's the advance warning."*

## 4. How the matching works, in plain language (1:40–2:30)

1. **Rules first, no AI.** Remove what's objectively dead: 330 already closed, 12 archived, and 17 administrative paperwork notices. Score deadline and award size with fixed formulas. **1,303 grants remain.**
2. **Fast AI screen (Jev).** Four multiple-choice questions per grant: is this DHHS's kind of work, which goal, can DHHS lead or partner, which division? Jev gives a **probability** for every answer. A grant is set aside **only when Jev is very confident** it's irrelevant or ineligible; anything uncertain goes to the next step. Result: **283** go on, **1,020** set aside (kept, not deleted).
3. **Careful AI review (DeepSeek V4 Pro).** For each of the 283 it writes the reasons, and **it must quote the grant text word-for-word**. Python checks every quote; a claim we can't find is downgraded. all **283** analyzed.
4. **A published formula ranks.** Strategic fit 30%, ability to run it 25%, award size 15%, deadline 15%, eligibility 15%. **The AI never ranks anything**; every score can be traced. Research grants (NIH-style R01s and similar) go to a separate "forward to a university partner" list.

Cost and reproducibility: **$3.36 of AI spend in total.** All answers are saved, so `python src/pipeline.py` **reproduces the whole thing in about 11 seconds, with no API key and no cost.** 71 automated tests.

## 5. How confident to be, and why (2:30–3:30)

Four independent checks, each with its real number:

1. **History: does DHHS actually win these programs?** (USAspending.gov, no AI.) We checked who received awards under each grant's federal program listing in FY2022–25.
   - **Watchlist top 5: 4 of 5 are programs NC DHHS has won** ($187.6M, $36.3M, $30.2M, $21.1M).
   - **Open top 10: only 1 of 10** (Title X). Say this honestly: the open list is thinner, and #2 (Public Health Crisis Response) is a new emergency roster with no award history.
   - Grants Jev set aside had a state-agency award history **2%** of the time; grants it sent on, **25%**. That's independent evidence the screen is sorting in the right direction.
2. **Evidence:** **282 of 283** strategic quotes and **280 of 283** eligibility quotes are found word-for-word in the grant text.
3. **Two AI models agree:** Muse Spark (before Meta blocked it) and DeepSeek agreed on DHHS's role for **87%** and on the owning division for **95%** of the **60** grants both analyzed.
4. **Human labels vs. keyword search:** a teammate blind-labeled **31** sampled grants (8 relevant). Jev kept **93%** of the relevant ones (95% interval **67–100%**). A keyword search given the same review budget kept **71%** (33–100%).
   - **Be honest about it:** 31 labels from one non-expert, and the intervals overlap, so this is *promising, not proof*. Jev's only "miss" was a CDC global-health program in **Ethiopia**, which a coordinator could reasonably skip.

**The keyword comparison that sells the method:**
- Keyword search ranks **Ryan White Part B #670 of 1,303** and **Title X #134**. Ours ranks them **#1 on the watchlist** and **#1 overall**.
- Keyword search's **#1 result** ("Behavioral Health Integration Initiative") is an **Indian Health Service program only tribes can apply for**. Jev set it aside with 99% confidence. Of the keyword top 20, Jev set aside 6, and **all 6 were correctly set aside** (4 for tribes or urban Indian organizations, 2 NIH research programs).

## 6. Where the AI was wrong, and how we caught it (3:30–4:15)

Pick one or two for the video (all in `docs/failure_modes.md`):

1. **The research-grant mistake (F7).** DeepSeek labeled **73 research grants** (NIH R01s, clinical trials) as ones DHHS would *lead*, because "state governments" appear on their eligibility lists. **7 of our first top 10** were NIH research awards. **Caught by:** Jev labeled *none* of them DHHS-led, and the disagreement log flagged it. **Fix:** an objective rule (the research code in the title, like "R01") moves them to a separate research-partnerships list.
2. **Fake-evidence guardrail.** For "Partnership for Disaster Health Response System" the model claimed DHHS would lead and cited the single word *"states"* as proof. The verifier rejected it, and the role became "unclear" automatically.
3. **An AI vendor blocked us (F6).** Meta's Muse Spark blocked our account for "policy violations" after 62 grants, because DHHS grants discuss HIV, STIs, sexual violence and overdoses. We tested three replacements on the most sensitive grants and switched in one setting. **Lesson for DHHS: don't depend on a single AI vendor.**
4. **Two checks disagreed, and reading settled it (F9).** The award-history check flagged a Ryan White Part B notice that Jev had set aside, under a program where NC DHHS won $187.6M. Reading the notice showed it's the **Pacific Islands territories-only** version, so Jev was right. History is per program, not per notice, which is why we keep both checks.

## 7. Limitations (pick one to say out loud)

- **The human labels are thin:** 31 grants, one team member, not grant experts. Recall intervals are wide.
- **The strategic plan is 2023–2025.** "Strategic fit" means fit with that plan, which may lag 2026 priorities.
- **The data is a snapshot from 2026-08-18.** Anything posted since isn't included.

## 8. What we'd build with more time (4:15–5:00)

- A **weekly automatic run** on the live Grants.gov feed, emailing the coordinator the new top 5 and any watchlist item that just opened.
- Use **award history as a scoring input** (a bonus for programs states actually win), not only as a check.
- **Expert labels** from a real DHHS grants officer, with two labelers per grant, so recall becomes a measurement rather than a first check.
- **Two AI vendors in parallel**, so a vendor block can't stop the pipeline. Also give the deep-review model the same role definitions Jev has.

---

## Rubric checklist

- **Understanding:** a specific user (the DHHS federal-grants coordinator) and 5 criteria from the DHHS plan, which directly drive the AI questions and the formula.
- **Framing:** decision support with three actions: apply now, prepare (watchlist), forward to a research partner.
- **Solving:** reproducible (one command, about 11 s, $0 rerun), objective rules wherever possible, AI only where reading is required, 71 tests.
- **Evaluating:** award history (independent and objective), verified quotes, cross-model agreement, blind labels with intervals, a keyword baseline, an AI error log, and 10 documented failures.
- **Driving impact:** each grant comes with a one-line reason, owner, deadline, main risk and "check Grants.gov now" flags (`data/results/top_results.md`).
