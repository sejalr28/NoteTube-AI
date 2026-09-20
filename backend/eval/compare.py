"""
compare.py
----------
Prints every saved eval run as a markdown table -- paste it into your README.

Run from backend/:
    python -m eval.compare
"""

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def pct(x) -> str:
    return "-" if x is None else f"{x * 100:.1f}%"


def main() -> None:
    reports = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(RESULTS_DIR.glob("*.json"))]
    if not reports:
        raise SystemExit("No results yet. Run: python -m eval.run_eval --label baseline")

    print("| Run | Hybrid | Rerank | Chunk | hit@1 | hit@4 | hit@10 | MRR@10 | Faithful |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in reports:
        c, m = r["config"], r["retrieval"]
        faithful = (r.get("answers") or {}).get("faithfulness")
        print(
            f"| {r['label']} | {'yes' if c.get('use_hybrid') else 'no'} | "
            f"{'yes' if c.get('use_reranker') else 'no'} | {c['chunk_size']} | "
            f"{pct(m['hit@1'])} | {pct(m['hit@4'])} | {pct(m['hit@10'])} | "
            f"{m['mrr@10']:.3f} | {pct(faithful)} |"
        )


if __name__ == "__main__":
    main()
