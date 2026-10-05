# Recording script: 5 minutes or less, addressed to NC DHHS leadership

A recording of **5 minutes or less** is preferred (a PowerPoint is accepted instead). Read the text below as written: **683 words, about 4.9 minutes** at a calm 140 words per minute (about 4.4 at a normal pace). It is identical to each slide's speaker notes. Extra numbers for questions: `slide_guide.md` and `docs/team_briefing.md`.

## How to record (no paid tools needed)

1. Open the deck in **Present** mode, or download it as **.pptx** (Share › Export).
2. Record your screen and voice. Any of these work:
   - In PowerPoint, **Slide Show › Record**, then File › Export › Create a Video.
   - On Windows, **Snipping Tool › Record**, or press `Win + Shift + R`.
   - In Zoom, start a meeting by yourself, share the screen and press Record.
3. Do one test run and check the length is under 5:00. Several teammates can split the slides.

---

**Slide 1, Title (0:00)**

Grants.gov posts hundreds of federal grants a week, and the states that spot the right ones first win the money. Our tool takes 1,662 listings and narrows them to the 15 NC DHHS should act on.

**Slide 2, Our user (0:15)**

Our user is the DHHS federal-grants coordinator, who decides which grants deserve a division's time. Before looking at any data, we defined a good grant: DHHS can apply; it supports one of the five strategic-plan goals; one of DHHS's thirteen divisions already does this work; there's time to apply; and the money is worth it.

**Slide 3, The problem (0:39)**

Nobody can read 1,662 listings, and keyword search gets fooled: 609 of 689 NIH research grants say states can apply, but they're built for universities. And a third of the listings haven't even opened yet.

**Slide 4, The whole funnel (0:54)**

Here's the system, with the bars to scale. Python rules cut 1,662 listings to 1,303. A fast AI called Jev cuts that to 283, about one in five. A stronger AI, DeepSeek, reads those closely. And a fixed formula picks the final 15.

**Slide 5, Step 1: Python rules (1:12)**

Step one is plain code, no AI. It removes only what's clearly dead: 330 closed, 12 archived, and 17 paperwork notices. It also scores two facts from zero to ten: time left to apply, and award size.

**Slide 6, Step 2: Jev screen (1:28)**

Step two is Jev, a small, fast AI from TypeSafe. Instead of writing paragraphs, it answers multiple-choice questions and says how confident it is. For each grant: is this DHHS's work, which goal, can DHHS apply, and which division owns it. It screened all 1,303 in about a minute for a few cents, and only set a grant aside when at least 85 percent sure. 283 moved on.

**Slide 7, Step 3: DeepSeek review (1:57)**

Step three is DeepSeek, a large language model like ChatGPT. It's slower, about 30 seconds a grant, but reads each one in full. For all 283, it scores strategic fit and whether DHHS could run it, names the owning division, and writes the main risk and a reason. Every claim needs an exact quote, which our code checks: 282 of 283 matched.

**Slide 8, Step 4: Formula ranks (2:24)**

Step four decides, and it's a formula, not AI: strategic fit 30 percent, can DHHS run it 25, and award size, deadline and eligibility 15 each. Title X scores a nine on one and tens on the rest: 97.5. That gives three lists: 33 open now, 116 opening soon, and 134 research grants for a university partner.

**Slide 9, Result 1: apply now (2:48)**

The best open grant is Title X Family Planning, scoring 98. Public Health would own it, DHHS can lead, it's due January 11th with up to 22 million dollars, and NC DHHS has already won 14.7 million from this program.

**Slide 10, Result 2: prepare now (3:05)**

The biggest money is opening soon. Four of the top five upcoming grants are programs NC DHHS has already won, about 275 million dollars in four years. Ryan White HIV care and Preschool Development may already be open, so check today.

**Slide 11, Why not keyword search (3:23)**

Why not keyword search? We tried it. It ranks Ryan White 670th and Title X 134th, and its top pick is a grant only tribes can apply for. Jev set that one aside with 99 percent confidence.

**Slide 12, How confident to be (3:39)**

How much should you trust this? Our strongest check uses no AI: federal spending records. Grants Jev set aside came from programs that pay state agencies just 2 percent of the time; grants it kept, 25 percent. And 282 of 283 quotes were real, two AI models agreed on DHHS's role 87 percent of the time, and a small human check agreed.

**Slide 13, Where the AI was wrong (4:05)**

The AI did make mistakes, and we caught them. DeepSeek said DHHS would lead 73 university research grants, 7 of our first top 10. Jev disagreed, which flagged it, so a rule now moves research grants to their own list. DeepSeek once offered the single word 'states' as proof, and our check rejected it. And Meta's AI blocked us over HIV topics, so we switched.

**Slide 14, Three things to do this week (4:33)**

This week: check Grants.gov for Ryan White and Preschool Development, send Title X to Public Health before January 11th, and pass the 134 research grants to a university partner. Our limits: August data, the 2023 to 2025 plan, and a small human check. Thank you.

*(spoken part ends about 4:52)*

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
