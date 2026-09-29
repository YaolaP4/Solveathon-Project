# Agency Profile: NC Department of Health and Human Services (NCDHHS)

Source: [NCDHHS Strategic Plan 2023–2025](https://www.osbm.nc.gov/strategic-plan-ncdhhs/open) (OSBM agency strategic plans). Structured version: [`priorities.json`](priorities.json).

## Why NCDHHS

- **Largest realistic opportunity pool.** 947 of the 1,662 grants in the dataset come from HHS. After removing grants that close before 2026-09-30, those that don't list state governments as eligible, and NIH research grants, a quick keyword count finds **roughly 110 DHHS-relevant grants**. The same count finds about 29 for DPI and 11 for DEQ, so a top-10 list for DHHS is a real selection rather than whatever happens to exist.
- **The plan asks for this.** The plan's Medicaid-expansion work is framed as a way to *"maximize federal resources"* (p. 3), and Goal 5, Objective 2.1, is about tracking "new and existing Federal funding." A tool that finds federal money fits a stated priority.
- **The hard part is visible.** DHHS is eligible for almost everything on paper: 609 of the 689 NIH grants list "state governments." The real question is whether DHHS is the *intended* applicant. That makes eligibility reasoning, rather than keyword matching, the core of the problem.

## User

**The NCDHHS federal-grants coordinator.** Each week they review new Grants.gov postings, decide which ones are worth pursuing, and route each one to the division that would own the application (for example Public Health; MH/DD/SUS; Child and Family Well-Being; Medicaid). They are not technical. They need a short list with a reason, an owner and a risk for each grant.

## Draft "good match" criteria (team to finalize before scoring)

1. **Right applicant role.** DHHS can lead, or is an expected partner. This is a gate: confirmed ineligible means excluded. "Technically eligible but designed for university researchers" ranks low.
2. **Strategic alignment.** The funded activity advances a named goal and objective of the 2023–2025 plan (G1–G5).
3. **A division can own it.** Some DHHS division already does this kind of work and has the authority to run it.
4. **Realistic deadline.** For open grants, enough time to apply (for example at least 30 days after the as-of date). Forecasts go to a separate watchlist to prepare early.
5. **Worth the effort.** The award size justifies the application cost; cost sharing is flagged.

## Known limitations

- The plan covers 2023–2025. As of September 2026 it may lag the Department's current priorities, especially after federal funding changes in 2025–2026.
- DHHS is very large, so "operational fit" depends on the division, which is why Layers 2 and 3 predict the owning division.
- The division list in `priorities.json` is our summary of the DHHS org chart and should be checked against the current one.
