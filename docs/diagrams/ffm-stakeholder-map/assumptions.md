# Assumptions & Validation Questions: Federal Funds Matchmaker (Stakeholder Map)

Team 14, UNC Solve-a-thon 2026 · Sponsor: NC OSBM · Agencies: NC DHHS, NC DEQ · Version 1.2 · 2026-11-07 · Validate each item with real stakeholders, then regenerate the map.

Changes in 1.2 (from 1.0; there was no 1.1 of this pack): NC OSBM (S9) is now the sponsor, problem owner and owner of the central tool (power 5, interest 4, Manage Closely; was 3/3). Added S19 NC DEQ grants coordinator and S20 NC DEQ leadership as users alongside NC DHHS's, and S21 smaller agencies with limited grant capacity (future users, high interest). The NC DHHS profile now comes from the 2026-2030 plan. The RACI is re-cut for an OSBM-run pilot: OSBM is accountable for profiles on the one template, match-quality evidence and the pilot go / no-go; triage and the decision to apply have one row per agency, so every row still has exactly one A. Assumptions A1, A2, A3, A5, A6, A7 and A10 changed; A13-A16 are new; the 2023-2025 plan question is replaced. Scores stay ASSUMED.

Facts come from the team's facts sheet, the challenge framing recorded in docs/finals_checklist.md and docs/solution_design.md, and the repository (README.md, agency/profiles/*.json, src/, deploy/). Everything below is an inference and is marked ASSUMED in report.html.

## Assumptions

| # | Assumption | Validate with |
|---|---|---|
| A1 | NC OSBM (S9) is the sponsor and problem owner and wants one central tool for all agencies (challenge framing in docs/finals_checklist.md and docs/solution_design.md). That OSBM would own, host and run the tool after the event, and which OSBM office would do so, is assumed. | NC OSBM |
| A2 | All power, interest and attitude scores are team estimates, including the coordinators' attitudes (S1 Supporter, S19 Neutral) and OSBM's (S9 Supporter). | Both agencies' grants coordinators, one DHHS division program lead, and NC OSBM |
| A3 | NCDIT and the DHHS privacy and security office must approve a pilot; NCDIT is accountable for the security review in the RACI. NC DEQ's and the smaller agency's own privacy or security reviewers may also need to sign off; they are not mapped separately. | NCDIT; each pilot agency |
| A4 | NCDIT is sceptical of the prototype because of the known gaps (no sign-in, keys instead of managed identity), not from contact with NCDIT. | NCDIT security reviewer |
| A5 | Procurement and legal (S8) are involved only for a production contract, which OSBM or the hosting agency would hold. | NC OSBM; state procurement |
| A6 | At NC DHHS, division directors are accountable for the decision to apply and executive leadership is consulted for large or cross-division awards; at NC DEQ, leadership (S20) both prepares and signs off the decision. | Both grants coordinators |
| A7 | OSBM, which publishes the agency strategic plans, is accountable for building each profile on the one template and keeping it in step with the published plan; each agency's coordinator checks its own profile. (In 1.0 the DHHS coordinator was accountable for the single profile.) | NC OSBM; both grants coordinators |
| A8 | Division program staff are sceptical of AI recommendations and grant-writing consultants may see the tool as a threat. | Interviews with 2-3 program staff; optional consultant interview |
| A9 | The Solve-a-thon hosts provide the Azure subscription (unc-sdis-solveathon-team14) and expect resources to be removed after judging. | Solve-a-thon organizers |
| A10 | HRSA, CDC, SAMHSA and ACF (for DHHS) and EPA and NOAA (for DEQ) are examples of federal awarding agencies; the list is illustrative. | Not needed for decisions |
| A11 | Engagement owners inside Team 14 (lead, tech lead) and frequencies are proposals for a pilot period. | Team 14 |
| A12 | In these stakeholder diagrams a dashed outline means external to NC state government; it does not mean “planned” as in the architecture diagrams. | Not needed (reading note) |
| A13 | Smaller agencies with limited grant capacity (S21) have high interest and little formal influence (2/4) and would support the tool; no smaller agency has been named or interviewed, and the one for the pilot is not chosen. | NC OSBM; 2-3 smaller agencies |
| A14 | The NC DEQ grants coordinator (S19) is Neutral because the matcher was tuned on NC DHHS data and NC DEQ uses the same settings untuned (README.md); the repository records no contact with NC DEQ. | NC DEQ grants coordinator |
| A15 | OSBM is accountable for measuring match quality for each agency and for the pilot go / no-go and budget; each agency's leadership is consulted on whether it joins. | NC OSBM |
| A16 | Agency leaders may be wary that the Statewide page shows the central budget office each agency's Pursue / Maybe / Pass counts. | DHHS executive leadership (S3); NC DEQ leadership (S20) |

## Assumed scores (power / interest, attitude)

