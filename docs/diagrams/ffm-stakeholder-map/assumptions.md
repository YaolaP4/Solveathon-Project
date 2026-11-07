# Assumptions & Validation Questions: Federal Funds Matchmaker for NC DHHS (Stakeholder Map)

Team 14, UNC Solve-a-thon 2026 · Version 1.0 · 2026-11-07 · Validate each item with real stakeholders, then regenerate the map.

Facts come from the team's facts sheet and the repository (README.md, agency/priorities.json, src/, deploy/). Everything below is an inference and is marked ASSUMED in report.html.

## Assumptions

| # | Assumption | Validate with |
|---|---|---|
| A1 | NC OSBM is the Solve-a-thon challenge sponsor (S9). | Solve-a-thon organizers |
| A2 | All power, interest and attitude scores are team estimates, including the coordinator's attitude (S1 Supporter). | The federal-grants coordinator and one division program lead |
| A3 | NCDIT and the DHHS privacy and security office must approve a pilot; NCDIT is accountable for the security review in the RACI. | DHHS privacy and security office |
| A4 | NCDIT is sceptical of the prototype because of the known gaps (no sign-in, keys instead of managed identity), not from contact with NCDIT. | NCDIT security reviewer |
| A5 | Procurement and legal (S8) are involved only for a production contract. | DHHS procurement |
| A6 | Division directors are accountable for the decision to apply; executive leadership is consulted for large or cross-division awards. | Federal-grants coordinator |
| A7 | The coordinator is the DHHS-side owner of the agency profile and of match-quality checks. | DHHS executive leadership |
| A8 | Division program staff are sceptical of AI recommendations and grant-writing consultants may see the tool as a threat. | Interviews with 2-3 program staff; optional consultant interview |
| A9 | The Solve-a-thon hosts provide the Azure subscription (unc-sdis-solveathon-team14) and expect resources to be removed after judging. | Solve-a-thon organizers |
| A10 | HRSA, CDC, SAMHSA and ACF are examples of federal awarding agencies; the list is illustrative. | Not needed for decisions |
| A11 | Engagement owners inside Team 14 (lead, tech lead) and frequencies are proposals for a pilot period. | Team 14 |
| A12 | In these stakeholder diagrams a dashed outline means external to NC state government; it does not mean “planned” as in the architecture diagrams. | Not needed (reading note) |

## Assumed scores (power / interest, attitude)

| ID | Stakeholder | P | I | Attitude | Basis |
|---|---|---|---|---|---|
| S1 | DHHS federal-grants coordinator | 3 | 5 | Supporter | Facts sheet (users); agency/priorities.json "user"; attitude and scores ASSUMED |
| S2 | DHHS division program leads | 3 | 4 | Neutral | Facts sheet (secondary users); 13 divisions in agency/priorities.json; scores ASSUMED |
| S3 | DHHS executive leadership | 5 | 3 | Neutral | Facts sheet (decision makers, goal funding view); scores ASSUMED |
| S4 | DHHS division directors | 4 | 3 | Neutral | Facts sheet (decision makers); scores ASSUMED |
| S5 | DHHS division program staff | 2 | 3 | Sceptic | Facts sheet (possible resistors); scores ASSUMED |
| S6 | NCDIT state IT security & privacy | 4 | 2 | Sceptic | Facts sheet (approvers, security gaps); attitude and scores ASSUMED |
| S7 | DHHS privacy & security office | 4 | 2 | Neutral | Facts sheet (approvers, data sensitivity); attitude and scores ASSUMED |
| S8 | Procurement & legal | 4 | 1 | Neutral | ASSUMED (facts sheet marks this as assumed) |
| S9 | NC OSBM: sponsor, plan publisher | 3 | 3 | Supporter | Sponsor role ASSUMED (facts sheet); plan source in agency/priorities.json |
| S10 | Team 14: builders, operators, labelers | 2 | 5 | Champion | Facts sheet; deploy/02_deploy.sh; deploy/99_teardown.sh |
| S11 | Solve-a-thon hosts: Azure subscription | 3 | 2 | Supporter | Facts sheet (subscription); deploy/env.sh; host role ASSUMED |
| S12 | Microsoft Azure: cloud & AI vendor | 2 | 1 | Neutral | Facts sheet (cloud services built); deploy/01_resources.sh |
| S13 | Grants.gov: listings API | 3 | 1 | Neutral | Facts sheet (external APIs); src/grantsgov.py |
| S14 | USAspending.gov: award history API | 1 | 1 | Neutral | Facts sheet (external APIs); data/cache/usaspending/ |
| S15 | Federal awarding agencies | 2 | 1 | Neutral | ASSUMED (not in facts sheet) |
| S16 | Local health depts, counties, orgs | 2 | 3 | Supporter | Facts sheet (beneficiaries); attitude and scores ASSUMED |
| S17 | NC residents served by DHHS | 1 | 2 | Neutral | Facts sheet (beneficiaries); attitude and scores ASSUMED |
| S18 | Grant-writing consultants | 1 | 2 | Sceptic | ASSUMED (facts sheet marks this as assumed) |

## Validation questions

1. Who owns the matchmaker after the event, and who would host and operate it (DHHS, NCDIT or another team)? (Ask: DHHS executive leadership; NCDIT.)
2. What is the review process for a pilot that uses Azure OpenAI, and who signs off? (Ask: NCDIT; DHHS privacy and security office.)
3. Who decides whether to apply: division directors, executive leadership, or both depending on award size? (Ask: Federal-grants coordinator.)
4. How many hours a week does scanning Grants.gov take today, and how often is a relevant notice found too late? (Ask: Federal-grants coordinator.)
5. Is there a newer NCDHHS strategic plan or priority list to replace the 2023-2025 plan? (Ask: NC OSBM; DHHS executive leadership.)
6. Which divisions should receive routed opportunities first in a pilot? (Ask: Federal-grants coordinator; division directors.)
