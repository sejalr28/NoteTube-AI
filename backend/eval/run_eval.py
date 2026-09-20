"""
run_eval.py
-----------
Scores the RAG pipeline on eval/questions.json and saves a results file.

Run from backend/:
    python -m eval.run_eval --label baseline              # retrieval only (free, fast)
    python -m eval.run_eval --label baseline --judge      # + answer faithfulness (LLM calls)
    python -m eval.run_eval --label hybrid --reindex      # after changing chunking/embeddings

Retrieval: hit@1/4/10 and MRR@10, plus a MIN_SIMILARITY sweep showing how many
answerable questions are kept vs unanswerable ones rejected at each threshold.
Faithfulness (--judge): an LLM checks each answer is supported by its sources.
Tip: pass --judge-model with a stronger model than the one answering, so the
model isn't grading its own work.
"""

import argparse
import json
import os
import time
from pathlib import Path

from eval.metrics import contains_evidence, retrieval_metrics, threshold_sweep

EVAL_DIR = Path(__file__).parent
RESULTS_DIR = EVAL_DIR / "results"
K_MAX = 10
THRESHOLDS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]

FAITHFUL_PROMPT = """You are checking an answer against transcript excerpts.

Excerpts:
{sources}

Answer:
{answer}

Is every claim in the answer supported by the excerpts? \
Reply with exactly one word: SUPPORTED or UNSUPPORTED."""

ABSTAIN_PROMPT = """Answer:
{answer}

Does this answer say that the information is not available or not covered \
(instead of giving a substantive answer)? Reply with exactly one word: YES or NO."""


def pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def ensure_indexed(video_id: str, reindex: bool) -> None:
    from app.config import settings
    from app.services.transcript_service import fetch_transcript
    from app.services.chunking_service import chunk_transcript
    from app.services.vectorstore_service import store_chunks

    index_file = os.path.join(settings.FAISS_INDEX_DIR, f"{video_id}.index")
    if os.path.exists(index_file) and not reindex:
        return
    print(f"  indexing {video_id} ...")
    store_chunks(video_id, chunk_transcript(fetch_transcript(video_id)))


def evaluate_retrieval(questions: list[dict]) -> list[dict]:
    from app.services.retrieval_service import retrieve_chunks

    rows = []
    for q in questions:
        retrieved = retrieve_chunks(q["video_id"], q["question"], top_k=K_MAX)
        rank = None
        if q["answerable"]:
            for i, chunk in enumerate(retrieved, start=1):
                if contains_evidence(chunk["text"], q["evidence"]):
                    rank = i
                    break
        rows.append({**q, "rank": rank, "top_score": max((c["score"] for c in retrieved), default=0.0)})
    return rows


def judge(prompt: str, model: str | None) -> str:
    from app.services.llm_service import generate_completion

    time.sleep(0.5)  # stay under Groq rate limits
    return generate_completion(prompt, temperature=0.0, model=model).strip().upper()


def evaluate_answers(rows: list[dict], judge_model: str | None) -> dict:
    from app.services.rag_service import answer_question

    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]

    for n, r in enumerate(rows, start=1):
        if n % 10 == 0:
            print(f"  ... {n}/{len(rows)} done")
        try:
            result = answer_question(r["video_id"], r["question"])
            r["answer"] = result["answer"]
            r["abstained"] = not result["sources"]
            if r["answerable"] and not r["abstained"]:
                sources = "\n\n".join(s["text"] for s in result["sources"])
                verdict = judge(FAITHFUL_PROMPT.format(sources=sources, answer=r["answer"]), judge_model)
                r["faithful"] = verdict.startswith("SUPPORTED")
            elif not r["answerable"]:
                r["abstain_ok"] = r["abstained"] or judge(
                    ABSTAIN_PROMPT.format(answer=r["answer"]), judge_model
                ).startswith("YES")
        except RuntimeError as e:
            print(f"  LLM error on '{r['question'][:50]}...': {e}")
            r["error"] = str(e)

    answered = [r for r in answerable if "faithful" in r]
    return {
        "answer_rate": len(answered) / len(answerable) if answerable else None,
        "faithfulness": sum(r["faithful"] for r in answered) / len(answered) if answered else None,
        "correct_abstention": (
            sum(r.get("abstain_ok", False) for r in unanswerable) / len(unanswerable)
            if unanswerable else None
        ),
    }


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--questions", default=str(EVAL_DIR / "questions.json"))
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--reindex", action="store_true")
    args = parser.parse_args(argv)

    from app.config import settings

    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    if not questions:
        raise SystemExit("questions.json is empty. Run: python -m eval.generate_questions VIDEO_ID")
    for q in questions:
        q.setdefault("answerable", True)

    print(f"Loaded {len(questions)} questions")
    for video_id in sorted({q["video_id"] for q in questions}):
        ensure_indexed(video_id, args.reindex)

    rows = evaluate_retrieval(questions)
    metrics = retrieval_metrics(rows)
    sweep = threshold_sweep(rows, THRESHOLDS)

    print("\n== Retrieval ==")
    for name, value in metrics.items():
        print(f"  {name:<8} {pct(value) if name != 'mrr@10' else f'{value:.3f}'}")

    print(f"\n== MIN_SIMILARITY sweep (current: {settings.MIN_SIMILARITY}) ==")
    print("  threshold  answerable kept  unanswerable rejected")
    for s in sweep:
        print(f"  {s['threshold']:<9.2f}  {pct(s['answerable_kept']):<15}  {pct(s['unanswerable_rejected'])}")
    scored = [s for s in sweep if s["answerable_kept"] is not None and s["unanswerable_rejected"] is not None]
    if scored:
        best = max(scored, key=lambda s: s["answerable_kept"] + s["unanswerable_rejected"])
        print(f"  best balanced threshold: {best['threshold']:.2f}")

    misses = [r for r in rows if r["answerable"] and r["rank"] is None]
    if misses:
        print(f"\n== {len(misses)} retrieval misses (not in top {K_MAX}) ==")
        for r in misses[:5]:
            print(f"  - {r['question']}  [evidence: {r['evidence']}]")

    faithfulness = None
    if args.judge:
        print("\n== Answer quality (LLM judge) ==")
        faithfulness = evaluate_answers(rows, args.judge_model)
        print(f"  answered (answerable): {pct(faithfulness['answer_rate'])}")
        print(f"  faithfulness:          {pct(faithfulness['faithfulness'])}")
        print(f"  correct abstention:    {pct(faithfulness['correct_abstention'])}")

    report = {
        "label": args.label,
        "config": {
            "embedding_model": settings.EMBEDDING_MODEL,
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "top_k": settings.TOP_K_RESULTS,
            "use_hybrid": settings.USE_HYBRID,
            "use_reranker": settings.USE_RERANKER,
            "candidate_pool": settings.CANDIDATE_POOL,
            "reranker_model": settings.RERANKER_MODEL,
            "min_similarity": settings.MIN_SIMILARITY,
            "llm_model": settings.LLM_MODEL,
            "judge_model": args.judge_model or settings.LLM_MODEL,
        },
        "n_answerable": sum(r["answerable"] for r in rows),
        "n_unanswerable": sum(not r["answerable"] for r in rows),
        "retrieval": metrics,
        "threshold_sweep": sweep,
        "answers": faithfulness,
        "rows": rows,
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{args.label}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {out}")
    return report


if __name__ == "__main__":
    main()