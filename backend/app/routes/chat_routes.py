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
from app.services.rag_service import answer_question
from app.services.summary_service import summarize_video
from app.services.transcript_service import fetch_transcript

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
        history = [m.model_dump() for m in request.history]
        result = answer_question(request.video_id, request.question, history)
    except ValueError as e:
        # Raised by vectorstore_service if the video hasn't been processed yet.
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        # Raised by llm_service if the LLM API call fails.
        raise HTTPException(status_code=502, detail=str(e))

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
    )


@router.post("/summarize", response_model=SummaryResponse)
def summarize_video_endpoint(request: SummaryRequest):
    """
    Summarizes the full video. Long videos are summarized section by section
    (map-reduce) and also come back as timestamped chapters.

    Note: we re-fetch the transcript here (rather than reusing stored
    chunks) because summarization needs the FULL text with timestamps, while
    FAISS only stores it split into chunks. Re-fetching is cheap and keeps
    this endpoint independent/stateless.
    """
    try:
        transcript_segments = fetch_transcript(request.video_id)
        result = summarize_video(transcript_segments)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return SummaryResponse(
        video_id=request.video_id,
        summary=result["summary"],
        chapters=result["chapters"],
    )