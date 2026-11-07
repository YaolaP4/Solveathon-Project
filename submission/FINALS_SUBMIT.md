# Finals submission: what to upload (deadline Sunday 8 Nov, 9:00 AM)

Form: "Solve-a-thon Final Submission" (linked on the Final Quest page; needs a UNC sign-in).
The website asks for **slides, field notes and repository**, plus the **link to the product** with the slides.

| Item | What to submit | Where it is |
|---|---|---|
| Slides (6-minute pitch) | Download the deck as PowerPoint or PDF from the Slides artifact (Share › Export) | Slides artifact "Federal Funds Matchmaker: Finals Pitch" |
| Link to the product | https://app-ffm-web.salmonmushroom-cf3974d2.eastus2.azurecontainerapps.io | Live on Azure (team 14 subscription) |
| Solution Design and GenAI Field Notes | `submission/Solution_Design_and_GenAI_Field_Notes.pdf` (both documents in one file) | Built from `docs/solution_design.md` and `docs/finals_field_notes.md` |
| Repository | https://github.com/pavparola/Solveathon-Project (public; merge pull request #10 first so `main` has the finals code) | README is the state-developer guide |

## Fill in before submitting

- [ ] **Discovery Session notes**: Section 1 of `docs/solution_design.md` ("What we learned from the sponsors") has a
      `[TEAM: ...]` placeholder. Write 3–5 bullets, then rebuild the PDF: `python src/md_to_pdf.py docs/solution_design.md`
      and `python src/submission_finals.py`.
- [ ] **Slide 1**: team name and member names. **Slide 2**: one line on what the sponsors told you.
- [ ] **Slide 8**: precision@10 and labeler agreement, after two people label on the Evaluation page (choose an agency
      first; about 15 minutes each). Do not present the `[__]` placeholders.
- [ ] Fill "reviewed by" in the two diagram reports (`docs/diagrams/*/report.html`).
- [ ] Open the app on a phone; record a backup demo (script in the slide notes).

## After judging

Delete the Azure resources so credits stop: `bash deploy/99_teardown.sh` (about $2–3 a day while running).
