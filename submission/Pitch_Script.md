# Pitch script: UNC Solvers, Federal Funds Matchmaker

**Sunday 8 Nov · we present FIRST, 10:10–10:18 AM, Manning 209 · 6 minutes + 2 minutes Q&A · judge check-in 9:30**

Speakers (swap names freely; keep the hand-overs): **Pavan** slides 1–3 · **Advik** slide 4 + live demo · **Mayank**
slides 7–9 · **Aarav** slides 10–13 and runs Q&A. Script runs about 5:45, leaving a 15-second buffer.

## Before 10:10 (do at check-in, 9:30)

- Laptop charged and plugged in; phone hotspot on standby in case the venue Wi-Fi fails.
- Window 1: the deck, full screen, on slide 1. Window 2: the app at
  `https://app-ffm-web.salmonmushroom-cf3974d2.eastus2.azurecontainerapps.io`, on the **NC DHHS** list, browser zoom **125%**.
- Check the banner says "Last refreshed: Sun 8 Nov" (the 6 AM run). Note what is ranked #1 (on Saturday it was the
  Rural Health Network Development Planning Program).
- Practice Alt+Tab between the two windows once.
- Recommended by the organizers: a 2-minute screen recording of the demo on the laptop as a backup.

## The script

| Time | Slide | Who | Say (and do) |
|---|---|---|---|
| 0:00–0:12 | 1 Cover | Pavan | "Good morning, we're UNC Solvers. This is the Federal Funds Matchmaker. Every morning it reads all of Grants.gov and tells each North Carolina agency which grants are worth its time, and why." **[→]** |
| 0:12–0:40 | 2 The user | Pavan | "Our user is the grants coordinator inside a state agency, and today every agency does this alone. There are 1,460 federal listings right now **[point: black bar]**. Search just Health and Human Services' topics and you still get 1,305 **[point: teal bar]**. Nobody can read that, so grants get missed, especially at small agencies. This red sliver is what we hand that coordinator: about 90 strong matches. And on Friday the sponsors told us one thing above all: it has to scale to every department. It does, and we'll show you how." **[→]** |
| 0:40–0:55 | 3 Frame | Pavan | "So the problem in one line: agencies scan federal notices alone and still miss good ones. We held ourselves to four rules: it runs daily on its own, every rank is explained, a human always decides, and it works for any agency." **[→] [hand over]** |
| 0:55–1:15 | 4 How it works | Advik | "Here's how it works. Every morning at six, one job on Azure pulls Grants.gov, cleans it, scores every listing against each agency's own plan, and has Azure OpenAI explain the top 45, and our code checks every quote. Coordinators open their list and decide. Two minutes a run, two to three dollars a day. Let me show you." **[→ to slide 5, then Alt+Tab to the browser]** |
| 1:15–3:05 | LIVE DEMO | Advik | See the demo steps below. Then **[Alt+Tab back, press → twice to skip slides 5–6, land on slide 7] [hand over]** |
| 3:05–3:35 | 7 Evidence | Mayank | "How do we know it works? Two measured checks. In the qualifier round our pipeline reviewed over a thousand of these same grants one by one. On the 1,037 still live, our daily score ranks the relevant ones above the rest with an AUC of 0.92 **[point: gauge]**: 0.5 is a coin flip, 1 is perfect. And 162 of 178 AI quotes matched the listing word for word; the rest were hidden from staff automatically. In the pilot, staff label picks blind, and the app already does the math." **[→]** |
| 3:35–4:00 | 8 Failure | Mayank | "Where it didn't work. Our first matcher used AI similarity alone, and it ranked a Navy research call near the top for a health department **[point: list]**. Long, generic text looks similar to everything. We caught it by reading the list, not trusting the numbers. The fix: score how much closer a grant is to the agency's plan than to ten unrelated fields, plus plain word matching. On-topic results went from 62 to 76 percent **[point: red bar]**." **[→]** |
| 4:00–4:25 | 9 AI right and wrong | Mayank | "The AI itself was both right and wrong. Right: the Gulf Coast grant you saw in the demo. Our score can't see geography, but the AI quoted the limit. Wrong: when we let that check remove grants, it misread 'territories may also apply' and hid an HIV program for the South, which includes North Carolina. So now it flags and never hides. A missed grant costs more than a minute spent passing a bad one." **[→] [hand over]** |
| 4:25–4:50 | 10 Security | Aarav | "This is a government system, so we built it like one. Only public data ever goes to the AI, and the AI can't change a score or act on its own. The site is HTTPS only, every form is protected against forgery, injected scripts are blocked, and every decision is logged by name. Our honest gap is sign-in: the pilot adds Entra ID and moves the keys into Key Vault." **[→]** |
| 4:50–5:10 | 11 Scale | Aarav | "You asked for scale **[point: diagram]**. Grants.gov is pulled once for everyone. A new department is one profile file built from its strategic plan, under a day of work, and the next morning it has its own list and a row in OSBM's view. We added Environmental Quality exactly that way. Each one costs under ten cents a day." **[→]** |
| 5:10–5:35 | 12 Pilot | Aarav | "So here's our ask: a 60-day pilot run by OSBM, with Health and Human Services, Environmental Quality and one small agency with little grant staff. They keep their manual checks so we can measure what we miss. At day 60, decide on evidence: hours saved, and grants found that would have been missed. Then every agency." **[pause]** "The system ranks and explains. People decide." **[→]** |
| 5:35–5:45 | 13 Questions | Aarav | "Thank you. The app is live at that link, so try it on your phone. We're happy to take questions." **[leave this slide up]** |

