"""Tiny Markdown -> PDF for submission documents (headings, paragraphs, lists, tables,
bold/italic/code). No extra packages; prints with headless Edge or Chrome.

Usage:  python src/md_to_pdf.py submission/ai_usage.md
"""

import html
import re
import sys
from pathlib import Path

from submission_pdf import to_pdf

CSS = """@page { size: letter; margin: 0.7in; }
body { font-family: 'Segoe UI', Arial, sans-serif; color: #1B2A3A; font-size: 10.5pt; line-height: 1.45; }
h1 { font-family: Georgia, serif; font-size: 20pt; margin: 0 0 8px; }
h2 { font-size: 13pt; color: #2A6F97; margin: 16px 0 6px; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 6px 0; }
th { background: #16243A; color: #F4F1EA; text-align: left; padding: 4px 6px; }
td { border-bottom: 1px solid #DDD8CC; padding: 4px 6px; vertical-align: top; }
code { background: #F2EFE8; padding: 0 3px; font-size: 9pt; }
li { margin: 2px 0; } tr { page-break-inside: avoid; }
blockquote { margin: 8px 0; padding: 6px 12px; border-left: 4px solid #2A6F97; background: #F2EFE8; font-style: italic; }
img { max-width: 100%; }
h1, h2, h3 { break-after: avoid; page-break-after: avoid; } a { color: #2A6F97; }"""


def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r"<img alt='\1' src='\2'>", t)   # images before links
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"<a href='\2'>\1</a>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
    return t


def convert(md: str) -> str:
    out, lines, i = [], md.splitlines(), 0
    stack = []  # open list tags with their indent

    def close_lists(to_indent=-1):
        while stack and stack[-1][1] > to_indent:
            out.append(f"</{stack.pop()[0]}>")

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            close_lists(); i += 1; block = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(html.escape(lines[i])); i += 1
            out.append("<pre><code>" + "\n".join(block) + "</code></pre>"); i += 1; continue
        if line.startswith("|"):
            close_lists(); rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            out.append("<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
                       + "</table>"); continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", line)
        if m:
            indent, tag = len(m.group(1)), "ul" if m.group(2) in "-*" else "ol"
            if not stack or indent > stack[-1][1]:
                out.append(f"<{tag}>"); stack.append((tag, indent))
            else:
                close_lists(indent)
                if not stack:
                    out.append(f"<{tag}>"); stack.append((tag, indent))
            text = m.group(3)
            i += 1
            # A wrapped list item continues on indented lines that are not new items.
            while i < len(lines) and lines[i].startswith(" ") and lines[i].strip() \
                    and not re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                text += " " + lines[i].strip(); i += 1
            out.append(f"<li>{inline(text)}</li>"); continue
        close_lists()
        if line.startswith("### "):
            out.append(f"<h3>{inline(line[4:])}</h3>"); i += 1
        elif line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>"); i += 1
        elif line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>"); i += 1
        elif line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip(">").strip()); i += 1
            out.append(f"<blockquote>{inline(' '.join(quote))}</blockquote>")
        elif line.strip():
            # A paragraph runs until a blank line or the start of another block.
            para = [line.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#|>|\||```|\s*([-*]|\d+\.)\s+)", lines[i]):
                para.append(lines[i].strip()); i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
        else:
            i += 1
    close_lists()
    return "\n".join(out)


if __name__ == "__main__":
    src = Path(sys.argv[1]).resolve()
    page = src.with_suffix(".html")
    page.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head>"
                    f"<body>{convert(src.read_text(encoding='utf-8'))}</body></html>", encoding="utf-8")
    pdf = to_pdf(page)
    page.unlink()
    print(f"Wrote {pdf}")
