"""
metrics.py
----------
Pure functions for scoring retrieval. No app imports, so they are easy to test.

A retrieved chunk counts as "correct" if it contains the question's
`evidence` phrase (a short phrase copied from the transcript). Matching on
text instead of chunk IDs means the same eval set still works after you
change the chunking strategy in Phase 3.
"""

import re


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def contains_evidence(chunk_text: str, evidence: str | None) -> bool:
    return bool(evidence) and normalize(evidence) in normalize(chunk_text)


def retrieval_metrics(rows: list[dict]) -> dict:
    """hit@k and MRR over answerable rows. Each row needs a `rank` (1-based, or None if missed)."""
    answerable = [r for r in rows if r["answerable"]]
    if not answerable:
        return {}
    n = len(answerable)

    def hit(k: int) -> float:
        return sum(1 for r in answerable if r["rank"] and r["rank"] <= k) / n

    return {
        "hit@1": hit(1),
        "hit@4": hit(4),
        "hit@10": hit(10),
        "mrr@10": sum(1 / r["rank"] for r in answerable if r["rank"]) / n,
    }


def threshold_sweep(rows: list[dict], thresholds: list[float]) -> list[dict]:
    """
    For each MIN_SIMILARITY candidate: how many answerable questions would still
    be answered, and how many unanswerable ones would be correctly rejected.
    Uses each row's `top_score` (similarity of its best retrieved chunk).
    """
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    sweep = []
    for t in thresholds:
        kept = (
            sum(r["top_score"] >= t for r in answerable) / len(answerable)
            if answerable else None
        )
        rejected = (
            sum(r["top_score"] < t for r in unanswerable) / len(unanswerable)
            if unanswerable else None
        )
        sweep.append({
            "threshold": t,
            "answerable_kept": kept,
            "unanswerable_rejected": rejected,
        })
    return sweep
