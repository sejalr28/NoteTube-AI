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

from app.services.vectorstore_service import query_similar_chunks
from app.services.llm_service import generate_completion


def answer_question(video_id: str, question: str) -> dict:
    """
    Full RAG flow for answering a user's question about a specific video.

    Steps:
      1. Retrieve top-k semantically similar chunks from FAISS.
      2. Build a prompt that INSTRUCTS the LLM to answer using ONLY
         that retrieved context (this is the "prompt engineering" part --
         we explicitly constrain the model's behavior).
      3. Send the prompt to the LLM and return its answer.
    """
    retrieved_chunks = query_similar_chunks(video_id, question)

    if not retrieved_chunks:
        return {
            "answer": "I couldn't find relevant information in this video to answer that.",
            "source_chunks": [],
        }

    # Combine retrieved chunks into a single context block for the prompt.
    context_text = "\n\n".join(
        f"[Chunk {i+1}]: {chunk['text']}"
        for i, chunk in enumerate(retrieved_chunks)
    )

    # Prompt engineering: we explicitly tell the LLM to:
    #   - only use the provided context (reduces hallucination)
    #   - admit uncertainty if the answer isn't present
    #   - keep the answer concise and conversational
    prompt = f"""You are an assistant that answers questions about a YouTube video, \
using ONLY the transcript excerpts provided below. Do not use outside knowledge.

Transcript excerpts:
{context_text}

Question: {question}

Instructions:
- Answer using only the information in the excerpts above.
- If the excerpts don't contain enough information to answer, say so honestly.
- Keep your answer clear and concise (3-5 sentences max).

Answer:"""

    answer = generate_completion(prompt)

    return {
        "answer": answer,
        "source_chunks": [chunk["text"] for chunk in retrieved_chunks],
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
