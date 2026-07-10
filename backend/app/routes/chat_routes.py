"""
chat_routes.py
----------------
REST API endpoints for:
  - Asking questions about a processed video (RAG Q&A)
  - Generating a summary of a processed video

AI/ML concept demonstrated: REST APIs + RAG + LLM integration, exposed
as clean HTTP endpoints the React frontend consumes.
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    SummaryRequest,
    SummaryResponse,
)
from app.services.rag_service import answer_question, summarize_transcript
from app.services.transcript_service import fetch_transcript, transcript_to_plain_text

router = APIRouter(prefix="/api/chat", tags=["Chat & Summary"])


@router.post("/ask", response_model=ChatResponse)
def ask_question(request: ChatRequest):
    """
    Answers a user's question about a video using RAG:
    retrieves relevant transcript chunks from FAISS, then asks the LLM
    to answer grounded only in those chunks.

    Requires the video to have been processed already via /api/video/process.
    """
    try:
        result = answer_question(request.video_id, request.question)
    except ValueError as e:
        # Raised by vectorstore_service if the video hasn't been processed yet.
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        # Raised by llm_service if the LLM API call fails.
        raise HTTPException(status_code=502, detail=str(e))

    return ChatResponse(
        answer=result["answer"],
        source_chunks=result["source_chunks"],
    )


@router.post("/summarize", response_model=SummaryResponse)
def summarize_video(request: SummaryRequest):
    """
    Generates a concise summary of the full video transcript.

    Note: we re-fetch the transcript here (rather than reusing stored
    chunks) because summarization needs the FULL text, while FAISS
    only stores it split into chunks. Re-fetching is cheap and keeps
    this endpoint independent/stateless.
    """
    try:
        transcript_segments = fetch_transcript(request.video_id)
        full_text = transcript_to_plain_text(transcript_segments)
        summary = summarize_transcript(full_text)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return SummaryResponse(
        video_id=request.video_id,
        summary=summary,
    )
