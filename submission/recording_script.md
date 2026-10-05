# Recording script: 5 minutes or less, addressed to NC DHHS leadership

A recording of **5 minutes or less** is preferred (a PowerPoint is accepted instead). Read the text below as written: **1103 words, about 7.9 minutes** at a calm 140 words per minute (about 7.1 at a normal pace). It is identical to each slide's speaker notes. Extra numbers for questions: `slide_guide.md` and `docs/team_briefing.md`.

## How to record (no paid tools needed)

1. Open the deck in **Present** mode, or download it as **.pptx** (Share › Export).
2. Record your screen and voice. Any of these work:
   - In PowerPoint, **Slide Show › Record**, then File › Export › Create a Video.
   - On Windows, **Snipping Tool › Record**, or press `Win + Shift + R`.
   - In Zoom, start a meeting by yourself, share the screen and press Record.
3. Do one test run and check the length is under 5:00. Several teammates can split the slides.

---

**Slide 1, Title (0:00)**

Every week, hundreds of new federal grants are posted, and the states that find the right ones first get funded. Our tool takes all 1,662 listings in our dataset and narrows them to the 15 NC DHHS should act on, with a reason for each.

**Slide 2, Our user (0:19)**

We designed this for one person: the DHHS federal-grants coordinator, who decides each week which grants deserve a division's time. Before touching the data, we used the DHHS strategic plan to define a good grant. DHHS has to be able to apply, as the lead or as a partner. It should support one of the plan's five goals. One of DHHS's thirteen divisions should already do this kind of work, so they could actually run it. There has to be enough time to apply, because state agencies need weeks for sign-off. And the money has to be worth the effort.

**Slide 3, The problem (1:02)**

This is hard for three reasons. First, 1,662 listings is too many to read. Second, keyword search gets fooled, because many grants sound relevant but aren't meant for a state. For example, 609 of the 689 NIH research grants list state governments as eligible, just because they list almost everyone, but they're really built for universities. Third, about a third of the listings are forecasts that haven't opened yet, and those are the earliest warning you can get.

**Slide 4, Step 1: Python rules (1:35)**

Our system runs in four steps, shown along the top. Step one uses no AI, because things like whether a deadline has passed are facts. Plain code removes only what's clearly dead: 330 closed listings, 12 archived, and 17 that are just paperwork for existing awards. That leaves 1,303. It also scores two facts from zero to ten. Time to apply, where under a week scores near zero because DHHS couldn't get sign-off in time. And award size, on a log scale, so one huge award can't drown out a better-fitting smaller one.

**Slide 5, Step 2: Jev screen (2:15)**

Step two is Jev, an AI from a company called TypeSafe. Unlike ChatGPT, Jev doesn't write paragraphs. It answers multiple-choice questions and tells you how confident it is in each answer, which makes it fast and cheap. It screened all 1,303 grants in about a minute, for a few cents. It asks four things: is this DHHS's kind of work, which goal does it serve, can DHHS apply, and which division would own it. Since missing a good grant is worse than keeping a bad one, Jev only sets a grant aside when it's at least 85 percent sure. 283 moved on.

**Slide 6, Step 3: DeepSeek review (2:59)**

Step three is DeepSeek, a large language model similar to ChatGPT. It reasons in full sentences, so it's slower, about 30 seconds a grant, which is why it only reads the 283 that Jev kept. For each one, it scores how well the grant fits DHHS's goals and whether DHHS could realistically run it, names the division that would own it, and writes the main risk and a one-line reason. Because AI can make things up, it has to back every claim with an exact quote from the grant, and our code checks each one. 282 of 283 checked out,.

**Slide 7, Step 4: Formula ranks (3:42)**

Step four makes the decision, and it's a formula, not AI, so anyone can check how a score was made. Strategic fit counts 30 percent and whether DHHS can run the program counts 25, because those matter most. Award size, deadline and eligibility count 15 each. A grant DHHS is proven ineligible for gets a zero, and claims the AI couldn't prove lose points. Title X, for example, gets a nine on one score and tens on the rest, which works out to 97.5. The result is three lists: 33 grants open now, 116 opening soon, and 134 research grants better suited to a university partner.

**Slide 8, Result 1: apply now (4:27)**

So what did we find? The best grant open right now is Title X Family Planning, scoring 98. It funds family planning services, a specific goal in the DHHS plan. Public Health would own it, and DHHS can apply as the lead, which we confirmed from the grant's own eligibility text. It's due January 11th, offers up to 22 million dollars, and NC DHHS has already won 14.7 million from this same program.

**Slide 9, Result 2: prepare now (4:58)**

The bigger opportunity is in grants that haven't opened yet. Four of our top five upcoming grants are programs NC DHHS has won before, about 275 million dollars over four years, led by Ryan White HIV care at 187.6 million. Ryan White and Preschool Development had expected opening dates that have already passed, so they may be open on Grants.gov right now.

**Slide 10, Why not keyword search (5:25)**

So why not just search for keywords? We built that as a comparison. It ranks Ryan White 670th and Title X 134th, because their descriptions don't happen to use the plan's exact words. And its number one pick is a behavioral health program that only tribes can apply for. The words match perfectly, but DHHS can't apply. Jev set it aside with 99 percent confidence. Reading eligibility beats matching words.

**Slide 11, How confident to be (5:55)**

How much should you trust this? Our strongest check uses no AI: federal spending records on who actually received money from each program. Among grants Jev set aside, only 2 percent came from programs that regularly pay state agencies. Among grants it kept, 25 percent did, so the screen keeps the right kind of grants. On top of that, 282 of 283 quotes were real, two different AI models agreed on DHHS's role 87 percent of the time, and a small hand-labeled check of 31 grants points the same way. Our advice: trust the watchlist most.

**Slide 12, Where the AI was wrong (6:36)**

The AI did make mistakes, and here's how we caught them. DeepSeek said DHHS would lead 73 university research grants, just because states were listed as eligible, and at one point they filled 7 of our top 10. Jev disagreed on every one, so we caught it and added a rule that moves research grants to their own list. DeepSeek also once offered the single word 'states' as proof, and our quote check rejected it. And Meta's AI blocked our account over HIV and overdose topics, so we switched models with a single setting.

**Slide 13, Three things to do this week (7:16)**

So this week, we recommend three things. Check Grants.gov for Ryan White and Preschool Development, since they may already be open. Send Title X to Public Health before January 11th. And pass the 134 research grants to a university partner like UNC. Our limits: the data is from August, strategic fit is based on the 2023 to 2025 plan, and our human check was small. With more time, we'd run this every week on live data and email the coordinator new matches. Thank you.

*(spoken part ends about 7:52)*

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
