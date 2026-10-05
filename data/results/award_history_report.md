# Historical-award check (USAspending.gov)

Objective, non-AI check: who actually received grant awards under each grant's assistance listings in **FY2022-FY2025** (USAspending.gov, award types: block, formula and project grants, cooperative agreements). It answers *"is this a program state agencies like DHHS actually win?"*. It does **not** measure strategic fit, and an assistance listing covers every funding notice under it, not only this one.

**How recipients are classified:** by name rules in `src/award_history.py` (state agency / university / tribal / local government / nonprofit-hospital-company), because USAspending's own recipient-type tags are incomplete (for listing 93.917, NC DHHS received $187.6M by name but only $91.2M is tagged as state government). Only the top 200 recipients per listing are fetched; `coverage` is the share of dollars those cover. 'State agency history' = NC DHHS received at least $100K, or state agencies received at least 25% of the dollars.

Grants checked: **1303** (every grant Jev triaged). Distinct assistance listings queried: **257**.

### Top 10 open grants

| # | Grant | Verdict | NC DHHS | State-agency share | University share | Coverage |
|---|---|---|---|---|---|---|
| 1 | Title X Family Planning Services Grants | NC DHHS has received awards | $14.7M | 42% | 1% | 100% |
| 2 | Public Health Crisis Response Cooperative Agreement | no awards found FY2022-FY2025 | — | 0% | 0% | 0% |
| 3 | Home Study and Post-Release Services for Unaccompanied Alien Children​ | mostly nonprofits, hospitals or companies | — | 0% | 0% | 100% |
| 4 | Emerging Infections Network - Research for Preventing, Detecting, and  | mostly universities | $35K | 23% | 50% | 100% |
| 5 | NARMS Cooperative Agreement Program to Strengthen Antibiotic Resistanc | mixed recipients (some state agencies) | — | 21% | 32% | 96% |
| 6 | Laboratory Flexible Funding Model (LFFM) | mixed recipients (some state agencies) | — | 21% | 32% | 96% |
| 7 | US Travelers Health Research, Surveillance, Communication, and Outreac | mostly universities | $35K | 23% | 50% | 100% |
| 8 | Institute of Education Sciences (IES): National Center for Special Edu | mostly universities | — | 0% | 90% | 100% |
| 9 | BJA FY 2026 The Kevin and Avonte Program: Reducing Injury and Death of | mixed recipients (some state agencies) | — | 6% | 3% | 100% |
| 10 | Announcement of Stand Down Grants | mostly nonprofits, hospitals or companies | — | 1% | 0% | 100% |

**1 of 10** have awards to NC DHHS (at least $100K in FY2022-FY2025); **1 of 10** have NC DHHS or substantial state-agency awards; 1 have no awards in FY2022-FY2025; 0 unknown/unclear.

### Top 5 watchlist grants

| # | Grant | Verdict | NC DHHS | State-agency share | University share | Coverage |
|---|---|---|---|---|---|---|
| 1 | HIV Care Grant Program - Part B States/Territories Formula and AIDS Dr | NC DHHS has received awards | $187.6M | 76% | 0% | 100% |
| 2 | Maternal, Infant, and Early Childhood Home Visiting Program (MIECHV) | NC DHHS has received awards | $21.1M | 73% | 0% | 100% |
| 3 | Strengthening Services to Prevent the Infectious Disease Consequences  | mostly nonprofits, hospitals or companies | — | 2% | 2% | 100% |
| 4 | Preschool Development Grant Birth Through Five (PDG B-5) SMART Grant | NC DHHS has received awards | $36.3M | 82% | 5% | 100% |
| 5 | National HIV Behavioral Surveillance | NC DHHS has received awards | $30.2M | 65% | 1% | 100% |

**4 of 5** have awards to NC DHHS (at least $100K in FY2022-FY2025); **4 of 5** have NC DHHS or substantial state-agency awards; 0 have no awards in FY2022-FY2025; 0 unknown/unclear.

## Compared with Layer 2 (Jev) routing

- **Deprioritized by Jev:** 1020. Of these, **24** have a history of awards to NC DHHS or substantial state-agency awards (possible false negatives). 6 of them under a listing where NC DHHS itself received awards.
- **Sent to deep review:** 283. Of these, **109** went mostly to universities with no state-agency recipients among the top 200 (probably research-type programs).
- Grants Jev deprioritized vs sent on, share with state-agency history: 2% vs 25%.

### Deprioritized grants with state-agency award history (inspect each)

