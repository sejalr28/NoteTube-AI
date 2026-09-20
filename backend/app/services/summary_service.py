"""
summary_service.py
------------------
Summarizes a whole video (including long ones) and builds a chapter list.

Short transcripts: one LLM call (rag_service.summarize_transcript).

Long transcripts use MAP-REDUCE, so they never overflow the LLM's context window:
  MAP:    split the transcript into ~6,000-character sections; the LLM gives each
          section a title and a short summary. These become timestamped chapters.
  REDUCE: the LLM writes the overall summary from the chapter summaries, which
          are short enough to always fit.
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

from app.services.llm_service import generate_completion
from app.services.rag_service import summarize_transcript
from app.services.transcript_service import transcript_to_plain_text

SECTION_CHARS = 6000   # target size of one chapter's worth of transcript (~6-7 minutes of speech)
MAX_WORKERS = 4        # parallel LLM calls; keep low to stay under Groq rate limits

MAP_PROMPT = """You are summarizing one section of a YouTube video transcript.

Transcript section:
{text}

Respond with JSON only, no markdown:
{{"title": "<chapter title, at most 8 words>", "summary": "<1-2 sentences on what this section covers>"}}"""

REDUCE_PROMPT = """Below are summaries of consecutive sections of one YouTube video, in order.

{outline}

Write a single summary of the whole video in 4-6 sentences, for someone who hasn't \
watched it. Use plain, easy-to-understand language. Do not include timestamps or \
mention "sections" or "chapters".

Summary:"""


def split_into_sections(segments: list[dict], size: int = SECTION_CHARS) -> list[dict]:
    """
    Groups timestamped segments into sections of about `size` characters.
    A leftover shorter than a quarter of `size` is merged into the last section.
    """
    sections = []
    text, start = "", 0.0

    for segment in segments:
        if text and len(text) + len(segment["text"]) > size:
            sections.append({"start_time": start, "text": text.strip()})
            text = ""
        if not text:
            start = segment["start"]
        text += " " + segment["text"]

    if text.strip():
        if sections and len(text) < size // 4:
            sections[-1]["text"] += " " + text.strip()
        else:
            sections.append({"start_time": start, "text": text.strip()})
    return sections


def parse_json(raw: str) -> dict | None:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _summarize_section(section: dict) -> dict | None:
    """MAP step for one section. Retries once; returns None if it still fails."""
    prompt = MAP_PROMPT.format(text=section["text"])
    for attempt in range(2):
        try:
            data = parse_json(generate_completion(prompt, temperature=0.2))
        except RuntimeError:
            data = None
        if data and data.get("title") and data.get("summary"):
            return {
                "start_time": section["start_time"],
                "title": str(data["title"]).strip(),
                "summary": str(data["summary"]).strip(),
            }
        if attempt == 0:
            time.sleep(1)
    return None


def summarize_video(segments: list[dict]) -> dict:
    """
    Returns {"summary": str, "chapters": [{"start_time", "title", "summary"}, ...]}.
    Chapters are empty for short videos. Raises RuntimeError if the LLM keeps failing.
    """
    full_text = transcript_to_plain_text(segments)

    if len(full_text) <= SECTION_CHARS * 1.5:
        return {"summary": summarize_transcript(full_text), "chapters": []}

    sections = split_into_sections(segments)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        chapters = [c for c in pool.map(_summarize_section, sections) if c]  # map keeps order

    if not chapters:
        raise RuntimeError("Could not summarize this video. Please try again.")

    outline = "\n".join(f"{i}. {c['title']}: {c['summary']}" for i, c in enumerate(chapters, start=1))
    return {"summary": generate_completion(REDUCE_PROMPT.format(outline=outline)), "chapters": chapters}