# Recording script: 5 minutes or less, addressed to NC DHHS leadership

A recording of **5 minutes or less** is preferred (a PowerPoint is accepted instead). Read the text below as written: **1577 words, about 11.3 minutes** at a calm 140 words per minute (about 10.2 at a normal pace). It is identical to each slide's speaker notes. Extra numbers for questions: `slide_guide.md` and `docs/team_briefing.md`.

## How to record (no paid tools needed)

1. Open the deck in **Present** mode, or download it as **.pptx** (Share › Export).
2. Record your screen and voice. Any of these work:
   - In PowerPoint, **Slide Show › Record**, then File › Export › Create a Video.
   - On Windows, **Snipping Tool › Record**, or press `Win + Shift + R`.
   - In Zoom, start a meeting by yourself, share the screen and press Record.
3. Do one test run and check the length is under 5:00. Several teammates can split the slides.

---

**Slide 1, Title (0:00)**

Every week, hundreds of new federal grants are posted on Grants.gov. Somewhere in that pile is money North Carolina could win, but nobody has time to read it all, and the states that find the right postings first are the ones that get funded. We built a tool for NC DHHS that takes all 1,662 listings in our dataset and narrows them down to the 15 that are actually worth acting on, with a reason for each one.

**Slide 2, Our user (0:33)**

We designed this for one person: the DHHS federal-grants coordinator. Every week, they decide which new grants deserve a division's time, and send each one to the right team. Before touching the data, we used the DHHS strategic plan to define what a good grant means for them. One: DHHS has to be able to apply, as the lead or as a partner. Two: it should support one of the plan's five goals, like health access or behavioral health. Three: one of DHHS's thirteen divisions should already do this kind of work, so they could actually run it. Four: there has to be enough time to apply, because a state agency needs weeks for internal sign-off. And five: the money has to be worth the effort. Everything else in our system measures these five things.

**Slide 3, The problem (1:31)**

Here's why this is hard. First, 1,662 listings is far more than one person can read. Second, the obvious shortcut, searching for health keywords, gets fooled, because many grants sound relevant but aren't meant for a state agency. For example, 609 of the 689 NIH research grants list state governments as eligible, only because they list almost every type of applicant. They're really built for university researchers. Third, 559 listings, about a third, are forecasts: programs that have been announced but haven't opened yet. Most tools skip those, but they're the earliest warning you can get.

**Slide 4, The whole funnel (2:12)**

So we built a pipeline where each step has one job. The bars are drawn to scale. Step one, plain Python rules, removes listings that are objectively dead and leaves 1,303. Step two, a fast AI called Jev, screens all of those and keeps 283, about one in five. Step three, a stronger AI called DeepSeek, reads those 283 closely and writes evidence for each. Step four, a fixed formula, scores and ranks them, and gives us the final 15. The principle: plain code for facts, AI only where something needs to be read, and a transparent formula for the final decision.

**Slide 5, Step 1: Python rules (2:56)**

Step one uses no AI at all, because things like whether a deadline has passed are facts, and we don't want an AI guessing at facts. The code removes only listings that are clearly dead: 330 that had already closed, 12 that were archived, and 17 that aren't real grants, just paperwork for transferring existing awards. Anything uncertain stays in. It also scores two facts from zero to ten. Deadline: a grant closing within a week scores near zero, because DHHS couldn't get sign-off in time, and one with two months or more scores ten. Award size uses a log scale, so a ten-million-dollar grant can't drown out a better-fitting one-million-dollar grant. It also cleans up junk data, like awards listed as 999,999,999 dollars.

**Slide 6, Step 2: Jev screen (3:49)**

Step two is Jev, an AI model from a company called TypeSafe. Jev is different from something like ChatGPT: it doesn't write paragraphs. You give it information and multiple-choice questions, and it picks an answer and tells you how confident it is in every option. That makes it fast and cheap: it screened all 1,303 grants in about a minute, for a few cents. We ask it four questions per grant: is this DHHS's kind of work, which strategic goal does it serve, can DHHS apply as lead or partner, and which division would own it. Since missing a good grant is worse than keeping a bad one, Jev only sets a grant aside when it's at least 85 to 95 percent sure. That removed 1,020 grants, almost all off-topic, and 283 moved on.

**Slide 7, Step 3: DeepSeek review (4:46)**

