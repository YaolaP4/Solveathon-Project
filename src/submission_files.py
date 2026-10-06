"""Build the 'work product and process' uploads (the form accepts Word/Excel/PPT/PDF, not zip):

  submission/process_report.pdf    how we got from the raw data to the results, with validation and failures
  submission/source_code.pdf       every script, prompt and config, printed
  submission/results_workbook.xlsx every grant's numbers at every step, one sheet per step

Usage:  python src/submission_files.py
"""

import html
from pathlib import Path

import pandas as pd
from openpyxl.styles import Font

import config
from md_to_pdf import CSS, convert
from submission_pdf import to_pdf

ROOT, SUB, RES = config.ROOT, config.ROOT / "submission", config.RESULTS
BREAK = "<div style='page-break-before: always'></div>"

INTRO = """# NC DHHS Grant Finder: work product and process

**UNC Solve-a-thon 2026 qualifier · Agency: NC Department of Health and Human Services.**

This report shows how we got from the 1,662 Grants.gov listings to our ranked results. Along with it we submitted:
- **Source code (PDF):** every script, prompt and config file.
- **Results workbook (Excel):** every grant's numbers at every step.
- **AI-use statement (PDF):** tools, key prompts, and where the AI was wrong.

## Our pipeline in one paragraph
**Layer 0–1, plain Python rules (no AI):** clean the data, remove 359 dead listings (closed, archived, paperwork notices), and score deadline and award size, leaving 1,303. **Layer 2, Jev:** a fast multiple-choice AI screens every grant with 4 questions and keeps 283, setting a grant aside only when it's 85–95% sure. **Layer 3, DeepSeek:** a large language model reviews the 283 and must back every claim with an exact quote, which our code verifies (282/283). **Layer 4, a published formula** (strategic fit 30%, can DHHS run it 25%, award 15%, deadline 15%, eligibility 15%) ranks them into 33 open grants, 116 forecasts and 134 research grants. **Layer 5, checks:** federal award history (USAspending.gov), hand labels, a keyword-search baseline, and an AI error log.

## Contents
1. Agency profile, user and match criteria
2. Slide-by-slide explanation of the method and results
3. Layer 1 audit counts
4. Historical-award check (USAspending.gov)
5. Validation against hand labels and the keyword baseline
6. Failure log: what went wrong and what we changed

Reproduce everything: `pip install -r requirements.txt`, then `python src/pipeline.py`. It reruns from saved model answers in about 11 seconds with no API key; there are 71 automated tests (`python -m pytest tests -q`).
"""

SECTIONS = [ROOT / "agency/agency_profile.md", SUB / "slide_guide.md", ROOT / "docs/layer1_report.md",
            RES / "award_history_report.md", RES / "validation_report.md", ROOT / "docs/failure_modes.md"]

CODE_FILES = ["src/pipeline.py", "src/config.py", "src/clean_data.py", "src/deterministic.py",
              "src/semantic_triage.py", "src/deep_analysis.py", "src/scoring.py", "src/award_history.py",
              "src/validation.py", "src/keyword_baseline.py", "src/report.py", "src/submission_table.py",
              "src/clients.py", "src/llm_cache.py", "src/text_utils.py",
              "prompts/jev_triage.json", "prompts/deep_analysis.txt", "agency/priorities.json"]


def write_pdf(name: str, body: str, extra_css: str = "") -> Path:
    page = SUB / f"{name}.html"
    page.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}{extra_css}</style></head>"
                    f"<body>{body}</body></html>", encoding="utf-8")
    pdf = to_pdf(page.resolve())
    page.unlink()
    return pdf


def process_report() -> Path:
    parts = [convert(INTRO)]
    for i, p in enumerate(SECTIONS, 1):
        md = p.read_text(encoding="utf-8")
        parts.append(BREAK + f"<p style='color:#6B7684;font-size:9pt'>Section {i} · {p.relative_to(ROOT)}</p>" + convert(md))
    return write_pdf("process_report", "\n".join(parts), "h3 { font-size: 11pt; margin: 10px 0 4px; } pre { white-space: pre-wrap; }")


