# Presentation notes: 5-minute recorded video to NCDHHS leadership

Every number below comes from the committed results (`data/results/`, `docs/layer1_report.md`, `data/results/ai_error_log.csv`) as of the 2026-10-02 run. If you rerun the pipeline, recheck the numbers before recording. **Don't round up, and don't claim anything in the "not measured yet" box.** The rubric rewards honest evaluation over claimed perfection.

Audience: a **non-technical budget director**. Lead with what to do, then why to trust it. Keep the technology to one slide.

---

## The headline numbers

| What | Number | Source |
|---|---|---|
| Federal grant listings in the starter dataset | **1,662** | `data/raw/grants.csv` |
| Removed by objective rules (closed before Sept 30, archived, or administrative transfer notices) | **359** | `docs/layer1_report.md` |
| Screened by AI (Jev), in about a minute | **1,303** | `jev_outputs.csv` |
| Sent to in-depth AI review | **283** | `jev_outputs.csv` |
| Analyzed in depth with quoted evidence (DeepSeek V4 Pro) | **270** | `deep_analysis.csv` |
| Final lists: open program grants / forecast watchlist / research partnerships | **28 / 112 / 130** | `ranked_grants.csv`, `watchlist.csv`, `research_partnerships.csv` |
| Evidence quotes that checked out word-for-word against the grant text | **269 of 270** (strategic), **267 of 270** (eligibility) | `deep_analysis.csv` |
| Total AI cost for the whole run | **$3.23** (about a quarter of a cent per grant) | Vercel AI Gateway usage |
| Time to reproduce the entire ranking from saved answers | **6 seconds, $0, no API key** | `python src/pipeline.py` |
| Automated tests | **65** | `python -m pytest tests -q` |

## Results to show (slide 2)

**Apply now (open):**
1. **Title X Family Planning Services**: 98/100. Division of Public Health, child and family well-being goal. Up to $22M per award, 103 days to apply. Main risk: the FY27 amount depends on the federal budget.

**Prepare now (forecast watchlist), where most of the high-value money is:**
1. **Ryan White HIV/AIDS Part B + AIDS Drug Assistance Program**: 96/100. Public Health. *The forecast post date has passed, so it may already be open: check Grants.gov today.*
2. **Maternal, Infant & Early Childhood Home Visiting (MIECHV)**: 96/100. Child and Family Well-Being.
3. **Preventing Infectious Disease Consequences of Drug Use**: 94/100. Public Health, opioid goal.
4. **Preschool Development Grant B-5**: 94/100. Child Development & Early Education. *May already be open.*

Say plainly: *"As of September 30, most of the strongest DHHS opportunities are forecasts, not open listings. Many state programs closed between the August data pull and today, so the watchlist is where the advance warning matters."* That's the challenge story ("money goes to states that found the posting first") backed by our data.

## The one comparison that sells the method (slide 3)

A keyword search (matching grant text against the strategic plan) is what most people would build. We built it as a baseline:

- Keyword search ranks **Ryan White HIV Part B, a core DHHS formula grant for HIV care, #670 of 1,303**. **Our system ranks it #1 on the watchlist.**
- Keyword search ranks **Title X at #134**. **Ours ranks it #1 overall.**
- Keyword search's **#1 result is an Indian Health Service program DHHS cannot apply for**: it's limited to tribes and tribal organizations. Jev set it aside with 99% confidence.
- Of the keyword method's top 20, Jev set aside 6. **All 6 were correct**: 4 programs limited to tribes, tribal or urban Indian organizations, and 2 NIH research programs (one limited to existing award holders).

The point for leadership: *matching words isn't the same as matching opportunities. Eligibility decides whether a grant is real for DHHS.*

## How it works, in plain language (slide 4; keep to about 45 seconds)

1. **Rules first, no AI.** Remove what is objectively dead: closed, archived, or administrative paperwork notices. Score deadlines and award size with fixed formulas.
2. **Fast AI screen (Jev).** Four multiple-choice questions per grant: is this DHHS's kind of work? which goal? can DHHS lead or partner? which division owns it? Jev gives a **probability** for each answer, and a grant is only set aside when Jev is very confident. Anything uncertain goes on to the next step.
3. **Careful AI review (DeepSeek).** For the ~280 survivors it writes the reasons and **must quote the grant text word-for-word**. Python checks every quote; a claim we can't find in the text is downgraded.
4. **A published formula ranks** (strategic fit 30%, ability to run it 25%, award size 15%, deadline 15%, eligibility 15%). **The AI never ranks anything.** Every score can be traced and explained.

## How confident to be, and where the AI was wrong (slide 5; required by the rubric)

