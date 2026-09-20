"""
retrieval_service.py
--------------------
The retrieval step of RAG: given a question, return the best transcript chunks.

Pipeline:
  1. DENSE search (FAISS): finds chunks with similar MEANING to the question.
  2. Optional HYBRID (USE_HYBRID): also run BM25 KEYWORD search and merge both
     rankings with Reciprocal Rank Fusion (RRF). Dense search can miss exact
     terms, numbers and names; BM25 catches those.
  3. Optional RERANK (USE_RERANKER): a cross-encoder reads the question and each
     candidate chunk TOGETHER and re-scores them. It is slower than the vector
     search but much better at picking the chunk that actually answers.

Both options are off by default so results match the baseline. Turn them on
via settings (env vars) and compare with `python -m eval.run_eval`.
"""

import re

import numpy as np

from app.config import settings
from app.services.embedding_service import embed_query
from app.services.vectorstore_service import load_video

_TOKEN = re.compile(r"[a-z0-9]+")
_RRF_K = 60  # standard RRF constant: dampens the advantage of rank 1 over rank 2

_reranker = None


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _get_reranker():
    """Loads the cross-encoder once, on first use (it is a ~90 MB download the first time)."""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(settings.RERANKER_MODEL)
    return _reranker


def _bm25_ranking(question: str, metadata: list[dict], n: int) -> list[int]:
    """Chunk positions ranked by BM25 keyword match. Chunks sharing no query word are left out."""
    from rank_bm25 import BM25Okapi

    bm25 = BM25Okapi([_tokenize(chunk["text"]) for chunk in metadata])
    scores = bm25.get_scores(_tokenize(question))
    order = np.argsort(scores)[::-1][:n]
    return [int(i) for i in order if scores[i] > 0]


def _rrf(rankings: list[list[int]]) -> list[int]:
    """Reciprocal Rank Fusion: a chunk scores 1/(k+rank) in each list it appears in."""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, pos in enumerate(ranking, start=1):
            fused[pos] = fused.get(pos, 0.0) + 1.0 / (_RRF_K + rank)
    return sorted(fused, key=fused.get, reverse=True)


def _rerank(question: str, metadata: list[dict], ranking: list[int]) -> list[int]:
    scores = _get_reranker().predict([(question, metadata[pos]["text"]) for pos in ranking])
    ordered = sorted(zip(scores, ranking), key=lambda pair: pair[0], reverse=True)
    return [pos for _, pos in ordered]


def retrieve_chunks(video_id: str, question: str, top_k: int | None = None) -> list[dict]:
    """
    Returns up to top_k chunks as {"text", "start_time", "score"}, best first.
    `score` is always the chunk's cosine similarity to the question, whichever
    ranking method is on, so MIN_SIMILARITY keeps the same meaning.
    """
    top_k = top_k or settings.TOP_K_RESULTS
    index, metadata = load_video(video_id)

    query_vector = np.array([embed_query(question)], dtype="float32")
    query_vector /= max(float(np.linalg.norm(query_vector)), 1e-10)

    pool = min(max(settings.CANDIDATE_POOL, top_k), index.ntotal)
    scores, positions = index.search(query_vector, pool)
    dense_score = {int(p): float(s) for s, p in zip(scores[0], positions[0]) if p != -1}
    ranking = list(dense_score)  # FAISS returns best first

    if settings.USE_HYBRID:
        ranking = _rrf([ranking, _bm25_ranking(question, metadata, pool)])

    if settings.USE_RERANKER:
        ranking = _rerank(question, metadata, ranking)

    return [
        {
            "text": metadata[pos]["text"],
            "start_time": metadata[pos]["start_time"],
            # BM25-only candidates weren't in the dense results, so compute their cosine directly.
            "score": dense_score[pos] if pos in dense_score
            else float(index.reconstruct(pos) @ query_vector[0]),
        }
        for pos in ranking[:top_k]
    ]
