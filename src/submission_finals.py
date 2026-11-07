"""Build the finals upload: Solution Design + GenAI Field Notes in one PDF (the form takes documents, not zips).

    python src/submission_finals.py
Writes submission/Solution_Design_and_GenAI_Field_Notes.pdf
"""

from pathlib import Path

import config
from md_to_pdf import CSS, convert
from submission_pdf import to_pdf

DOCS = config.ROOT / "docs"
OUT = config.ROOT / "submission" / "Solution_Design_and_GenAI_Field_Notes.html"
BREAK = "<div style='page-break-before: always'></div>"


def build() -> Path:
    design = convert((DOCS / "solution_design.md").read_text(encoding="utf-8"))
    notes = convert((DOCS / "finals_field_notes.md").read_text(encoding="utf-8"))
    # The design embeds docs/diagrams/...; the combined page sits in submission/, so point one level up.
    design = design.replace("src='diagrams/", "src='../docs/diagrams/")
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>Solution Design and GenAI Field Notes</title>"
            f"<style>{CSS} h3 {{ font-size: 11pt; margin: 10px 0 4px; }} pre {{ white-space: pre-wrap; }}</style></head>"
            f"<body>{design}{BREAK}{notes}</body></html>")
    OUT.write_text(page, encoding="utf-8")
    pdf = to_pdf(OUT)
    OUT.unlink()
    return pdf


if __name__ == "__main__":
    print(f"Wrote {build()}")
