# Recording script: 5 minutes or less, addressed to NC DHHS leadership

A recording of **5 minutes or less** is preferred (a PowerPoint is accepted instead). Read only the **Say** text: **648 words, about 4.6 minutes** at a calm 140 words per minute. The **Background** lines are numbers to have ready for questions; don't read them. The same text is in each slide's speaker notes. What each slide *means*: `slide_guide.md`.

## How to record (no paid tools needed)

1. Open the deck in **Present** mode, or download it as **.pptx** (Share › Export).
2. Record your screen and voice. Any of these work:
   - In PowerPoint, **Slide Show › Record**, then File › Export › Create a Video.
   - On Windows, **Snipping Tool › Record**, or press `Win + Shift + R`.
   - In Zoom, start a meeting by yourself, share the screen and press Record.
3. Do one test run and check the length is under 5:00. Several teammates can split the slides.

---

**Slide 1, Title (0:00)**

**Say:** Every week Grants.gov posts hundreds of federal grants, and the states that find the right ones first get the money. We built a tool that narrows 1,662 listings down to the 15 that NC DHHS should act on.

*Background:* Data: the competition's Grants.gov export of 1,662 listings, pulled 18 Aug 2026; all dates are measured as of 30 Sep 2026. Agency: NC Department of Health and Human Services. 947 of the 1,662 listings come from the federal Department of Health and Human Services.

**Slide 2, Our user (0:16)**

**Say:** Our user is the DHHS federal-grants coordinator, who decides which postings deserve a division's time. We defined a good match up front: DHHS can lead or partner; it serves one of the five goals in the DHHS strategic plan; one of its 13 divisions already does this work; there's time to apply; and the award is worth it.

*Background:* The 5 goals and 20 objectives come from the DHHS Strategic Plan 2023-2025 (health access; child and family well-being; behavioral health; workforce; operational excellence). The 13 divisions include Public Health, Mental Health/DD/Substance Use, Medicaid, Child and Family Well-Being, Social Services, Aging, Child Development and Early Education, and Rural Health. These 5 criteria map directly onto the formula weights on slide 8.

**Slide 3, The problem (0:41)**

**Say:** The data has 1,662 listings. Keyword matching misleads: 609 of the 689 NIH research grants list states as eligible, but they're built for universities. And 559 listings, a third, haven't even opened yet.

*Background:* 559 of 1,662 = 34% are forecasts. 1,040 summaries contained raw HTML that we had to clean. 114 award amounts were $0 and 3 were placeholders such as $999,999,999, all treated as 'unknown' rather than real money.

**Slide 4, The whole funnel (0:55)**

**Say:** Here's the whole system, to scale. Python rules keep 1,303. Jev, a fast AI, keeps 283, about one in five. DeepSeek, a stronger AI, scores them with evidence. A formula picks the 15 worth acting on: under one percent.

*Background:* Percentages: 1,303 / 1,662 = 78% survive the rules; 283 / 1,303 = 22% survive Jev; 15 / 1,662 = 0.9% end up on the action lists. Total AI cost for the whole run: $3.36. Rerunning everything from saved answers takes about 11 seconds and needs no API key.

**Slide 5, Step 1: Python rules (1:12)**

**Say:** Step one is plain Python, no AI. It removes only what's objectively dead: 330 already closed, 17 paperwork notices and 12 archived. It also scores deadline and award size on a fixed zero-to-ten scale.

*Background:* Of the 1,303 kept: 744 are open and 559 are forecasts. Among open grants: 77 close within 7 days, 142 within 30, 505 have a comfortable deadline, and 97 have no deadline (66 of them 'accepted anytime'). Award scale is logarithmic: $100K = 0, $1M = 5, $10M+ = 10. 511 kept grants state no award amount, so they get a neutral 5. Paperwork notices are records like 'RFA-TS-18-000' that only transfer existing awards.

**Slide 6, Step 2: Jev screen (1:26)**

**Say:** Step two is Jev, a small, fast AI from TypeSafe. Instead of writing text, it answers multiple-choice questions with a probability for each option: is this DHHS's work, which goal, can DHHS apply, who owns it. It screened all 1,303 in about a minute for a few cents, keeping 283.

