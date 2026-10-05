# Qualifier submission checklist (due Mon 5 Oct 2026, 11:59 p.m.)

The competition asks for 3 things. Here's where each one is.

| # | Required | Our file(s) |
|---|---|---|
| 1 | **Top results list** with a one-line rationale per opportunity, tied to the match criteria | [`top_results.md`](top_results.md) (readable) and [`top_results.csv`](top_results.csv) (opens in Excel or Sheets): top 10 open grants and top 5 forecast grants, each with a rationale, a 5-criteria check, the main risk and NC DHHS award history |
| 2 | **Our work** (notebook/script/spreadsheet with notes) + **AI use**: tools, key prompts, at least one place the AI was wrong and how we caught it | The repository (`README.md` explains every layer; `python src/pipeline.py` reproduces everything in about 11 s, no API key) and [`ai_usage.md`](ai_usage.md). Supporting: `docs/failure_modes.md`, `data/results/validation_report.md`, `data/results/award_history_report.md` |
| 3 | **Presentation to agency leadership**: a recording of 5 minutes or less is preferred, but a PowerPoint is accepted | Slide deck (Claude artifact "NC DHHS Grant Finder"; download as .pptx or PDF) plus [`recording_script.md`](recording_script.md) (about 4½ min, with how-to-record steps) |

## Before submitting

- [ ] Record the video (or export the deck to .pptx/PDF if not recording).
- [ ] Make the code visible to judges: either make the GitHub repo public, or upload a .zip of the repo (**never include `.env`**, which holds the API key; `git archive` leaves it out automatically: `git archive -o solveathon.zip HEAD`).
- [ ] One submission per team, through the form on the Solve-a-thon page (UNC Microsoft sign-in).
