"""
schemas.py
----------
Pydantic models define the "shape" of data flowing in and out of our API.

Why this matters for an AI/ML backend:
FastAPI uses these models to automatically:
  1. Validate incoming request data (e.g. reject a request with no URL)
  2. Serialize outgoing responses into consistent JSON
  3. Generate interactive API docs at /docs

Keeping all schemas in one file makes it easy to see the full "API contract"
at a glance.
"""

from pydantic import BaseModel, Field
from typing import List, Literal


# ---------- Requests ----------

class VideoRequest(BaseModel):
    """Sent when the user submits a YouTube URL to be processed."""
    youtube_url: str = Field(..., description="Full YouTube video URL")


class ChatMessage(BaseModel):
    """One earlier message in the conversation."""
    role: Literal["user", "assistant"]
    text: str


class ChatRequest(BaseModel):
    """Sent when the user asks a question about a previously processed video."""
    video_id: str = Field(..., description="YouTube video ID (used as FAISS index filename)")
    question: str = Field(..., description="User's natural language question")
    history: List[ChatMessage] = Field(
        default_factory=list,
        description="Recent chat messages (oldest first), used to resolve follow-up questions",
    )


class SummaryRequest(BaseModel):
    """Sent to request a summary for a previously processed video."""
    video_id: str = Field(..., description="YouTube video ID")


# ---------- Responses ----------

class VideoProcessResponse(BaseModel):
    """Returned after a video has been fully processed (transcript -> embeddings -> stored)."""
    video_id: str
    title: str
    thumbnail_url: str
    num_chunks: int
    processing_time_seconds: float
    message: str


class Source(BaseModel):
    """A transcript chunk used to ground an answer, with where it starts in the video."""
    text: str
    start_time: float  # seconds from the start of the video


class ChatResponse(BaseModel):
    """Returned after answering a user's question via RAG."""
    answer: str
    sources: List[Source]  # empty when the video doesn't cover the question


class SummaryResponse(BaseModel):
    """Returned after generating a video summary."""
    video_id: str
    summary: str