*Background:* Jev runs through the Vercel AI Gateway (model 'typesafe-ai/jev'); price about $0.04 per million input tokens (word pieces), no output charge. Answers across 1,303: relevance strong 102, moderate 21, weak 838, none 342. Role: lead 29, partner 166, unusual fit 844, ineligible 259. Set-aside rules: P(unrelated) >= 85%, or P(unrelated or weak) >= 95%, or P(ineligible) >= 90%. That set aside 997 as off-topic/weak and 23 as ineligible. Of the 283 kept, 129 point to Public Health and 95 to the health-access goal.

**Slide 7, Step 3: DeepSeek review (1:48)**

**Say:** Step three is DeepSeek V4 Pro, a large language model from the Chinese AI lab DeepSeek. Unlike Jev it reasons in full sentences: slower, about 30 seconds a grant, but thorough. It scored each of the 283 and named the owner, risk and reason, backing every claim with an exact quote. Python checked them: 282 of 283 matched.

*Background:* Also via the Vercel AI Gateway (model 'deepseek/deepseek-v4-pro'), run 12 grants at a time; the Layer 3 run cost about $3. We originally used Meta's Muse Spark, but Meta blocked our account after 62 grants (slide 13); DeepSeek was chosen after a test on the 8 most sensitive grants: 8/8 valid answers, 8/8 quotes verified, 100% agreement with Muse on role and division. Results across 283: average strategic fit 5.6/10; it recommended 125 for review; eligibility quotes verified 280/283.

**Slide 8, Step 4: Formula ranks (2:12)**

**Say:** Step four is a published formula, not AI: fit 30 percent, ability to run it 25, and award, deadline and eligibility 15 each. Title X scores ten on everything but one nine: 97.5. Out come three lists: 33 open now, 116 opening soon, and 134 research grants.

*Background:* Worked example, Title X: 10x0.30 + 9x0.25 + 10x0.15 + 10x0.15 + 10x0.15 = 9.75, times 10 = 97.5 (shown as 98). Rules on top: proven ineligible = 0; unverified strategic quote = -5; no deadline = -3 (-2 if 'apply anytime', 0 if first-come-first-served). Scores of 80+: 3 of 33 open, 36 of 116 forecasts, 8 of 134 research. Research grants are split off by an objective rule: an NIH-style code like R01 in the title.

**Slide 9, Result 1: apply now (2:33)**

**Say:** The top open grant is Title X Family Planning, 98 out of 100. Public Health would own it, DHHS can lead, it's due January 11, and up to 22 million dollars is available. Federal records show NC DHHS has already won 14.7 million dollars under this program.

*Background:* Title X: deadline 11 Jan 2027 (103 days after 30 Sep). Nationally, state agencies received 42% of the $0.52B awarded under this program (assistance listing 93.217) in FY2022-25. Main risk the AI flagged: the FY2027 amount depends on the federal budget.

**Slide 10, Result 2: prepare now (2:53)**

**Say:** The bigger money is opening soon. Four of the top five forecasts are programs NC DHHS has already won, about 275 million dollars in four years. Ryan White and Preschool Development may already be open, so check today.

*Background:* NC DHHS awards FY2022-25 (USAspending.gov): Ryan White Part B $187.6M (state agencies got 76% of $5.1B nationally); Preschool Development B-5 $36.3M (82% to states); HIV Behavioral Surveillance $30.2M; MIECHV home visiting $21.1M (73% to states). Total $275.2M. 'May already be open' = the forecast post date has passed but the close date has not.

**Slide 11, Why not keyword search (3:09)**

**Say:** Why not keyword search? We built it as a baseline. Out of 1,303 grants it ranks Ryan White 670th and Title X 134th, and its number one pick is a grant only tribes can apply for. Jev set that one aside with 99 percent confidence.

*Background:* Baseline = TF-IDF word similarity between each grant and the strategic-plan text. Of the keyword method's top 20, Jev set aside 6, and all 6 were correct: 4 open only to tribal or urban Indian organizations, 2 NIH research programs.

