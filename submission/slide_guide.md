# Slide guide: what each slide means, in plain language

For the team: what each slide is saying, why it's there, and what to say if a judge asks. Spoken script: `recording_script.md`.

**The big picture in one sentence:** we take 1,662 federal grant listings and narrow them to the 15 that NC DHHS should act on. Plain Python handles the facts, two AIs handle the reading, and a fixed formula makes the final call.

---

### 1. Title: "Find North Carolina's federal health money first"
**Means:** who the tool is for (NC DHHS) and what goes in and comes out (1,662 listings in, a short list with reasons out).

### 2. Our user
**Means:** we designed for one real person, the DHHS federal-grants coordinator who routes grants to divisions, and we wrote down five rules for a good grant *before* looking at the data: DHHS can apply, it serves a strategic-plan goal, a division already does this work, there's time to apply, and the money is worth the effort.
**Why it's there:** the rubric's first criterion is whether the criteria are specific to this agency and user.

### 3. The problem
**Means:** reading 1,662 listings by hand is impossible, and keyword search is misleading. 609 of 689 NIH research grants list "state governments" as eligible even though they're built for universities, and 559 listings are only announcements of future grants.

### 4. Step 1: Python rules, no AI
**The four step labels at the top** of slides 4–7 show where you are and how many grants are left after each step: 1,303 → 283 → 283 scored → top 15.

**Means:** before any AI, plain code removes only what's objectively dead: 330 already closed, 17 paperwork notices (records that just transfer an existing award), and 12 archived. It also scores the two factual criteria on a fixed 0–10 scale:
- **Deadline:** 0 if it closes within days, 10 if 60+ days away.
- **Award size:** $100K → 0, $1M → 5, $10M+ → 10.

It also cleans fake numbers like "$999,999,999".
**Why:** facts shouldn't be left to an AI that might get them wrong.

### 5. Step 2: Jev screens all 1,303
**Means:** Jev is a fast, cheap AI that answers multiple-choice questions and says how sure it is. It answers four questions about every grant: is this DHHS's kind of work, which goal, can DHHS apply, and which division. It throws a grant out only when it's at least 85–95% sure. **283 kept, 1,020 set aside**: 997 as off-topic or only weakly related, and 23 because DHHS can't apply (for example, tribes-only grants).
**Why:** reading everything carefully is expensive, so this screen narrows the pile while erring toward keeping things.

### 6. Step 3: DeepSeek reads the 283
**Means:** DeepSeek is a stronger AI. For each of the 283 grants it writes a fit score, whether DHHS can realistically run it, DHHS's role, the owning division, the main risk and a one-line reason. **It must quote the grant word for word**, and Python checks every quote: 282 of 283 were found exactly. A claim it can't back up is downgraded.
**Key point:** DeepSeek doesn't remove or rank anything. It only explains.

### 7. Step 4: a published formula decides (bar chart of weights)
**Means:** the final score out of 100 is a fixed recipe: strategic fit 30%, can DHHS run it 25%, award size 15%, deadline 15%, eligibility certainty 15%. A few rules sit on top: proven-ineligible scores 0, an unproven quote costs 5 points, and no deadline costs 3. The output is three lists:
- **33 open now**
- **116 opening soon** (forecasts)
- **134 research grants** that suit a university partner

**Why:** anyone can check how a score was made. The AI never picks the winners.

### 8. Result 1: apply now
**Means:** the best grant open today is **Title X Family Planning** (98/100). Public Health would own it, DHHS can lead (verified from the grant text), it's due 11 January 2027 with up to $22M, and federal records show NC DHHS already won $14.7M under it.

### 9. The biggest money is opening soon (watchlist table)
**Means:** the biggest opportunities are **forecasts**, grants announced but not yet open. 4 of the top 5 are programs NC DHHS has already won (about $275M combined in FY2022–25). Two (Ryan White HIV Part B and Preschool Development B-5) had forecast open dates that have passed, so they may be live now.

### 10. Why not just keyword search? (comparison table)
**Means:** we also built the obvious simple method, matching words to the strategic plan, to prove our approach is better. Keyword search ranks Ryan White (a $187.6M DHHS program) **#670**, and its **#1 pick is a grant only tribes can apply for**. Our screen correctly set that one aside.

### 11. How confident should you be? (bar chart + three numbers)
**Means:** four independent checks, strongest first.
1. **Federal spending records (no AI):** grants Jev threw out had a history of paying state agencies only 2% of the time, against 25% for the ones it kept. And 4 of 5 watchlist programs have already paid NC DHHS.
2. **Evidence:** 282 of 283 AI quotes are real.
3. **Two different AIs agree** on DHHS's role 87% of the time.
4. **A small human check** (31 grants) points the same way, but is too small to prove anything.

**Bottom line:** trust the watchlist most, and double-check the open list beyond Title X.

### 12. Where the AI was wrong (required by the competition)
**Means:** three real mistakes and how we caught them.
1. DeepSeek said DHHS would lead 73 university research grants. Jev disagreed, which exposed it, so we added a rule that moves research grants to their own list.
2. DeepSeek once used the single word "states" as proof. Our quote check rejected it.
3. Meta's AI blocked us because DHHS grants mention HIV and overdoses, so we switched to DeepSeek.

### 13. Three things we think NC DHHS should do (the last slide)
**Means:** our recommendation, as three actions:
1. **Check Grants.gov now** for Ryan White Part B and Preschool Development B-5, which may already be open.
2. **Apply for Title X** through the Division of Public Health (due 11 January 2027, up to $22M).
3. **Share the research list** (134 grants) with a university partner, since DHHS can't lead those itself.

One line at the bottom covers what we'd build with more time (a weekly run on live data that emails the coordinator new matches). The competition requires one known limitation and a "with more time" item: the limitation (our small hand-labeled check) is said on slide 11, and the "more time" item is here.
