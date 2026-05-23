import re
import hashlib
from datetime import date, timedelta


def slugify(sender: str, title: str) -> str:
    """Generate a URL-safe slug for an article."""
    raw = f"{sender}-{title}"
    raw = raw.lower().strip()
    raw = re.sub(r"[^\w\s-]", "", raw)
    raw = re.sub(r"[\s_]+", "-", raw)
    raw = re.sub(r"-+", "-", raw)
    return raw[:100]


# Invisible spacer characters used in HTML emails as layout separators.
# Repeating sequences of these (3+) typically indicate a paragraph break.
_INVISIBLE_SPACERS = re.compile(
    r"[­͏ -‏  ‪-  ⁠⠀﻿]{3,}"
)

# Known section headers that start new paragraphs in financial newsletters
_SECTION_HEADERS = re.compile(
    r"\b("
    r"What Wall Street Is Talking About|What Wall Street is talking about|"
    r"Markets at a Glance|One Big Story|What's Coming Up|"
    r"Behind America'?s|About Us|Subscribe|Read More|"
    r"Market Talk|The Eagle Eye|Daily Insights|"
    r"WHAT'S HAPPENING|Big Number|The Big Number|"
    r"In Case You Missed|Editor's Pick|Top Stories|"
    r"Coming Up|Also in the News"
    r")\b",
    re.IGNORECASE,
)


def split_paragraphs(text: str) -> list[str]:
    """Split plain text into meaningful paragraphs."""
    # Step 1: Normalize invisible spacer sequences to double newlines
    text = _INVISIBLE_SPACERS.sub("\n\n", text)

    # Step 2: Insert breaks before known section headers
    text = _SECTION_HEADERS.sub(r"\n\n\1", text)

    # Step 3: Collapse whitespace runs (but not newlines)
    text = re.sub(r"[^\S\n]{2,}", " ", text)

    # Step 4: Split on double newlines
    parts = text.split("\n\n")
    if len(parts) <= 1:
        # Fallback: split on single newlines
        parts = text.split("\n")

    # Step 5: Clean and filter paragraphs
    result = []
    for p in parts:
        # Normalize internal whitespace
        p = re.sub(r"\s+", " ", p).strip()
        # Filter noise
        if not p:
            continue
        if len(p) < 40 and not _is_likely_header(p):
            continue
        if re.match(r"^[\s­ -‏﻿]+$", p):
            continue
        result.append(p)

    # Step 6: If still only 1 giant paragraph, try sentence-boundary splitting
    if len(result) <= 1 and result:
        result = _split_by_sentences(result[0])

    return result


def _is_likely_header(text: str) -> bool:
    """Check if short text looks like a section header."""
    return bool(re.match(r"^[A-Z][A-Za-z\s&']{3,40}$", text))


def _split_by_sentences(text: str) -> list[str]:
    """Split a long text block into paragraph groups by topic/sentence proximity."""
    # Split into sentences
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)

    # Group sentences into paragraphs (3-5 sentences per paragraph)
    paras = []
    buf = []
    for s in sents:
        buf.append(s)
        if len(buf) >= 4:
            merged = " ".join(buf)
            if len(merged) > 80:
                paras.append(merged)
            buf = []
    if buf:
        merged = " ".join(buf)
        if len(merged) > 40:
            paras.append(merged)

    return paras if len(paras) > 1 else [text]