**Slide 12, How confident to be (3:28)**

**Say:** How much should you trust this? The strongest check uses no AI: federal spending records. Grants Jev set aside had paid state agencies 2 percent of the time, against 25 percent for the ones it kept. Quotes check out, two AIs agree 87 percent of the time, and a small human check points the same way. Trust the watchlist most.

*Background:* Track record = NC DHHS received at least $100K, or state agencies received 25%+ of the program's dollars (USAspending.gov, FY2022-25, 816 cached queries). We read all 24 set-aside grants with any state history; none was a genuine DHHS miss (e.g. one was the Pacific-territories-only version of Ryan White). Two-AI agreement: Muse Spark vs DeepSeek on 60 grants: role 87%, division 95%. Human check: 31 grants, 8 relevant; Jev kept 7 (93%, 95% range 67-100%); keyword search 71%. Small sample: say 'points the same way', not 'proves'.

**Slide 13, Where the AI was wrong (3:54)**

**Say:** The AI was wrong three ways. DeepSeek called 73 university research grants DHHS-led, filling 7 of our first top 10; Jev disagreed, which exposed it. DeepSeek once cited the single word "states" as proof, and our check rejected it. And Meta's AI blocked our HIV and overdose text, so we switched vendors.

*Background:* Research grants moved to their own list: 134. The 'states' case: 'Partnership for Disaster Health Response System'; the role was downgraded to 'unclear' automatically. Meta block: 'repeated policy violations' after 62 of 283 grants; we tested 3 replacement models on the 8 most sensitive grants. All failures are in docs/failure_modes.md (10 entries) and data/results/ai_error_log.csv.

**Slide 14, Three things to do this week (4:16)**

**Say:** Our recommendation: check Ryan White and Preschool Development B-5 on Grants.gov today, send Title X to Public Health before its January 11 deadline, and pass the 134 research grants to a university partner. The limits: August data, the 2023 to 2025 plan, and a small human check. Thank you.

*Background:* With more time: a weekly automatic run on the live Grants.gov feed that emails the coordinator new matches; use the award track record as a scoring input; labels from real DHHS grants officers; two AI vendors in parallel. The whole run cost $3.36 and reruns in about 11 seconds.

*(spoken part ends about 4:37)*

---

## What Jev and DeepSeek are, if anyone asks

- **Jev** (TypeSafe AI, model `typesafe-ai/jev`) is a small, fast *decision* model. Instead of writing text, it answers multiple-choice questions about a piece of information and returns a probability for every option. That makes it cheap (about $0.04 per million input tokens) and fast (all 1,303 grants in about a minute), and it gives us a built-in confidence number. We use it to screen.
- **DeepSeek V4 Pro** (DeepSeek, model `deepseek/deepseek-v4-pro`) is a full large language model that reasons in sentences, like ChatGPT. It's slower (about 30 s per grant) and costs more, so it only reads the 283 grants Jev keeps. It writes the scores, reasons and risks, with exact quotes we verify in code. It replaced Meta's Muse Spark, which blocked our account.
- Both are reached through the **Vercel AI Gateway**, one API key that connects to many model providers. Every answer is saved, so the whole pipeline reruns in about 11 seconds without calling any AI.

## If an evaluator asks (every member should be able to answer)

- **Why two AI models?** The fast one (Jev) screens all 1,303 grants cheaply. The careful one (DeepSeek) writes evidence only for the 283 that matter. Neither ranks; the formula does.
- **Why trust the scores?** The weights are published (30/25/15/15/15), and every input is in `data/results/ranked_grants.csv`.
- **What if the AI makes things up?** Every quote is checked against the grant text. An unproven eligibility claim becomes "unclear", and only proven ineligibility zeroes a score.
- **Why is the open list weak?** Most programs DHHS traditionally wins closed between the August 18 data pull and September 30, or haven't opened yet. That's why the watchlist matters.
- **Does the screen throw away good grants?** Set-aside grants had state-agency award history 2% of the time, against 25% for kept ones. We read all 24 set-asides with any state-award history, and none was a genuine DHHS miss (`docs/failure_modes.md`, F9).
