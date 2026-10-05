# Recording script: 5 minutes or less, addressed to NC DHHS leadership

The competition prefers a recording of **5 minutes or less**; a PowerPoint is accepted instead. Record the slide deck with your voice over it. The script below is about **640 words, roughly 4 minutes 15 seconds** at a normal pace, which leaves room for pauses. The same text is in each slide's speaker notes.

## How to record (no paid tools needed)

1. Open the deck and use **Present** mode, or download it as **.pptx** (Share › Export).
2. Record your screen and voice. Any of these work:
   - In PowerPoint (the .pptx), **Slide Show › Record**, which records narration per slide and exports to MP4 under File › Export › Create a Video.
   - On Windows, **Snipping Tool › Record**, or press `Win + Shift + R`.
   - In Zoom, start a meeting by yourself, share the screen and press Record.
3. Read the script at a calm pace, and change slides at each heading. Do a test run first, then check the length is under 5:00.
4. If several teammates speak, split the script by slide. The rules say every member should be able to explain the approach.

---

**Slide 1, Title (0:00)**
Every week Grants.gov posts hundreds of federal funding opportunities, and the states that find the right ones first get the money. We built a tool for one person, the NC DHHS federal-grants coordinator, that turns that pile into a short, trustworthy list.

**Slide 2, Our user (0:15)**
Our user is the DHHS federal-grants coordinator, who decides each week which postings deserve a division's time. Before touching the data, we defined a good match: DHHS can lead or partner, which is a gate; it advances a strategic-plan goal; a division already does this work; there's time to apply; and the award is worth the effort.

**Slide 3, The problem (0:40)**
The starter data alone has 1,662 listings. Keywords aren't enough: 609 of 689 NIH research grants list state governments as eligible, but they're built for universities. And 559 are forecasts that haven't opened yet. The real question is which grants DHHS can actually win.

**Slide 4, Apply now (1:00)**
The one open grant to act on today is Title X Family Planning, at 98 out of 100. It funds family planning, a stated women's health objective. Public Health would own it, and we verified DHHS is the intended applicant. It's due January 11, and federal spending records show NC DHHS already won 14.7 million dollars under this program.

**Slide 5, Prepare now (1:25)**
The bigger money is in the watchlist of forecast programs. Four of our top five are programs NC DHHS has already won, about 275 million dollars in four years, led by Ryan White HIV care. Ryan White and Preschool Development B-5 may already be open on Grants.gov, so check those today.

**Slide 6, How it works (1:50)**
It works in four steps. First, plain rules remove what's closed, archived or just paperwork, leaving 1,303. Second, a fast AI screen answers four multiple-choice questions per grant and sets one aside only when it's very sure; 283 go on. Third, a stronger model writes the reasons and must quote the grant word for word, and we check every quote. Fourth, a published formula ranks. The AI never ranks. The run cost three dollars and reruns in seconds.

**Slide 7, Why not keywords (2:25)**
Why not keyword search? We built it as a baseline. It ranks Ryan White, a 187-million-dollar DHHS program, 670th, and Title X 134th. Its top result is a program only tribes can apply for, which our screen set aside. Of its top 20, we set aside six, all correctly.

**Slide 8, How confident to be (2:50)**
How much should you trust this? The strongest check uses no AI: federal spending records. Four of five watchlist programs are ones DHHS has won, and grants we set aside had state-agency awards only 2 percent of the time, against 25 percent for those we kept. 282 of 283 AI reasons quote the grant exactly. Two different AI models agreed on DHHS's role 87 percent of the time. A small early human check points the same way but is too small to prove anything. So trust the watchlist most, and check the open list beyond Title X before investing time.

**Slide 9, Where the AI was wrong (3:35)**
The AI was wrong, and here's how we caught it. The review model called 73 NIH research grants DHHS-led; at one point they filled seven of our top ten. The first AI disagreed on every one, which flagged it, and a plain rule now moves them to a university-partner list. It also once cited the single word "states" as proof, and our quote check rejected it. And Meta's model blocked us for HIV and overdose text, so we switched vendors in one setting. Lesson: don't rely on one AI vendor.

**Slide 10, What to do next (4:10)**
This week: check Ryan White and Preschool Development B-5 on Grants.gov, route Title X to Public Health, and send the research list to a university partner. Limitations: the data is from August 18, fit means fit with the 2023 to 2025 plan, and our human check is small. With more time, we'd run this weekly on the live feed and email the coordinator new matches. Thank you.

*(ends about 4:30)*

---

## If an evaluator asks (every member should be able to answer)

- **Why two AI models?** The fast one screens 1,303 grants cheaply. The careful one writes evidence only for the 283 that matter. Neither ranks; the formula does.
- **Why trust the scores?** The weights are published (30/25/15/15/15), and every input is in `data/results/ranked_grants.csv`.
- **What if the AI hallucinates?** Every quote is checked against the grant text. Unverified eligibility claims are downgraded to "unclear", and only verified ineligibility can zero a score.
- **Why is the open list weak?** Most programs DHHS traditionally wins either closed between the August 18 data pull and September 30 or haven't opened yet. That's why the watchlist matters.
- **How do you know the screen doesn't throw away good grants?** Set-aside grants had state-agency award history 2% of the time, against 25% for kept ones. We read all 24 set-asides that had any state-award history, and none was a genuine DHHS miss (`docs/failure_modes.md`, F9).
