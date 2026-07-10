"""
chunking_service.py
--------------------
Splits a long transcript into smaller overlapping chunks.

AI/ML concept demonstrated: CHUNKING.
Why chunk at all?
  - Embedding models and LLMs have limited context windows.
  - Smaller chunks -> more precise semantic search (a 500-char chunk about
    "backpropagation" is easier to match than one giant 10,000-char blob).
  - Overlap between chunks prevents losing meaning when a sentence gets
    cut across a chunk boundary (e.g. "...gradient descent works by..."
    should not be split away from the sentence that explains it).

We chunk using the ORIGINAL timestamped segments (not plain text) so each
chunk retains a "start_time" -- this powers future features like jumping
to the exact moment in the video a chunk came from.
"""

from app.config import settings


def chunk_transcript(transcript_segments: list[dict]) -> list[dict]:
    """
    Groups timestamped transcript segments into overlapping text chunks.

    Args:
        transcript_segments: list of {"text", "start", "duration"} dicts
                              from the YouTube Transcript API.

    Returns:
        list of {"chunk_id", "text", "start_time"} dicts, ready for embedding.
    """
    chunk_size = settings.CHUNK_SIZE
    chunk_overlap = settings.CHUNK_OVERLAP

    chunks = []
    current_text = ""
    current_start_time = transcript_segments[0]["start"] if transcript_segments else 0.0
    chunk_id = 0

    for segment in transcript_segments:
        # If adding this segment would exceed our target chunk size,
        # finalize the current chunk and start a new one.
        if len(current_text) + len(segment["text"]) > chunk_size and current_text:
            chunks.append({
                "chunk_id": chunk_id,
                "text": current_text.strip(),
                "start_time": current_start_time,
            })
            chunk_id += 1

            # Build overlap: carry the tail end of the previous chunk forward
            # so context isn't lost at the boundary.
            overlap_text = current_text[-chunk_overlap:] if chunk_overlap > 0 else ""
            current_text = overlap_text + " " + segment["text"]
            current_start_time = segment["start"]
        else:
            if current_text == "":
                current_start_time = segment["start"]
            current_text += " " + segment["text"]

    # Don't forget the final chunk after the loop ends.
    if current_text.strip():
        chunks.append({
            "chunk_id": chunk_id,
            "text": current_text.strip(),
            "start_time": current_start_time,
        })

    return chunks
