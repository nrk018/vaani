from __future__ import annotations

import math
import threading
from collections import deque

from app.models import AskResponse


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return xs[int(k)]
    return xs[f] * (c - k) + xs[c] * (k - f)


class MetricsRing:
    def __init__(self, size: int = 500) -> None:
        self._lock = threading.Lock()
        self.rag: deque[float] = deque(maxlen=size)
        self.ttft: deque[float] = deque(maxlen=size)
        self.nodes: dict[str, deque[float]] = {}
        self.verdicts: dict[str, int] = {}
        self.traces: deque[dict] = deque(maxlen=40)

    def record(self, resp: AskResponse) -> None:
        with self._lock:
            self.rag.append(resp.rag_ms)
            if resp.ttft_ms is not None:
                self.ttft.append(resp.ttft_ms)
            for t in resp.timings:
                self.nodes.setdefault(t.node, deque(maxlen=500)).append(t.ms)
            self.verdicts[resp.verdict] = self.verdicts.get(resp.verdict, 0) + 1
            self.traces.appendleft(
                {
                    "answer": resp.answer[:180],
                    "verdict": resp.verdict,
                    "rag_ms": round(resp.rag_ms, 2),
                    "ttft_ms": round(resp.ttft_ms or 0, 2),
                    "tools": resp.tools,
                    "citations": [
                        {"title": c.title, "strategy": c.strategy, "score": c.score}
                        for c in resp.citations[:4]
                    ],
                }
            )

    def snapshot(self) -> dict:
        with self._lock:
            def pack(xs: deque[float] | list[float]) -> dict:
                vals = list(xs)
                return {
                    "n": len(vals),
                    "p50": round(percentile(vals, 50), 2),
                    "p70": round(percentile(vals, 70), 2),
                    "p100": round(percentile(vals, 100), 2),
                    "mean": round(sum(vals) / len(vals), 2) if vals else 0.0,
                }

            nodes = {name: pack(dq) for name, dq in self.nodes.items()}
            return {
                "rag": pack(self.rag),
                "ttft": pack(self.ttft),
                "nodes": nodes,
                "verdicts": dict(self.verdicts),
                "traces": list(self.traces),
            }


metrics = MetricsRing()
