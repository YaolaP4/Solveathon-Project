"""Text cleanup and the verbatim-quote check used to catch hallucinated evidence."""

import html
import re

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_PUNCT_MAP = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
})


def strip_html(text) -> str:
    """Grant summaries often contain raw HTML (<p>, <br>, &amp;). Return plain text."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"(?i)<br\s*/?>|</p>|</li>", "\n", text)
    text = _TAG.sub(" ", text)
    return html.unescape(text).strip()


def normalize(text: str) -> str:
    """Lowercase, unify quotes/dashes, collapse whitespace. Used only for matching."""
    text = strip_html(text).translate(_PUNCT_MAP).lower()
    return _WS.sub(" ", text).strip()


def quote_in_source(quote, source: str, min_chars: int = 12) -> bool:
    """True if `quote` appears verbatim (after normalization) in `source`.

    Models sometimes shorten a quote with "..." -- each fragment must then appear
    in order. Quotes shorter than `min_chars` are rejected: too short to be evidence.
    """
    if not isinstance(quote, str) or not quote.strip():
        return False
    src = normalize(source)
    fragments = [normalize(f) for f in re.split(r"\.\.\.|…", quote)]
    fragments = [f.strip(" \"'") for f in fragments if f.strip(" \"'")]
    if not fragments or sum(len(f) for f in fragments) < min_chars:
        return False
    pos = 0
    for frag in fragments:
        i = src.find(frag, pos)
        if i < 0:
            return False
        pos = i + len(frag)
    return True


def truncate(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + " [truncated]"