| ID | Stakeholder | P | I | Attitude | Basis |
|---|---|---|---|---|---|
| S1 | DHHS federal-grants coordinator | 3 | 5 | Supporter | Facts sheet (users); agency/profiles/ncdhhs.json "user"; attitude and scores ASSUMED |
| S2 | DHHS division program leads | 3 | 4 | Neutral | Facts sheet (secondary users); 13 divisions in agency/profiles/ncdhhs.json; scores ASSUMED |
| S3 | DHHS executive leadership | 5 | 3 | Neutral | Facts sheet (decision makers, goal funding view); 2026-2030 plan in agency/profiles/ncdhhs.json; scores ASSUMED |
| S4 | DHHS division directors | 4 | 3 | Neutral | Facts sheet (decision makers); scores ASSUMED |
| S5 | DHHS division program staff | 2 | 3 | Sceptic | Facts sheet (possible resistors); scores ASSUMED |
| S6 | NCDIT state IT security & privacy | 4 | 2 | Sceptic | Facts sheet (approvers, security gaps); attitude and scores ASSUMED |
| S7 | DHHS privacy & security office | 4 | 2 | Neutral | Facts sheet (approvers, data sensitivity); attitude and scores ASSUMED |
| S8 | Procurement & legal | 4 | 1 | Neutral | ASSUMED (facts sheet marks this as assumed) |
| S9 | NC OSBM: sponsor, central tool owner | 5 | 4 | Supporter | Sponsor and problem owner: challenge framing (docs/finals_checklist.md, docs/solution_design.md); owner of the central tool and scores ASSUMED |
| S10 | Team 14: builders, operators, labelers | 2 | 5 | Champion | Facts sheet; deploy/02_deploy.sh; deploy/99_teardown.sh |
| S11 | Solve-a-thon hosts: Azure subscription | 3 | 2 | Supporter | Facts sheet (subscription); deploy/env.sh; host role ASSUMED |
| S12 | Microsoft Azure: cloud & AI vendor | 2 | 1 | Neutral | Facts sheet (cloud services built); deploy/01_resources.sh |
| S13 | Grants.gov: listings API | 3 | 1 | Neutral | Facts sheet (external APIs); src/grantsgov.py; one pull per run in src/job.py |
| S14 | USAspending.gov: award history API | 1 | 1 | Neutral | Facts sheet (external APIs); usaspending_recipient_pattern in agency/profiles/*.json, used in src/matcher.py; data/cache/usaspending/ |
| S15 | Federal awarding agencies | 2 | 1 | Neutral | ASSUMED (not in facts sheet) |
| S16 | Local govts, utilities, community orgs | 2 | 3 | Supporter | Facts sheet (beneficiaries); utilities ASSUMED from the DEQ profile's water infrastructure program area; attitude and scores ASSUMED |
| S17 | NC residents served by DHHS and DEQ | 1 | 2 | Neutral | Facts sheet (beneficiaries); attitude and scores ASSUMED |
| S18 | Grant-writing consultants | 1 | 2 | Sceptic | ASSUMED (facts sheet marks this as assumed) |
| S19 | NC DEQ grants coordinator | 3 | 5 | Neutral | agency/profiles/ncdeq.json "user"; README.md known limitations; attitude and scores ASSUMED |
| S20 | NC DEQ leadership | 4 | 3 | Neutral | agency/profiles/ncdeq.json (2025-2029 plan, 11 divisions); scores ASSUMED |
| S21 | Smaller agencies: limited grant capacity | 2 | 4 | Supporter | Challenge framing (docs/finals_checklist.md); pilot plan in docs/solution_design.md section 7; attitude and scores ASSUMED |

## Validation questions

1. Which OSBM team would own and operate the central tool after the event, and would OSBM or NCDIT host it? (Ask: NC OSBM; NCDIT.)
2. What is the review process for a pilot that uses Azure OpenAI, and who signs off for each participating agency? (Ask: NCDIT; DHHS privacy and security office; NC DEQ.)
3. Which smaller agency should join the pilot, and who there would review the shortlist each week? (Ask: NC OSBM.)
4. Who decides whether to apply at each agency: division directors, executive leadership, or both depending on award size? (Ask: Both grants coordinators.)
5. How many hours a week does scanning Grants.gov take today, and how often is a relevant notice found too late? (Ask: Both grants coordinators; the pilot's smaller agency.)
6. Is the DEQ division list in agency/profiles/ncdeq.json right, and are DEQ matches good enough without DEQ-specific tuning? (Ask: NC DEQ grants coordinator; NC DEQ leadership.)
7. What should the Statewide page show OSBM: decision counts only, or more? (Ask: NC OSBM; DHHS executive leadership; NC DEQ leadership.)
8. Which divisions should receive routed opportunities first in a pilot? (Ask: Both grants coordinators; division directors.)
