#!/usr/bin/env python3
"""Latency + guardrail bench. Writes eval/results.json with P50/P70/P100."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT))

from app.harness import run_ask  # noqa: E402
from app.index_store import store  # noqa: E402
from app.metrics import percentile  # noqa: E402

EXPAND = [
    "Who patented the telephone?",
    "What is a vector database?",
    "What is HNSW used for?",
    "When does water boil at sea level?",
    "What is a hallucination in language models?",
    "Which city is the largest in Goa?",
    "What is Fontainhas?",
    "What hashtag must HH Goa videos use?",
    "When is the HH Goa 2026 deadline?",
    "Must every team member post the videos?",
    "Which STT provider does Vaani use?",
    "Does MSMARCO-XI include Konkani?",
    "Why does Vaani index Marathi?",
    "What are the four chunking strategies?",
    "What is the RAG latency target in milliseconds?",
    "Name two UNESCO sites related to Old Goa",
    "What districts is Goa divided into?",
    "What is cashew feni's GI status?",
    "How long did Portuguese rule last in Goa?",
    "What does the Vaani guardrail do when evidence is weak?",
    "Explain parent-child chunking",
    "What is MS MARCO?",
    "What constant denotes the speed of light?",
    "Where is New Delhi?",
    "What river is Panaji on?",
    "What is mando music?",
    "Which beaches are named in the Goa pack?",
    "What visual palette does Vaani use?",
    "What does #RAGInGoa refer to?",
    "Is chunking done at query time?",
    "What is the scored latency budget?",
    "How does hybrid retrieval work in Vaani?",
    "What model family is used for generation?",
    "What happens on an off-topic sports question?",
    "Describe the Manhattan Project's immediate impact in one line",
    "What oxygen byproduct comes from photosynthesis?",
    "Who is buried at the Basilica of Bom Jesus?",
    "What scripts is Konkani written in?",
    "How do you wish a good day in Konkani?",
    "What year did Goa become a state?",
    "भारत में संसद कहाँ है?",
    "गोवा किस सागर से लगता है?",
    "फेनी किससे बनती है?",
    "मैनहटन परियोजना का प्रभाव क्या था?",
    "प्रकाश की चाल कितनी है?",
    "आरएजी क्यों इस्तेमाल होता है?",
    "देव बोरें कोरूं का मतलब?",
    "पणजी कहाँ है?",
    "What is the capital of Portugal's former Indian colony Goa?",
    "Tell me a grounded fact about the Arabian Sea",
    "How do you fuse BM25 with dense vectors?",
    "What is the boiling point of water in Fahrenheit?",
    "Did Bell and Gray file on the same day?",
    "What is e5 used for in this project?",
    "Why keep FAISS in memory?",
    "What is a proposition chunk?",
    "What is semantic breakpoint splitting?",
    "Name the two Goa districts",
    "What is laterite?",
    "Where are Mangeshi and Shantadurga?",
    "What is Operation Vijay also known for?",
    "Can Vaani answer medical dosages not in the index?",
    "What is the live working link requirement?",
    "How long is the process video?",
    "Which platforms must videos be posted to?",
    "What speech-to-text latency does Scribe advertise?",
    "Why is Pinecone avoided on the hot path?",
]


def load_queries() -> list[dict]:
    golden = json.loads((ROOT / "eval" / "golden_queries.json").read_text(encoding="utf-8"))
    extra = [{"id": f"x{i}", "query": q, "expect": "grounded"} for i, q in enumerate(EXPAND)]
    extra[-1]["expect"] = "refused"
    extra[-2]["expect"] = "grounded"
    return golden + extra


def pack(values: list[float]) -> dict:
    return {
        "n": len(values),
        "p50": round(percentile(values, 50), 2),
        "p70": round(percentile(values, 70), 2),
        "p100": round(percentile(values, 100), 2),
        "mean": round(sum(values) / len(values), 2) if values else 0.0,
    }


def main() -> None:
    store.load_or_build()
    queries = load_queries()
    print(f"bench n={len(queries)}")
    rows = []
    t0 = time.perf_counter()
    for q in queries:
        resp = run_ask(q["query"])
        row = {
            "id": q["id"],
            "query": q["query"],
            "expect": q.get("expect"),
            "verdict": resp.verdict,
            "rag_ms": round(resp.rag_ms, 2),
            "ttft_ms": round(resp.ttft_ms or 0, 2),
            "tools": resp.tools,
            "answer": resp.answer,
            "n_citations": len(resp.citations),
            "timings": {t.node: round(t.ms, 2) for t in resp.timings},
        }
        rows.append(row)
        print(f"{q['id']:6} {resp.rag_ms:7.1f}ms {resp.verdict:15} {q['query'][:48]}")

    rag = [r["rag_ms"] for r in rows]
    ttft = [r["ttft_ms"] for r in rows]
    by_node: dict[str, list[float]] = {}
    for r in rows:
        for k, v in r["timings"].items():
            by_node.setdefault(k, []).append(v)

    under = sum(1 for x in rag if x < 200)
    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n": len(rows),
        "under_200ms": under,
        "under_200ms_pct": round(100 * under / len(rows), 1) if rows else 0,
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "index": store.info(),
        "latency": {
            "rag": pack(rag),
            "ttft": pack(ttft),
            "nodes": {k: pack(v) for k, v in by_node.items()},
        },
        "verdicts": {
            v: sum(1 for r in rows if r["verdict"] == v)
            for v in ("GROUNDED", "LOW_CONFIDENCE", "REFUSED")
        },
        "rows": rows,
    }
    out = ROOT / "eval" / "results.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["latency"], indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
