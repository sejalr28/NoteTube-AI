"""
study_routes.py
----------------
REST API endpoints for study tools built from a video's transcript:
  - Multiple-choice quiz
  - Flashcards
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    FlashcardRequest,
    FlashcardResponse,
    QuizRequest,
    QuizResponse,
)
from app.services.study_service import generate_flashcards, generate_quiz
from app.services.transcript_service import fetch_transcript

router = APIRouter(prefix="/api/study", tags=["Study tools"])


@router.post("/quiz", response_model=QuizResponse)
def make_quiz(request: QuizRequest):
    """Generates a multiple-choice quiz, one question per spread-out section of the video."""
    try:
        segments = fetch_transcript(request.video_id)
        questions = generate_quiz(segments, request.count)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return QuizResponse(video_id=request.video_id, questions=questions)


@router.post("/flashcards", response_model=FlashcardResponse)
def make_flashcards(request: FlashcardRequest):
    """Generates study flashcards, one per spread-out section of the video."""
    try:
        segments = fetch_transcript(request.video_id)
        cards = generate_flashcards(segments, request.count)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return FlashcardResponse(video_id=request.video_id, cards=cards)