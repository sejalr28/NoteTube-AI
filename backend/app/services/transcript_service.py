import xml.etree.ElementTree as ET

from fastapi import HTTPException
from youtube_transcript_api import YouTubeTranscriptApi

try:
    from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
except ImportError:
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

_PREFERRED_LANGS = ["en", "en-US", "en-GB"]


def _fetch_raw_segments(video_id: str) -> list[dict]:
    """
    Fetches raw transcript segments, supporting both the current
    instance-based API (YouTubeTranscriptApi().fetch(...)) and the
    legacy classmethod API (YouTubeTranscriptApi.get_transcript(...)),
    since the library's API surface changed between major versions.
    """
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=_PREFERRED_LANGS)

        if hasattr(fetched, "to_raw_data"):
            return fetched.to_raw_data()

        return [
            {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
            for snippet in fetched
        ]
    except AttributeError:
        return YouTubeTranscriptApi.get_transcript(video_id, languages=_PREFERRED_LANGS)


def fetch_transcript(video_id: str) -> list[dict]:
    """
    Fetches the transcript for a given YouTube video ID.

    Returns a list of segments, each shaped like:
        {"text": "some spoken words", "start": 12.4, "duration": 3.2}
    """
    try:
        transcript_segments = _fetch_raw_segments(video_id)
    except TranscriptsDisabled:
        raise HTTPException(
            status_code=422,
            detail="Transcripts are disabled for this video."
        )
    except NoTranscriptFound:
        raise HTTPException(
            status_code=422,
            detail="No English transcript is available for this video."
        )
    except VideoUnavailable:
        raise HTTPException(
            status_code=404,
            detail="This video is unavailable."
        )
    except ET.ParseError as e:
        raise HTTPException(
            status_code=502,
            detail=f"YouTube returned invalid transcript data: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch transcript: {str(e)}"
        )

    if not transcript_segments:
        raise HTTPException(
            status_code=422,
            detail="Transcript was empty for this video."
        )

    return transcript_segments


def transcript_to_plain_text(transcript_segments: list[dict]) -> str:
    """
    Joins all transcript segments into a single continuous string.
    Useful for full-video operations like summarization, where we don't
    need per-segment timestamps -- just the complete text.
    """
    return " ".join(segment["text"] for segment in transcript_segments)