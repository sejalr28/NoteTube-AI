"""
embedding_service.py
---------------------
Generates vector embeddings for text using sentence-transformers.

AI/ML concept demonstrated: EMBEDDINGS.
An embedding is a fixed-length numeric vector that captures the SEMANTIC
MEANING of a piece of text. Two chunks of text with similar meaning will
have embeddings that are close together in vector space, even if they
don't share the exact same words.

Example:
  "How does gradient descent work?" and "Explain the optimization algorithm"
  would produce vectors that are close together, because they mean similar
  things -- even though barely any words overlap.

We use "all-MiniLM-L6-v2": a small, fast, CPU-friendly model that produces
384-dimensional embeddings. It's a popular choice for portfolio/production
RAG projects because it balances speed and semantic quality well.

Why load the model once at module level (not inside a function):
Loading a transformer model from disk is slow (~1-2 seconds). We want this
to happen ONCE when the server starts, not on every single request.
"""

from sentence_transformers import SentenceTransformer
from app.config import settings

# Loaded once when this module is first imported (i.e. at server startup).
_model = SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Converts a list of text strings into a list of embedding vectors.
    Used when embedding all chunks of a transcript at once (batch operation).

    Returns:
        A list where each element is a 384-dimensional float vector.
    """
    # convert_to_numpy=False keeps output as plain Python lists,
    # which FAISS expects for storage.
    embeddings = _model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """
    Converts a single query string (e.g. a user's question) into an
    embedding vector. Used at question-answering time to find the most
    semantically similar transcript chunks via FAISS.
    """
    embedding = _model.encode(query, convert_to_numpy=True)
    return embedding.tolist()