Step three is DeepSeek V4 Pro, a large language model similar to ChatGPT. Unlike Jev, it reasons in full sentences, so it's slower and costs more, about 30 seconds per grant, which is why it only reads the 283 that Jev kept. For each one, it reads the full description and eligibility rules. It scores how well the grant fits DHHS's goals and whether DHHS could realistically run it, names the division that would own it, and writes the biggest risk and a one-line reason for leadership. AI models can make things up, so we made DeepSeek back every claim with an exact quote from the grant, and our code checks each quote against the real text. 282 of 283 checked out, and any claim it can't prove gets downgraded automatically.

**Slide 8, Step 4: Formula ranks (5:42)**

Step four is where the decision actually happens, and it's a formula, not AI, so anyone can check how a score was made. Strategic fit counts 30 percent and whether DHHS can run the program counts 25, because those matter most to the coordinator. Award size, deadline and eligibility count 15 percent each. A few rules sit on top: a grant DHHS is proven ineligible for gets a zero, and a claim the AI couldn't back up with a quote loses points. Title X, for example, gets a nine on whether DHHS can run it and tens on everything else, which works out to 97.5 out of 100. Finally, the formula splits everything into three lists: 33 grants open right now, 116 opening soon, and 134 research grants that suit a university partner better than DHHS.

**Slide 9, Result 1: apply now (6:41)**

So what did we find? The best grant open right now is Title X Family Planning, scoring 98. It funds family planning services, a specific goal in the DHHS plan. The Division of Public Health would own it, and DHHS can apply as the lead, which we confirmed from the grant's own eligibility text. It's due January 11th and offers up to 22 million dollars. And federal spending records show NC DHHS has already won 14.7 million dollars from this same program, so it's a proven fit.

**Slide 10, Result 2: prepare now (7:18)**

But the bigger opportunity is in grants that haven't opened yet. Four of our top five upcoming grants are programs NC DHHS has won before, together about 275 million dollars over the last four years. The biggest is Ryan White HIV care, at 187.6 million. Two of these, Ryan White and Preschool Development, had expected opening dates that have already passed, which means they may be open on Grants.gov right now. That's exactly the early warning that helps a state get there first.

**Slide 11, Why not keyword search (7:54)**

You might ask why we didn't just search for keywords. We built that as a comparison, matching each grant's wording against the strategic plan. It ranks Ryan White, a 187-million-dollar DHHS program, at number 670, and Title X at 134, because their descriptions don't happen to use the plan's exact words. Worse, its number one result is a behavioral health program that only tribes can apply for. The words match perfectly, but DHHS can't apply. Jev caught that and set it aside with 99 percent confidence. That's why reading eligibility matters more than matching words.

**Slide 12, How confident to be (8:34)**

So how much should you trust this? We used four checks. The strongest uses no AI at all: we looked up federal spending records to see who has actually received money from each program over the last four years. Among grants Jev set aside, only 2 percent came from programs that regularly pay state agencies. Among grants it kept, 25 percent did. So the screen is keeping the right kind of grants. Second, 282 of 283 AI quotes were found word for word. Third, two different AI models agreed on DHHS's role 87 percent of the time. And fourth, a small hand-labeled check of 31 grants points the same way, though it's too small to prove anything on its own. Our honest advice: trust the watchlist the most.

**Slide 13, Where the AI was wrong (9:29)**

The AI did make mistakes, and here's how we caught them. First, DeepSeek said DHHS would lead 73 university research grants, just because state governments were listed as eligible. At one point, those filled 7 of our top 10. We caught it because Jev disagreed on every single one, and our system logs those disagreements. So we added a simple rule: grants with research codes, like R01, go to their own list. Second, DeepSeek once claimed DHHS could lead a grant and offered the single word 'states' as proof. Our quote check rejected that automatically. Third, Meta's AI model blocked our account entirely, because DHHS grants talk about HIV, STIs and overdoses. Our system can swap models with one setting, so we switched to DeepSeek. The lesson for DHHS: don't depend on a single AI vendor.

**Slide 14, Three things to do this week (10:27)**

So here's what we recommend doing this week. First, check Grants.gov for Ryan White and Preschool Development, since they may already be open. Second, send Title X to the Division of Public Health before its January 11th deadline. Third, pass the 134 research grants to a university partner like UNC, who may want DHHS as a partner or data source. We also want to be upfront about our limits: the data is a snapshot from August, strategic fit is based on the 2023 to 2025 plan, and our human check was small. With more time, we'd run this automatically every week on live data and email the coordinator new matches. Thank you.

*(spoken part ends about 11:15)*

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
