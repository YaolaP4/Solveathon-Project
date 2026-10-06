"""Render submission/top_results.csv as a print-ready page and PDF (submission item 1).

Usage:  python src/submission_pdf.py      (run src/submission_table.py first)
Writes submission/top_results.html and submission/top_results.pdf (via headless Edge or Chrome).
"""

import html
import shutil
import subprocess
from pathlib import Path

import pandas as pd

import config

SUB = config.ROOT / "submission"
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe", "msedge", "google-chrome", "chromium"]


def criteria_cells(check: str) -> str:
    parts = [p.strip() for p in check.split("|")]
    return "<br>".join(html.escape(p) for p in parts)


def table(rows: pd.DataFrame) -> str:
    out = ["<table><thead><tr><th>#</th><th>Grant</th><th>Score</th><th>Why it fits (one line)</th>"
           "<th>Check against our 5 criteria</th><th>NC DHHS won<br>FY22–25</th></tr></thead><tbody>"]
    for r in rows.itertuples():
        out.append(
            f"<tr><td class=n>{r.rank}</td>"
            f"<td class=g><a href='{html.escape(r.link)}'>{html.escape(r.grant)}</a></td>"
            f"<td class=s>{r.score_0_100}</td>"
            f"<td>{html.escape(r.one_line_rationale)}</td>"
            f"<td class=c>{criteria_cells(r.criteria_check)}</td>"
            f"<td class=w>{html.escape(r.nc_dhhs_awards_fy22_25)}</td></tr>")
    out.append("</tbody></table>")
    return "".join(out)


def build() -> Path:
    df = pd.read_csv(SUB / "top_results.csv", encoding="utf-8-sig")
    agency = config.load_agency()
    w = agency["layer4_scoring"]["weights"]
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>NC DHHS top grant opportunities</title>
<style>
@page {{ size: letter landscape; margin: 0.45in; }}
body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1B2A3A; font-size: 9.5pt; margin: 0; }}
h1 {{ font-family: Georgia, serif; font-size: 19pt; margin: 0 0 2px; }}
.sub {{ color: #4A5568; margin: 0 0 8px; }}
.box {{ background: #F2EFE8; border-left: 4px solid #2A6F97; padding: 6px 10px; margin: 0 0 10px; }}
h2 {{ font-size: 12.5pt; margin: 12px 0 4px; color: #2A6F97; }}
table {{ border-collapse: collapse; width: 100%; }}
th {{ background: #16243A; color: #F4F1EA; text-align: left; padding: 4px 6px; font-size: 8.5pt; }}
td {{ border-bottom: 1px solid #DDD8CC; padding: 4px 6px; vertical-align: top; }}
tr:nth-child(even) td {{ background: #FAF8F3; }}
td.n, td.s {{ text-align: center; font-weight: 700; }} td.s {{ color: #2A6F97; font-size: 11pt; }}
td.g {{ width: 19%; font-weight: 600; }} td.c {{ width: 30%; font-size: 8pt; color: #3E4C5E; }} td.w {{ width: 8%; }}
a {{ color: #1B2A3A; text-decoration: none; }}
.foot {{ margin-top: 8px; font-size: 8pt; color: #6B7684; }}
tr {{ page-break-inside: avoid; }}
</style></head><body>
<h1>Top federal grant opportunities for NC DHHS</h1>
<p class=sub>For the NC DHHS federal-grants coordinator · grants as of 30 Sep 2026 (Grants.gov export pulled 18 Aug 2026) · NC DHHS award history from USAspending.gov, FY2022–FY2025</p>
<div class=box><b>Our 5 match criteria:</b> (1) DHHS can apply, as lead or partner (a gate) · (2) supports a goal in the DHHS 2023–2025 Strategic Plan ·
(3) a DHHS division already does this work · (4) realistic time to apply · (5) award worth the effort.<br>
<b>Score (0–100), a published formula, not AI:</b> strategic fit {w['strategic_alignment']:.0%} · DHHS can run it {w['operational_fit']:.0%} ·
award size {w['financial_value_score']:.0%} · deadline {w['deadline_score']:.0%} · eligibility certainty {w['eligibility_confidence_score']:.0%}.
Rationales are written by AI (DeepSeek V4 Pro) and backed by verified quotes from each grant; scores are computed in Python.</div>
<h2>Apply now: top 10 open opportunities</h2>
{table(df[df['list'] == 'Apply now'])}
<h2 style='page-break-before: always'>Prepare now: top 5 forecast opportunities (announced, not yet open)</h2>
{table(df[df['list'] != 'Apply now'])}
<p class=foot>Full method, code and every number: github.com/YaolaP4/Solveathon-Project (submission/README.md). Grant names link to the Grants.gov listing.</p>
</body></html>"""
    out_html = SUB / "top_results.html"
    out_html.write_text(page, encoding="utf-8")
    return out_html


def to_pdf(src: Path) -> Path | None:
    pdf = src.with_suffix(".pdf")
    pdf.unlink(missing_ok=True)  # never report a stale PDF as freshly built
    for b in BROWSERS:
        exe = b if Path(b).exists() else shutil.which(b)
        if not exe:
            continue
        subprocess.run([exe, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf}", src.resolve().as_uri()], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        if pdf.exists():
            return pdf
    return None


if __name__ == "__main__":
    h = build()
    p = to_pdf(h)
    print(f"Wrote {h}" + (f" and {p}" if p else " (no browser found for PDF)"))
