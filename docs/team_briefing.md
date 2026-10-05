# Team briefing: what our grant finder actually does (about 10 minutes)

The rules say evaluators may ask **any** of us to explain the approach, so everyone should be able to give this talk.

---

## 1. The problem, in one breath (1 min)

Every week Grants.gov posts hundreds of federal grants. Somewhere in there is money NC DHHS could win, but nobody has time to read them all. Our job: take the **1,662** listings in the starter data and hand the DHHS grants coordinator a **short list of the ones worth their time**, each with a reason, an owner, a deadline and a risk.

**The analogy:** it works like hiring.
- **HR removes the impossible applications.** That's Python rules.
- **A recruiter skims the rest fast.** That's Jev.
- **A senior interviewer reads the finalists closely and writes notes.** That's DeepSeek.
- **A published scorecard picks the winners.** That's the formula.

Nobody's opinion alone decides; the scorecard does.

## 2. Our user and what "good" means (1 min)

The user is the **DHHS federal-grants coordinator**, the person who routes grants to divisions. Before touching the data, we wrote down five rules for a good grant:
1. **DHHS can actually apply**, as lead or partner. This is a gate.
2. It serves a **goal in the DHHS 2023–2025 strategic plan**.
3. **A DHHS division already does this kind of work.**
4. There's **enough time to apply**.
5. The **money is worth the effort**.

Everything below exists to measure those five things.

## 3. The four steps (5 min)

### Step 1: Python rules (no AI). 1,662 → 1,303
Plain code handles anything that's a **fact**:
- **Removes** only what's dead: 330 already closed, 12 archived, 17 paperwork notices (records that just transfer an existing award, not real opportunities).
- **Scores** deadline (0 if closing within days, 10 if 60+ days out) and award size ($100K → 0, $1M → 5, $10M+ → 10) on fixed scales.
- **Cleans up fake numbers**, like an award listed as $999,999,999.
- **Flags** forecasts (grants announced but not open yet) and research grants (titles with codes like "R01").

*Why no AI here?* Facts like "is the deadline past?" shouldn't depend on an AI that might get them wrong.

### Step 2: Jev, the fast screen. 1,303 → 283
Jev is a cheap, fast AI that answers **multiple-choice questions** and says how confident it is. For every grant it answers four:
1. Is this DHHS's kind of work? (none / weak / moderate / strong)
2. Which strategic-plan goal does it serve?
3. Can DHHS apply? (lead / partner / unusual / ineligible)
4. Which of the 13 DHHS divisions would own it?

It only throws a grant out when it's **85–95% sure**; anything uncertain moves on. Result: **283 kept, 1,020 set aside** (997 off-topic, 23 that DHHS can't apply for, such as tribes-only grants).

*Why a screen?* Reading everything carefully costs money and time, so we narrow first, erring on the side of keeping things.

### Step 3: DeepSeek, the careful reader. 283 analyzed
DeepSeek is a stronger AI. For each of the 283 it reads the full grant and writes:
- **fit** with DHHS's goals (0–10)
- whether **DHHS can realistically run it** (0–10)
- **DHHS's role** (lead or partner)
- the **owning division**
- the **main risk** and a **one-line reason**

The key trick: **it has to quote the grant word for word as proof**, and our code checks every quote against the real text. 282 of 283 checked out. If it can't prove a claim, the claim gets downgraded.

**DeepSeek doesn't remove or rank anything. It only explains.**

### Step 4: The formula decides
A fixed, published scorecard turns everything into a score out of 100:

| Criterion | Weight | Comes from |
|---|---|---|
| Strategic fit | 30% | DeepSeek |
| Can DHHS run it | 25% | DeepSeek |
| Award size | 15% | Python |
| Deadline | 15% | Python |
| Eligibility certainty | 15% | DeepSeek's quote, checked by Python |

Plus a few rules: proven ineligible means 0, an unproven quote costs 5 points, and no deadline costs 3. Then it sorts grants into **three lists**:
- **33 open now**: apply.
- **116 opening soon**: forecasts to prepare for.
- **134 research grants**: DHHS can't lead these, so pass them to a university partner.

**The AI never picks the winners. The formula does, and anyone can check the math.**

## 4. One grant, start to finish (1 min): Title X Family Planning

1. **Python:** it's open with 103 days left, so deadline 10/10. Up to $22M, so award 10/10.
2. **Jev:** "strong" fit, DHHS can lead, owner is the Division of Public Health. It goes on.
3. **DeepSeek:** fit 10/10, can-run-it 9/10, role = lead, **with the eligibility sentence quoted and verified**.
4. **Formula:** **98/100**, #1 on the "apply now" list.
5. **Check:** federal spending records show NC DHHS already won **$14.7M** under this program.

## 5. What we found (30 sec)

- **Apply now:** Title X (98/100). The rest of the open list is weaker.
- **Prepare now:** the real money is in forecasts. 4 of the top 5 are programs NC DHHS has already won, about **$275M** in four years, led by Ryan White HIV care ($187.6M). Two may already be open.

## 6. How we know it works (1 min)

1. **Federal spending records (no AI at all):** grants Jev threw out had a history of paying state agencies only **2%** of the time, against **25%** for the ones it kept. So the screen sorts in the right direction.
2. **Evidence:** 282/283 AI quotes are real.
3. **Two different AIs agree** on DHHS's role **87%** of the time.
4. **Keyword search, for comparison:** the simple approach ranks Ryan White **#670**, and its #1 is a grant only tribes can apply for.
5. **A small human check** (31 grants) points the same way, but it's too small to prove anything. Don't oversell it.

## 7. Where the AI was wrong (required, 30 sec)

1. **DeepSeek said DHHS would lead 73 university research grants.** Jev disagreed on all of them, which exposed the mistake. Fix: a rule moves research grants (codes like "R01") to their own list.
2. **DeepSeek once used the single word "states" as proof** of eligibility. Our quote check rejected it automatically.
3. **Meta's AI blocked us** because DHHS grants mention HIV and overdoses. We switched to DeepSeek by changing one setting. Lesson: don't rely on one AI vendor.

## 8. Honest limits (say these confidently; judges reward it)

- The data is a **snapshot from August 18**.
- "Fit" means fit with the **2023–2025** strategic plan.
- The **human check is small**.

## 9. Numbers worth memorizing

**1,662 → 1,303 → 283 → 15** · weights **30 / 25 / 15 / 15 / 15** · Title X **98** · Ryan White **$187.6M**, keyword rank **#670** · quotes **282/283** · track record **2% vs 25%** · total AI cost **$3.36** · reruns in **~11 seconds**.

---

## Practice questions (anyone may get one)

- **"Why use two AIs instead of one?"** The fast one screens all 1,303 cheaply; the careful one writes evidence only for the 283 that matter. Neither ranks.
- **"How do you stop the AI making things up?"** It must quote the grant word for word, and code checks every quote. Unproven claims get downgraded.
- **"Couldn't you just search for keywords?"** We built that. It ranks DHHS's $187M HIV program 670th and puts a tribes-only grant at #1.
- **"Why is the open list weak?"** Most programs DHHS wins closed between August and September, or haven't opened yet. That's why the forecast watchlist matters.
- **"How sure are you?"** Strongest evidence: federal spending records show the programs we prioritize are ones states actually win. Weakest: our human check is small.
- **"What would you do with more time?"** Run it weekly on live data and email the coordinator, use the award track record in the score, and get labels from real grants officers.
