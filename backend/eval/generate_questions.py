"""
generate_questions.py
---------------------
Drafts an eval set from real videos so you don't write 40 questions by hand.

For evenly spaced transcript chunks, the LLM writes a question that chunk
answers plus an exact evidence phrase from it. Optionally it also drafts
"unanswerable" questions (same topic, but not answered by the excerpt).

Run from backend/:
    python -m eval.generate_questions URL_OR_ID [URL_OR_ID ...] --per-video 12 --negatives 3

Each argument can be a full YouTube URL or the 11-character video ID. Videos
must have English captions. Videos that fail are skipped.

Results are appended to eval/questions.json.
IMPORTANT: read through the output and delete or fix weak questions. Unanswerable
ones especially -- the video might actually answer them somewhere. A reviewed
eval set of 40 is worth more than an unreviewed one of 200.
"""

import argparse
import json
import re
import time
from pathlib import Path

from eval.metrics import contains_evidence

QUESTIONS_PATH = Path(__file__).parent / "questions.json"
BARE_ID = re.compile(r"^[0-9A-Za-z_-]{11}$")
MIN_CHUNK_CHARS = 200  # skip tiny trailing chunks

ANSWERABLE_PROMPT = """Below is an excerpt from a video transcript.

Excerpt:
{text}

Write ONE question that can be answered using only this excerpt, phrased the way a \
student who has not seen the excerpt would ask it. Do not copy distinctive words from \
the excerpt into the question; paraphrase. Then copy an exact phrase of 2-6 words from \
the excerpt that is essential to the answer.

Respond with JSON only, no markdown:
{{"question": "...", "evidence": "..."}}"""

UNANSWERABLE_PROMPT = """Below is an excerpt from a video transcript.

Excerpt:
{text}

Write ONE question on the same general subject that this excerpt does NOT answer \
(for example a related detail or topic the excerpt never mentions).

Respond with JSON only, no markdown:
{{"question": "..."}}"""


def evenly_spaced(items: list, n: int) -> list:
    """Pick n items spread across the list, so questions cover the whole video."""
    if n >= len(items):
        return items
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def ask_json(prompt: str) -> dict | None:
    from app.services.llm_service import generate_completion

    try:
        raw = generate_completion(prompt, temperature=0.4)
    except RuntimeError as e:
        print(f"    LLM error, skipping: {e}")
        time.sleep(2)
        return None
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def generate_for_video(video_id: str, per_video: int, negatives: int) -> list[dict]:
    from app.services.transcript_service import fetch_transcript
    from app.services.chunking_service import chunk_transcript

    chunks = chunk_transcript(fetch_transcript(video_id))
    candidates = [c for c in chunks if len(c["text"]) >= MIN_CHUNK_CHARS]
    wanted = per_video + negatives
    picked = evenly_spaced(candidates, wanted)
    if len(picked) < wanted:
        print(f"  only {len(picked)} usable chunks (wanted {wanted}): this video is short. "
              "Use a longer video (20+ min) or add more videos for a bigger eval set.")
    # On a short video, shrink the negatives proportionally so answerable questions still come first.
    n_negatives = round(negatives * len(picked) / wanted) if wanted else 0

    entries = []
    for i, chunk in enumerate(picked):
        make_negative = i >= len(picked) - n_negatives  # last picks become negatives  # last picks become negatives
        prompt = (UNANSWERABLE_PROMPT if make_negative else ANSWERABLE_PROMPT).format(text=chunk["text"])
        data = ask_json(prompt)
        time.sleep(0.5)  # stay under Groq rate limits
        if not data or not str(data.get("question", "")).strip():
            continue

        if make_negative:
            entries.append({
                "video_id": video_id,
                "question": data["question"].strip(),
                "evidence": None,
                "answerable": False,
                "source_start_time": chunk["start_time"],
            })
        else:
            evidence = str(data.get("evidence", "")).strip()
            if not contains_evidence(chunk["text"], evidence):
                continue  # LLM didn't copy the phrase exactly -- drop it
            entries.append({
                "video_id": video_id,
                "question": data["question"].strip(),
                "evidence": evidence,
                "answerable": True,
                "source_start_time": chunk["start_time"],
            })
    return entries


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("videos", nargs="+", help="YouTube URLs or 11-character video IDs")
    parser.add_argument("--per-video", type=int, default=12)
    parser.add_argument("--negatives", type=int, default=3)
    args = parser.parse_args(argv)

    existing = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8")) if QUESTIONS_PATH.exists() else []
    seen = {(q["video_id"], q["question"]) for q in existing}

    from fastapi import HTTPException
    from app.utils.youtube_utils import extract_video_id

    for video in args.videos:
        try:
            video_id = video if BARE_ID.match(video) else extract_video_id(video)
            print(f"Generating for {video_id} ...")
            entries = generate_for_video(video_id, args.per_video, args.negatives)
        except HTTPException as e:
            print(f"  skipped '{video}': {e.detail}")
            continue
        new = [e for e in entries if (e["video_id"], e["question"]) not in seen]
        existing.extend(new)
        print(f"  added {len(new)} questions")

    QUESTIONS_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(existing)} total questions to {QUESTIONS_PATH}")


if __name__ == "__main__":
    main()