| Grant | Jev relevance / role | Verdict | NC DHHS | State share |
|---|---|---|---|---|
| HIV Care Grant Program - Part B States/Territories Formula and AIDS Drug Assistance Progra | strong / ineligible | NC DHHS has received awards | $187.6M | 76% |
| NIH, CDC and FDA Small Business Innovation Research Grant (Parent SBIR [R43/R44] Clinical  | weak / ineligible | NC DHHS has received awards (spans 41 listings) | $41.0M | 1% |
| Strengthening Public Health Systems and Services in Indian Country | weak / ineligible | NC DHHS has received awards | $1.3M | 19% |
| NIOSH Robotics and Intelligent Mining Technology and Workplace Safety Research (U60) | weak / atypical | NC DHHS has received awards | $579K | 3% |
| Continuation and Expansion of the National Mesothelioma Virtual Bank for Translational Res | weak / atypical | NC DHHS has received awards | $579K | 3% |
| World Trade Center Health Program Mentored Research Scientist Career Development Award (K0 | weak / atypical | NC DHHS has received awards | $579K | 3% |
| Specialty Crop Multi-State Grant Program 2026 | none / atypical | other state agencies win this | — | 92% |
| Fiscal Year (FY) 2026 Funding Opportunity for Indian Tribes and Intertribal Consortia for  | weak / ineligible | other state agencies win this | — | 87% |
| RESTORE Act Centers of Excellence Research Grants Program | none / atypical | other state agencies win this | — | 80% |
| RESTORE Act Direct Component - Non-Construction Activities | none / atypical | other state agencies win this | — | 80% |
| RESTORE Act Direct Component – Construction and Real Property Acquisition Activities | none / atypical | other state agencies win this | — | 80% |
| Outdoor Recreation Legacy Partnership Program (ORLP) Recurring Notice 5 Year | none / atypical | other state agencies win this | — | 78% |
| Readiness and Recreation Initiative (RARI) – Recurring 5 Year Notice | none / partner | other state agencies win this | — | 78% |
| F25AS00379 Highlands Conservation Act - Base Funding Round | none / ineligible | other state agencies win this | — | 71% |
| F25AS00332 Highlands Conservation Act – Competitive Funding Round | none / ineligible | other state agencies win this | — | 71% |
| FY2026 ABPP - Battlefield Land Acquisition Grant | none / atypical | other state agencies win this | — | 61% |
| Defense Security Cooperation University - Research Grants | none / atypical | other state agencies win this | — | 48% |
| F26AS00085 Aquatic Invasive Species Interjurisdictional Grants to the Great Lakes States a | none / ineligible | other state agencies win this | — | 45% |
| F26AS00083 Aquatic Invasive Species Grants to Great Lakes States - Fiscal Year 2026 Great  | none / ineligible | other state agencies win this | — | 45% |
| F26AS00084 Aquatic Invasive Species Grants to Great Lakes Tribes - Fiscal Year 2026 Great  | none / ineligible | other state agencies win this | — | 45% |
| 2026 National Urban and Community Forestry Challenge Cost Share Grant Program | weak / atypical | other state agencies win this | — | 42% |
| Fiscal Year (FY) 2022-2026 Advanced Digital Construction Management Systems (ADCMS) | none / ineligible | other state agencies win this | — | 39% |
| F26AS00104 State ANS Management Plan 2026 | none / ineligible | other state agencies win this | — | 34% |
| NOI: PROSPECT Program: Providing Opportunities for Specialized Education in Critical Techn | none / atypical | other state agencies win this | — | 26% |

_Caveat: an assistance listing is shared by many funding notices. A listing states win (e.g. a broad CDC or HRSA listing) can still carry a specific notice meant for others, such as a tribal-only or university-only competition. Treat these as leads to check, not proven misses. Our inspection of each is in `docs/failure_modes.md` (F9)._

## Verdicts across all checked grants

| verdict                                                |   grants |
|:-------------------------------------------------------|---------:|
| mostly universities                                    |      926 |
| mostly nonprofits, hospitals or companies              |      106 |
| mixed recipients (some state agencies)                 |       73 |
| NC DHHS has received awards                            |       71 |
| mixed recipients (no state agencies)                   |       39 |
| no awards found FY2022-FY2025                          |       31 |
| other state agencies win this                          |       24 |
| mostly tribal / Native organizations                   |       18 |
| unclear (top recipients cover too little of the money) |        8 |
| unknown (API error or non-standard listing)            |        6 |
| mostly local governments                               |        1 |

