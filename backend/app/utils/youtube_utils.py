"""
youtube_utils.py
-----------------
Small helper functions for working with YouTube URLs and metadata.

Why a separate file:
URL parsing and metadata lookup are unrelated to transcript-fetching
logic. Keeping them separate follows the Single Responsibility Principle
-- each file does ONE clear job, which makes the codebase easier to
navigate and explain.
"""

import re

import requests
from fastapi import HTTPException

# YouTube's public oEmbed endpoint returns basic metadata (title, author,
# thumbnail) for any public video with a single unauthenticated GET
# request -- no API key required, and no new dependency, since `requests`
# is already used elsewhere in this project.
_OEMBED_URL = "https://www.youtube.com/oembed"


def extract_video_id(youtube_url: str) -> str:
    """
    Extracts the 11-character YouTube video ID from various URL formats:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID
      - https://www.youtube.com/shorts/VIDEO_ID

    We use a regex instead of a heavy URL-parsing library because the
    pattern is simple and predictable -- keeping dependencies minimal.
    """
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",   # watch?v= or /VIDEO_ID
        r"youtu\.be\/([0-9A-Za-z_-]{11})",   # short links
        r"embed\/([0-9A-Za-z_-]{11})",       # embed links
        r"shorts\/([0-9A-Za-z_-]{11})",      # YouTube Shorts
    ]

    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)

    raise HTTPException(
        status_code=400,
        detail="Could not extract a valid video ID from the provided YouTube URL."
    )


def fetch_video_metadata(video_id: str) -> dict:
    """
    Fetches the video's title and thumbnail URL via YouTube's oEmbed
    endpoint. This is best-effort: if the lookup fails for any reason
    (network hiccup, private video, etc.), we fall back to a generic
    title and YouTube's predictable thumbnail URL pattern rather than
    failing the whole request -- metadata is a nice-to-have, not
    something that should block transcript processing.
    """
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    fallback_thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    try:
        response = requests.get(
            _OEMBED_URL,
            params={"url": watch_url, "format": "json"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        return {
            "title": data.get("title", f"YouTube video ({video_id})"),
            "thumbnail_url": data.get("thumbnail_url", fallback_thumbnail),
        }
    except Exception:
        return {
            "title": f"YouTube video ({video_id})",
            "thumbnail_url": fallback_thumbnail,
        }

