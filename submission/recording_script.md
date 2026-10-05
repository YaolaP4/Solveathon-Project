# Recording script: 5 minutes or less, addressed to NC DHHS leadership

The competition prefers a recording of **5 minutes or less**; a PowerPoint is accepted instead. This script is **544 words, about 3.9 minutes** at a calm pace, so pauses fit comfortably. Each slide's text is also in its speaker notes in the deck. What each slide *means* is in `slide_guide.md`.

## How to record (no paid tools needed)

1. Open the deck in **Present** mode, or download it as **.pptx** (Share › Export).
2. Record your screen and voice. Any of these work:
   - In PowerPoint, **Slide Show › Record**, then File › Export › Create a Video.
   - On Windows, **Snipping Tool › Record**, or press `Win + Shift + R`.
   - In Zoom, start a meeting by yourself, share the screen and press Record.
3. Do one test run and check the length is under 5:00. Several teammates can split the slides.

---

**Slide 1, Title (0:00)**  
Every week Grants.gov posts hundreds of federal grants, and the states that find the right ones first get the money. We built a tool that finds them for NC DHHS.

**Slide 2, Our user (0:12)**  
Our user is the DHHS federal-grants coordinator, who decides which postings deserve a division's time. We defined a good match up front: DHHS can lead or partner; it serves a strategic-plan goal; a division already does this work; there's time to apply; and the award is worth it.

**Slide 3, The problem (0:33)**  
The data has 1,662 listings. Keyword matching fails: most NIH research grants list states as eligible but are built for universities, and 559 listings haven't even opened yet.

**Slide 4, The whole funnel (0:45)**  
Here's the whole system, drawn to scale. Python rules remove 359 dead listings. Jev, a fast AI, keeps 283 of the rest. DeepSeek, a stronger AI, scores those 283 with evidence. A fixed formula picks the 15 worth acting on.

**Slide 5, Step 1: Python rules (1:02)**  
Step one is plain Python, no AI. It removes only what's objectively dead: closed, archived or paperwork. It also scores deadline and award size on a fixed scale.

**Slide 6, Step 2: Jev screen (1:14)**  
Step two: Jev asks four multiple-choice questions about every grant: is it DHHS's kind of work, which goal, can DHHS apply, and who would own it. It sets a grant aside only when it's very sure. 283 go on.

**Slide 7, Step 3: DeepSeek review (1:31)**  
Step three: DeepSeek reads those 283 in full. It scores fit and whether DHHS can run it, names the owner, and writes the risk and a reason. Every claim needs an exact quote, and Python checks them: 282 of 283 matched.

**Slide 8, Step 4: Formula ranks (1:48)**  
Step four is a published formula, not AI: fit 30 percent, ability to run it 25, and award, deadline and eligibility 15 each. Out come three lists: open now, opening soon, and research for a university partner.

**Slide 9, Result 1: apply now (2:04)**  
The top open grant is Title X Family Planning, 98 out of 100. Public Health would own it, DHHS can lead, it's due January 11, and NC DHHS has won 14.7 million dollars under it before.

**Slide 10, Result 2: prepare now (2:20)**  
The bigger money is opening soon. Four of the top five forecast grants are programs DHHS has already won, about 275 million dollars in four years. Ryan White and Preschool Development may already be open.

**Slide 11, Why not keyword search (2:35)**  
Why not keyword search? We built it as a baseline. It ranks Ryan White 670th and Title X 134th, and its number one result is a grant only tribes can apply for. Ours caught that.

**Slide 12, How confident to be (2:50)**  
How much to trust it? The strongest check uses no AI: federal spending records. Grants Jev set aside had paid state agencies 2 percent of the time, against 25 percent for those it kept. Quotes check out, two AIs agree 87 percent of the time, and a small human check agrees. Trust the watchlist most.

**Slide 13, Where the AI was wrong (3:13)**  
The AI was wrong three ways. DeepSeek called 73 research grants DHHS-led; Jev disagreed, which exposed it, and a rule now moves them aside. It once cited the single word "states" as proof, and our check rejected it. And Meta's AI blocked our HIV and overdose text, so we switched vendors.

**Slide 14, Three things to do this week (3:35)**  
Our recommendation: check Ryan White and Preschool Development B-5 today, send Title X to Public Health, and pass the research grants to a university partner. The limits: August data, the 2023 to 2025 plan, and a small human check. Thank you.

*(ends about 3:53)*

---

## If an evaluator asks (every member should be able to answer)

- **Why two AI models?** The fast one (Jev) screens all 1,303 grants cheaply. The careful one (DeepSeek) writes evidence only for the 283 that matter. Neither ranks; the formula does.
- **Why trust the scores?** The weights are published (30/25/15/15/15), and every input is in `data/results/ranked_grants.csv`.
- **What if the AI makes things up?** Every quote is checked against the grant text. An unproven eligibility claim becomes "unclear", and only proven ineligibility zeroes a score.
- **Why is the open list weak?** Most programs DHHS traditionally wins closed between the August 18 data pull and September 30, or haven't opened yet. That's why the watchlist matters.
- **Does the screen throw away good grants?** Set-aside grants had state-agency award history 2% of the time, against 25% for kept ones. We read all 24 set-asides with any state-award history, and none was a genuine DHHS miss (`docs/failure_modes.md`, F9).