### Live demo (Advik, 1:15–3:05)

1. **[NC DHHS list; point at the banner]** "This is the Health and Human Services list. Last refreshed this morning, 1,460 listings checked. Nobody pressed a button."
2. **[Point at the red alerts]** "Red alerts: strong matches that close within 10 days."
3. **[Point at the ranked rows]** "Then the ranked matches, each with a score, a confidence level, and Pursue, Maybe or Pass right on the row. Low matches are hidden, one click away."
4. **[Click #1, the Rural Health Network Development Planning Program; if the order changed, open whatever is #1]** "Our top match: a rural health planning grant. It's tied to objective 3.4 of DHHS's new plan, page 6. Here's why it matches in plain English, and this quote from the listing. The grey line means our code checked it word for word. State agencies can lead, and the owning division is the Office of Rural Health."
5. **[Scroll to the score breakdown]** "The score isn't magic: 83 out of 100, and every point is accounted for, including that DHHS already won 1.4 million dollars under this program."
6. **[Scroll to Decision: initials, Pursue, Save]** "The coordinator decides. Pursue, saved with a name and a full history."
7. **[Agency switcher → NC DEQ; click the RESTORE Act row]** "Same tool, second agency: Environmental Quality. Its top hit is a RESTORE Act grant, but the AI quoted that it's for Gulf Coast states only and lowered its confidence. It flags; it never hides."
8. **[Click Statewide in the top menu]** "And this is OSBM's view: every agency's strong matches, deadlines and decisions on one page."

**If the Wi-Fi fails:** stay on the slides. Say steps 1–3 on slide 5 and steps 4–6 on slide 6, then go on to slide 7.

## Q&A (2 minutes): short, honest answers

Leave slide 13 up. For "how does the score work", press → twice (slide 15). For "what does OSBM see", press → three times (slide 16).

| If they ask | Answer |
|---|---|
| How do you know you aren't missing grants? | Low matches are never deleted, only one click away. The Evaluation page counts relevant grants that keyword search misses. In the pilot, coordinators keep their manual checks so we can measure recall honestly. |
| What about statutory authority? | Not modelled yet. Profiles hold the plan's goals, objectives and priorities; adding each agency's statutes as a profile field is the next step. |
| Why should leadership trust the AI? | It never sets the score; that's a published formula. It can only flag, with a quote our code checks word for word, and people make every decision. |
| What does it cost? | About $2–3 a day for both agencies, mostly the always-on website. Each extra agency adds under 10 cents a day of AI. |
| Who can access it? Security? | HTTPS only, forgery-protected forms, strict content policy, keys in Azure secrets. The gap is sign-in: anyone with the link can record a decision today, but every decision is logged by name. The pilot adds Entra ID and Key Vault. |
| What happens when an agency's plan changes? | Rebuild its profile. We did it during this event: DHHS published a new 2026–2030 plan, and we rebuilt the profile from it; matching quality held (AUC 0.92). |
| Why Grants.gov and not SAM.gov? | Grants.gov is where federal grant opportunities are posted, with a free API. SAM.gov contracts are a natural next source. |
| How did you use AI to build it? | Two ways. In the product, Azure OpenAI for meaning-based matching and summaries. To build it, an AI coding assistant working to our direction; we set the scope, reviewed and tested its output. It's all documented in our GenAI Field Notes, including where the AI was wrong. |
| What if Grants.gov is down? | The job retries, and if fewer than 50 listings arrive it refuses to publish, so yesterday's list stays up. |
| How long to add an agency? | Under a day: one profile file from its strategic plan, then redeploy. DEQ was added that way. |
| Does it learn from staff? | Yes. A new grant very similar to one staff passed drops a confidence level; one similar to a pursued grant rises one, with the reason shown. Tuning the weights from decisions is on the roadmap. |