**Evidence it works:**
- 269 of 270 strategic quotes, and 267 of 270 eligibility quotes, are found word-for-word in the grant text.
- Two different AI models (Muse Spark, before it was blocked, and DeepSeek) agreed on DHHS's role for **87%** of the 60 grants both analyzed, and on the owning division for **95%**.
- Every grant Jev set aside from the keyword method's top 20 was correctly set aside.

**Where the AI was wrong, and how we caught it (pick one for the video):**
1. **The research-grant mistake.** The in-depth model labeled **71 NIH research grants** (R01s, clinical trials) as ones DHHS would *lead*, because "state governments" appear on their eligibility list. Our first top 10 had **7 research grants** in it. We caught it because Jev, which was given clear definitions of each role, labeled **none** of those as DHHS-led, and the disagreement log flagged it. Fix: an objective rule (the NIH activity code in the title, like "R01") moves these to a separate *research partnerships* list for university partners.
2. **The fake-evidence guardrail.** For "Partnership for Disaster Health Response System" the model claimed DHHS would lead and cited the single word *"states"* as proof. Our verifier rejects quotes that short, so the role was downgraded to "unclear" automatically.
3. **The AI vendor that blocked us.** Meta's model blocked our account for "policy violations" partway through, because DHHS grants discuss HIV, STIs, sexual violence and overdoses. We tested three replacements on the most sensitive grants and switched in one setting. **Lesson for DHHS: don't build on a single AI vendor.**

**Not measured yet (don't claim these until the labels are done):**
- Recall: the share of truly relevant grants the system keeps. This needs the 90-grant blind labeling sheet (`data/validation/labels.csv`). After labeling, run `python src/validation.py evaluate`; it reports recall with a confidence interval and lists every grant Jev wrongly set aside.

## One known limitation (required)

Pick one and say it plainly:
- **The strategic plan is from 2023–2025.** "Strategic fit" means fit with that plan, which may lag 2026 priorities.
- **The data is a snapshot from August 18.** New postings since then aren't included; in production this would pull from Grants.gov weekly.
- **AI judgment of "can DHHS realistically run this"** is the least reliable score. That's why it has evidence checks and is only 25% of the formula.

## What we'd build with more time

- A **weekly automatic run** against the live Grants.gov feed, emailing the coordinator the new top 5 and any watchlist item that just opened.
- **Feedback from the coordinator** ("applied", "not for us") to tune the weights.
- Give the in-depth model the same role definitions Jev has, and re-run (about $3).
- Use **two AI vendors in parallel**, so one vendor blocking us can't stop the pipeline.

---

## Suggested 5-minute script

| Time | Slide | Say |
|---|---|---|
| 0:00–0:40 | Problem & user | "Every week Grants.gov posts hundreds of opportunities. Our user is the DHHS federal-grants coordinator, who has to decide which ones are worth a division's time and route them. A good match for DHHS means: DHHS can lead or partner, it advances a strategic-plan goal, a division already does this work, there is time to apply, and the award is worth the effort." |
| 0:40–1:40 | Results | Title X; the watchlist (Ryan White Part B, MIECHV, PDG B-5); "check Ryan White and PDG B-5 on Grants.gov now, they may already be open." |
| 1:40–2:30 | Why not keyword search | The #670 vs #1 comparison, and keyword search's #1 being a program only tribes can apply for. |
| 2:30–3:15 | How it works | The 4 steps; "AI gives evidence, a published formula ranks." |
| 3:15–4:15 | Confidence & failure | 269/270 verified quotes; 87% cross-model agreement; the research-grant mistake and how we caught it; recall if labeled by then. |
| 4:15–5:00 | Limitation & next | 2023–25 plan; weekly live run; it reproduces in 6 seconds for $0, about a quarter of a cent per grant. |

## Rubric checklist

- **Understanding:** user = DHHS federal-grants coordinator; 5 criteria taken from the DHHS plan (`agency/agency_profile.md`). The criteria drive the formula and the AI questions directly.
- **Framing:** decision support, not decision replacement; "open now" vs "prepare" vs "research partner" are three different actions.
- **Solving:** reproducible (one command, cached, 6 s), 65 tests, objective rules wherever possible, and AI only where reading is required.
- **Evaluating:** keyword baseline comparison, verified evidence, cross-model agreement, an AI error log, 8 documented failures (`docs/failure_modes.md`), and recall from blind labels once they're done.
- **Driving impact:** the top-results list (`data/results/top_results.md`) gives a one-line reason, owner, deadline and main risk per grant, plus "check Grants.gov now" flags.
