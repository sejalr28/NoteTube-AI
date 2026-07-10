"""
video_routes.py
-----------------
REST API endpoint for processing a YouTube video end-to-end:
  URL -> video ID -> transcript -> chunks -> embeddings -> FAISS storage

AI/ML concept demonstrated: REST APIs.
This endpoint exposes our entire preprocessing pipeline as a single,
simple HTTP call the React frontend can hit whenever a user submits a URL.
"""

import time

from fastapi import APIRouter, HTTPException

from app.models.schemas import VideoRequest, VideoProcessResponse
from app.utils.youtube_utils import extract_video_id, fetch_video_metadata
from app.services.transcript_service import fetch_transcript
from app.services.chunking_service import chunk_transcript
from app.services.vectorstore_service import store_chunks

router = APIRouter(prefix="/api/video", tags=["Video Processing"])


@router.post("/process", response_model=VideoProcessResponse)
def process_video(request: VideoRequest):
    """
    Full pipeline endpoint. Given a YouTube URL:
      1. Extract the video ID
      2. Fetch the transcript
      3. Split it into overlapping chunks
      4. Embed and store chunks in FAISS (index = video_id)

    After this succeeds, the frontend can call /api/chat/ask and
    /api/chat/summarize using the returned video_id.
    """
    start_time = time.monotonic()

    video_id = extract_video_id(request.youtube_url)

    transcript_segments = fetch_transcript(video_id)

    if not transcript_segments:
        raise HTTPException(
            status_code=422,
            detail="Transcript was empty for this video."
        )

    chunks = chunk_transcript(transcript_segments)

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="Could not generate any chunks from this transcript."
        )

    store_chunks(video_id, chunks)

    # Best-effort metadata lookup (title + thumbnail) -- never blocks
    # or fails the response, since it's a nice-to-have for the UI.
    metadata = fetch_video_metadata(video_id)

    elapsed_seconds = round(time.monotonic() - start_time, 2)

    return VideoProcessResponse(
        video_id=video_id,
        title=metadata["title"],
        thumbnail_url=metadata["thumbnail_url"],
        num_chunks=len(chunks),
        processing_time_seconds=elapsed_seconds,
        message="Indexed successfully. You can now ask questions or request a summary."
    )
