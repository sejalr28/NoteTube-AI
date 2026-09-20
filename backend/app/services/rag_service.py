"""
rag_service.py
----------------
Orchestrates the full RAG (Retrieval-Augmented Generation) pipeline and
handles video summarization.

AI/ML concepts demonstrated: RAG + PROMPT ENGINEERING.

RAG in plain terms:
  Instead of asking an LLM a question "cold" (where it might hallucinate
  or lack video-specific knowledge), we first RETRIEVE the most relevant
  transcript chunks via semantic search, then AUGMENT the LLM's prompt
  with that retrieved context, and finally GENERATE an answer. This
  grounds the model's response in facts that actually exist in the video,
  instead of relying purely on what the LLM "remembers" from training.

This file is intentionally the "brain" that ties together:
  vectorstore_service (retrieval) + llm_service (generation)
"""

from app.config import settings
from app.services.retrieval_service import retrieve_chunks
from app.services.llm_service import generate_completion

NOT_COVERED_ANSWER = (
    "This video doesn't seem to cover that. "
    "Try rephrasing, or ask about something discussed in the video."
)


def _format_history(history: list[dict]) -> str:
    return "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['text']}"
        for m in history
    )


def _rewrite_question(question: str, history: list[dict]) -> str:
    """
    Turns a follow-up like "why is that?" into a standalone question so
    retrieval has something meaningful to embed. Falls back to the original
    question if the LLM call fails -- retrieval just gets a bit weaker.
    """
    prompt = f"""Given the conversation below and a follow-up question, rewrite the \
follow-up as a single standalone question that makes sense without the conversation. \
If it is already standalone, return it unchanged. Output only the question.

Conversation:
{_format_history(history)}

Follow-up question: {question}

Standalone question:"""
    try:
        return generate_completion(prompt, temperature=0.0) or question
    except RuntimeError:
        return question


def answer_question(video_id: str, question: str, history: list[dict] | None = None) -> dict:
    """
    Full RAG flow for answering a user's question about a specific video.

    Steps:
      1. If there is chat history, rewrite the question to be standalone.
      2. Retrieve top-k semantically similar chunks from FAISS.
      3. If even the best chunk is a weak match, say the video doesn't cover it.
      4. Otherwise build a prompt that INSTRUCTS the LLM to answer using ONLY
         the retrieved context, and return the answer with timestamped sources.
    """
    history = (history or [])[-settings.HISTORY_MESSAGES:]
    search_query = _rewrite_question(question, history) if history else question

    retrieved_chunks = retrieve_chunks(video_id, search_query)

    # `score` is each chunk's cosine similarity to the question; reranking can
    # reorder chunks, so use the best of them rather than the first.
    if not retrieved_chunks or max(c["score"] for c in retrieved_chunks) < settings.MIN_SIMILARITY:
        return {"answer": NOT_COVERED_ANSWER, "sources": []}

    # Combine retrieved chunks into a single context block for the prompt.
    context_text = "\n\n".join(
        f"[Chunk {i+1}]: {chunk['text']}"
        for i, chunk in enumerate(retrieved_chunks)
    )

    history_block = (
        f"Conversation so far (only for understanding references like \"that\" or \"it\"):\n"
        f"{_format_history(history)}\n\n"
        if history
        else ""
    )

    # Prompt engineering: we explicitly tell the LLM to:
    #   - only use the provided context (reduces hallucination)
    #   - admit uncertainty if the answer isn't present
    #   - keep the answer concise and conversational
    prompt = f"""You are an assistant that answers questions about a YouTube video, \
using ONLY the transcript excerpts provided below. Do not use outside knowledge.

Transcript excerpts:
{context_text}

{history_block}Question: {question}

Instructions:
- Answer using only the information in the excerpts above.
- If the excerpts don't contain enough information to answer, say so honestly.
- Keep your answer clear and concise (3-5 sentences max).

Answer:"""

    answer = generate_completion(prompt)

    return {
        "answer": answer,
        "sources": [
            {"text": chunk["text"], "start_time": chunk["start_time"]}
            for chunk in retrieved_chunks
        ],
    }


def summarize_transcript(full_text: str) -> str:
    """
    Generates a concise summary of the entire video transcript.

    Unlike Q&A (which retrieves only a few relevant chunks), summarization
    needs the FULL transcript as context, since we're condensing the whole
    video rather than answering a specific narrow question.

    Note: for very long transcripts this could exceed the LLM's context
    window. For this intermediate-level project we keep it simple and pass
    the full text directly -- a production system might chunk-summarize-then
    combine ("map-reduce" summarization), but that's beyond this project's scope.
    """
    prompt = f"""Summarize the following YouTube video transcript into a clear, \
concise summary for someone who hasn't watched the video.

Transcript:
{full_text}

Instructions:
- Write 4-6 sentences capturing the key points and overall message.
- Use plain, easy-to-understand language.
- Do not include timestamps or filler commentary -- just the summary.

Summary:"""

    return generate_completion(prompt)
