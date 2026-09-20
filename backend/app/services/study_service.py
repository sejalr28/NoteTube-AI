"""
study_service.py
----------------
Generates study material from a video: multiple-choice quiz questions and flashcards.

Each item is generated from ONE short transcript section (~2.5 minutes of speech), picked
evenly across the video. That keeps every item grounded in real content and gives it an
exact timestamp, so the student can jump back to review the part they got wrong.
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor

from app.services.llm_service import generate_completion
from app.services.summary_service import MAX_WORKERS, parse_json, split_into_sections

STUDY_SECTION_CHARS = 2500

QUIZ_PROMPT = """Below is an excerpt from a YouTube video transcript.

Excerpt:
{text}

Write ONE multiple-choice question that tests understanding of an important idea in this \
excerpt, not trivia. Give exactly 4 options: one correct answer and three plausible wrong \
answers of similar length. The question must make sense on its own, so never mention \
"the excerpt" or "the speaker".

Respond with JSON only, no markdown. "answer_index" is the position (0-3) of the correct option:
{{"question": "...", "options": ["...", "...", "...", "..."], "answer_index": 0, "explanation": "<one sentence on why that answer is correct>"}}"""

FLASHCARD_PROMPT = """Below is an excerpt from a YouTube video transcript.

Excerpt:
{text}

Write ONE flashcard for studying the most important idea in this excerpt. The front is a \
short question or term. The back is a clear answer in 1-2 sentences. It must make sense on \
its own, so never mention "the excerpt" or "the speaker".

Respond with JSON only, no markdown:
{{"front": "...", "back": "..."}}"""


def evenly_spaced(items: list, n: int) -> list:
    """Picks n items spread across the list, so material covers the whole video."""
    if n >= len(items):
        return items
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def _build_question(data: dict, start_time: float) -> dict | None:
    """Validates one generated question. Returns None if it is malformed."""
    question = str(data.get("question", "")).strip()
    raw_options = data.get("options")
    if not question or not isinstance(raw_options, list):
        return None
    options = [str(o).strip() for o in raw_options]
    try:
        answer_index = int(data.get("answer_index"))
    except (TypeError, ValueError):
        return None
    if len(options) != 4 or "" in options or len(set(options)) != 4 or not 0 <= answer_index < 4:
        return None

    # Models like to put the right answer first, so shuffle the options.
    correct = options[answer_index]
    random.shuffle(options)
    return {
        "question": question,
        "options": options,
        "answer_index": options.index(correct),
        "explanation": str(data.get("explanation", "")).strip(),
        "start_time": start_time,
    }


def _build_card(data: dict, start_time: float) -> dict | None:
    front = str(data.get("front", "")).strip()
    back = str(data.get("back", "")).strip()
    if not front or not back:
        return None
    return {"front": front, "back": back, "start_time": start_time}


def _generate_item(section: dict, prompt_template: str, build) -> dict | None:
    """Asks the LLM for one item from a section. Retries once; returns None if it still fails."""
    prompt = prompt_template.format(text=section["text"])
    for attempt in range(2):
        try:
            data = parse_json(generate_completion(prompt, temperature=0.5))
        except RuntimeError:
            data = None
        item = build(data, section["start_time"]) if data else None
        if item:
            return item
        if attempt == 0:
            time.sleep(1)
    return None


def _generate(segments: list[dict], count: int, prompt_template: str, build, dedupe_key: str) -> list[dict]:
    sections = evenly_spaced(split_into_sections(segments, size=STUDY_SECTION_CHARS), count)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(lambda s: _generate_item(s, prompt_template, build), sections))

    items, seen = [], set()
    for item in results:  # map keeps order, so items follow the video
        key = item[dedupe_key].lower() if item else None
        if item and key not in seen:
            seen.add(key)
            items.append(item)

    if not items:
        raise RuntimeError("Could not generate study material. Please try again.")
    return items


def generate_quiz(segments: list[dict], count: int) -> list[dict]:
    return _generate(segments, count, QUIZ_PROMPT, _build_question, "question")


def generate_flashcards(segments: list[dict], count: int) -> list[dict]:
    return _generate(segments, count, FLASHCARD_PROMPT, _build_card, "front")