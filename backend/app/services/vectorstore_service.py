"""
vectorstore_service.py
------------------------
Wraps FAISS operations: storing chunk embeddings and running semantic
(similarity) search over them.

AI/ML concept demonstrated: VECTOR DATABASES + SEMANTIC SEARCH.
FAISS (Facebook AI Similarity Search) is a library for fast nearest-neighbor
search over dense vectors. Unlike a full vector database, FAISS itself only
stores VECTORS and their positions -- it has no built-in concept of
"documents" or metadata. So we pair each FAISS index with a small JSON
"sidecar" file that stores the original chunk text + timestamp for each
vector, in the same order they were added to the index. This is a common,
lightweight pattern for small-to-medium RAG projects.

Design choice: ONE INDEX FILE PER VIDEO.
Each YouTube video gets its own FAISS index (video_id.index) plus a
matching metadata file (video_id.json). This keeps videos fully isolated
-- asking a question about Video A will never retrieve chunks from Video B.
Re-processing the same video simply overwrites both files.

Similarity metric: COSINE SIMILARITY via normalized vectors + inner product.
We L2-normalize every embedding before storing/querying, then use FAISS's
IndexFlatIP (inner product). For normalized vectors, inner product is
mathematically equivalent to cosine similarity -- a standard trick to get
cosine-based search out of FAISS's simpler index types.
"""

import os
import json
import faiss
import numpy as np

from app.config import settings
from app.services.embedding_service import embed_texts, embed_query

# Ensure the storage directory exists at startup.
os.makedirs(settings.FAISS_INDEX_DIR, exist_ok=True)


def _index_path(video_id: str) -> str:
    return os.path.join(settings.FAISS_INDEX_DIR, f"{video_id}.index")


def _metadata_path(video_id: str) -> str:
    return os.path.join(settings.FAISS_INDEX_DIR, f"{video_id}.json")


def _normalize(vectors: np.ndarray) -> np.ndarray:
    """
    L2-normalizes vectors so that inner product search behaves like
    cosine similarity search. Each vector is scaled to unit length.
    """
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10  # avoid division by zero for edge-case zero vectors
    return vectors / norms


def store_chunks(video_id: str, chunks: list[dict]) -> None:
    """
    Embeds and stores all chunks for a video as a FAISS index, with a
    matching JSON sidecar file holding each chunk's text + start_time.

    If the video was processed before, both files are simply overwritten
    so we never accumulate stale/duplicate data.
    """
    texts = [chunk["text"] for chunk in chunks]
    embeddings = np.array(embed_texts(texts), dtype="float32")
    embeddings = _normalize(embeddings)

    embedding_dim = embeddings.shape[1]

    # IndexFlatIP = exact (brute-force) inner-product search.
    # "Flat" means no approximation -- ideal for small/medium datasets like
    # a single video's transcript, and simplest to explain in an interview.
    index = faiss.IndexFlatIP(embedding_dim)
    index.add(embeddings)

    faiss.write_index(index, _index_path(video_id))

    # Sidecar metadata, stored in the SAME ORDER as vectors were added.
    # FAISS returns integer positions on search -- we map those positions
    # back to this list to recover the original text + timestamp.
    metadata = [
        {"chunk_id": chunk["chunk_id"], "text": chunk["text"], "start_time": chunk["start_time"]}
        for chunk in chunks
    ]
    with open(_metadata_path(video_id), "w", encoding="utf-8") as f:
        json.dump(metadata, f)


def query_similar_chunks(video_id: str, question: str, top_k: int = None) -> list[dict]:
    """
    Given a user's question, finds the top_k most semantically similar
    chunks from the video's transcript.

    This is the RETRIEVAL step of RAG: we narrow a potentially large
    transcript down to just the few chunks most relevant to the question,
    so only that focused context gets passed to the LLM.
    """
    if top_k is None:
        top_k = settings.TOP_K_RESULTS

    index_path = _index_path(video_id)
    metadata_path = _metadata_path(video_id)

    if not os.path.exists(index_path) or not os.path.exists(metadata_path):
        raise ValueError(
            f"No processed data found for video_id '{video_id}'. "
            "Please process the video first."
        )

    index = faiss.read_index(index_path)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    query_vector = np.array([embed_query(question)], dtype="float32")
    query_vector = _normalize(query_vector)

    # FAISS search returns two arrays: similarity scores and positions.
    # Positions map back into `metadata`; scores (cosine similarity, since
    # vectors are normalized) let the caller decide if a match is good enough.
    top_k = min(top_k, index.ntotal)  # guard against asking for more than exist
    scores, positions = index.search(query_vector, top_k)

    retrieved_chunks = [
        {
            "text": metadata[pos]["text"],
            "start_time": metadata[pos]["start_time"],
            "score": float(score),
        }
        for score, pos in zip(scores[0], positions[0])
        if pos != -1  # FAISS pads with -1 if fewer than top_k results exist
    ]

    return retrieved_chunks