def source_code() -> Path:
    toc = "".join(f"<li><code>{f}</code></li>" for f in CODE_FILES)
    parts = ["<h1>NC DHHS Grant Finder: source code</h1>",
             "<p>Every script, prompt and configuration file of the pipeline, in run order. "
             "Tests (71) are in <code>tests/</code> of the repository.</p>", f"<ol>{toc}</ol>"]
    for f in CODE_FILES:
        text = (ROOT / f).read_text(encoding="utf-8")
        parts.append(f"{BREAK}<h2>{html.escape(f)}</h2><pre class=code>{html.escape(text)}</pre>")
    css = "pre.code { font-family: Consolas, 'Courier New', monospace; font-size: 7.5pt; line-height: 1.3; white-space: pre-wrap; background: #FAF8F3; padding: 8px; border: 1px solid #E1DDD3; }"
    return write_pdf("source_code", "\n".join(parts), css)


def workbook() -> Path:
    feats = pd.read_csv(config.LAYER1_OUTPUT)
    jev = pd.read_csv(RES / "jev_outputs.csv")
    deep = pd.read_csv(RES / "deep_analysis.csv")
    keep_rank = ["rank", "opportunity_title", "final_score", "strategic_alignment", "operational_fit",
                 "financial_value_score", "deadline_score", "eligibility_confidence_score", "applicant_role_verified",
                 "owning_division", "matched_objective", "one_line_rationale", "major_risk", "close_date_real",
                 "forecasted_close_date", "award_value_usd", "requires_cost_share", "url"]
    readme = pd.DataFrame({"Sheet": [
        "Top results", "Open ranked", "Watchlist", "Research", "Jev screen", "DeepSeek review", "Award history",
        "Removed by rules", "Scoring formula"], "What it shows": [
        "Our submitted top 10 open + top 5 forecast grants, with one-line rationale and 5-criteria check",
        "All 33 open (non-research) grants that reached the formula, with every score component",
        "All 116 forecast grants (announced, not yet open), same columns",
        "All 134 research/training grants (NIH-style codes such as R01), routed to a university partner",
        "All 1,303 grants screened by Jev: its answer and probability for each question, and the routing decision",
        "All 283 grants reviewed by DeepSeek: scores, role, division, risk, rationale and quote checks",
        "For every screened grant: who received awards under its assistance listings in FY2022-25 (USAspending.gov)",
        "The 359 listings removed by plain rules, with the reason",
        "Score = 10 x (0.30 x strategic fit + 0.25 x can DHHS run it + 0.15 x award size + 0.15 x deadline + 0.15 x eligibility certainty); "
        "proven ineligible = 0; unverified strategic quote = -5; no deadline = -3 (-2 if 'apply anytime', 0 if first-come)"]})
    sheets = {
        "Read me": readme,
        "Top results": pd.read_csv(SUB / "top_results.csv", encoding="utf-8-sig"),
        "Open ranked": pd.read_csv(RES / "ranked_grants.csv").reindex(columns=keep_rank),
        "Watchlist": pd.read_csv(RES / "watchlist.csv").reindex(columns=keep_rank),
        "Research": pd.read_csv(RES / "research_partnerships.csv").reindex(columns=keep_rank),
        "Jev screen": jev[["grant_id", "opportunity_title", "track", "domain_relevance", "domain_relevance_p",
                           "matched_goal", "applicant_role", "applicant_role_p", "owning_division",
                           "triage_priority", "route", "route_reason"]],
        "DeepSeek review": deep[["grant_id", "opportunity_title", "strategic_alignment", "matched_objective",
                                 "operational_fit", "applicant_role", "applicant_role_verified", "owning_division",
                                 "strategic_quote_verified", "eligibility_quote_verified", "recommended_for_review",
                                 "one_line_rationale", "major_risk", "strategic_evidence_quote", "eligibility_evidence_quote"]],
        "Award history": pd.read_csv(RES / "award_history.csv")[["opportunity_title", "verdict", "nc_dhhs", "total",
                                                                  "state_agency_share", "university_share", "coverage",
                                                                  "alns", "top_recipients"]],
        "Removed by rules": feats[feats["hard_filtered"]][["opportunity_title", "hard_filter_reason", "close_date",
                                                           "agency_name"]],
    }
    out = SUB / "results_workbook.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.font = Font(bold=True)
            for col in ws.columns:
                width = max(len(str(c.value or "")) for c in list(col)[:60])
                ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 60)
    return out


if __name__ == "__main__":
    for f in (process_report(), source_code(), workbook()):
        print(f"Wrote {f}  ({f.stat().st_size / 1e6:.2f} MB)")
