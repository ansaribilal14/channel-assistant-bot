"""Keyword FAQ matcher — works with zero LLM, zero API cost.

Scoring model (per FAQ):
  +3.0  keyword appears as an exact word in the query
  +2.5  multi-word keyword appears as a phrase in the query
  +2.0  prefix match between keyword and a query word (min 4 chars)
  +1.0  keyword contained inside a query word (or vice versa), min 4 chars

The best-scoring FAQ wins if its score >= threshold (default 2.0, so a single
exact keyword hit is enough; near-misses need more evidence).
"""

from __future__ import annotations

import re
from typing import Optional

from core.config import Faq

_WORD_RE = re.compile(r"[a-z0-9']+")


def tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def score_query(query: str, keywords: list[str]) -> float:
    tokens = tokenize(query)
    score = 0.0
    for kw in keywords:
        kw_l = kw.lower().strip()
        if not kw_l:
            continue
        if " " in kw_l:  # multi-word phrase keyword
            if kw_l in query.lower():
                score += 2.5
            continue
        if kw_l in tokens:
            score += 3.0
            continue
        matched = False
        for t in tokens:
            if len(kw_l) >= 4 and len(t) >= 4 and (t.startswith(kw_l) or kw_l.startswith(t)):
                score += 2.0
                matched = True
                break
        if not matched and len(kw_l) >= 4:
            if any(kw_l in t or t in kw_l for t in tokens):
                score += 1.0
    return score


def best_answer(text: str, faqs: list[Faq], threshold: float = 2.0) -> tuple[Optional[int], float]:
    """Return (faq_index, score) of the best match, or (None, best_score)."""
    best_i: Optional[int] = None
    best_s = 0.0
    for i, f in enumerate(faqs):
        s = score_query(text, f.keywords)
        if s > best_s:
            best_i, best_s = i, s
    if best_s >= threshold:
        return best_i, best_s
    return None, best_s
