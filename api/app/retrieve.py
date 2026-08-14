from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from app.config import settings
from app.index_store import store
from app.models import Citation
from app.text import tokenize

DEVANAGARI = re.compile(r"[\u0900-\u097F]")
LATIN = re.compile(r"[A-Za-z]")

_pool = ThreadPoolExecutor(max_workers=2)


def detect_script(query: str) -> str:
    if DEVANAGARI.search(query):
        return "deva"
    return "latin"


def route_weights(query: str) -> dict[str, float]:
    q = query.lower()
    n = len(query.split())
    weights = {
        "native": 1.0,
        "parent_child": 1.0,
        "semantic": 1.0,
        "proposition": 1.0,
    }
    if n <= 8 or any(ch.isdigit() for ch in query):
        weights["proposition"] = 1.35
    if n >= 14:
        weights["parent_child"] = 1.2
        weights["semantic"] = 1.15
    if "goa" in q or "konkani" in q or "vaani" in q or "hh " in q:
        weights["native"] = 1.2
    return weights


def lang_boost(chunk: dict, script: str) -> float:
    lang = chunk.get("lang", "en")
    source = chunk.get("source", "")
    if source == "goa":
        return 1.12
    if script == "deva" and lang in {"hi", "mr"}:
        return 1.15
    if script == "latin" and lang == "en":
        return 1.05
    return 1.0


def rrf_fuse(
    dense_ranks: list[tuple[int, float]],
    bm25_ranks: list[tuple[int, float]],
    k: int,
) -> list[tuple[int, float, float, float]]:
    scores: dict[int, float] = {}
    dense_map = dict(dense_ranks)
    bm25_map = dict(bm25_ranks)
    for rank, (idx, _) in enumerate(dense_ranks, start=1):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank)
    for rank, (idx, _) in enumerate(bm25_ranks, start=1):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank)
    fused = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    out: list[tuple[int, float, float, float]] = []
    for idx, fused_score in fused:
        out.append((idx, fused_score, dense_map.get(idx, 0.0), bm25_map.get(idx, 0.0)))
    return out


def dense_search(qvec: np.ndarray, k: int) -> list[tuple[int, float]]:
    if store.vectors.shape[0] == 0:
        return []
    if store.faiss_index is not None:
        scores, ids = store.faiss_index.search(qvec.astype(np.float32), k)
        return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]
    hits = store.vectors @ qvec.reshape(-1)
    top = np.argpartition(-hits, min(k, len(hits) - 1))[:k]
    top = top[np.argsort(-hits[top])]
    return [(int(i), float(hits[i])) for i in top]


def bm25_search(query: str, k: int) -> list[tuple[int, float]]:
    if store.bm25 is None:
        return []
    tokens = tokenize(query, drop_stop=True)
    if not tokens:
        return []
    scores = np.array(store.bm25.get_scores(tokens), dtype=np.float32)
    if scores.size == 0:
        return []
    top = np.argpartition(-scores, min(k, len(scores) - 1))[:k]
    top = top[np.argsort(-scores[top])]
    return [(int(i), float(scores[i])) for i in top]


def retrieve(query: str) -> tuple[list[Citation], dict[str, float]]:
    timings: dict[str, float] = {}
    script = detect_script(query)
    weights = route_weights(query)

    t0 = time.perf_counter()
    index_embedder = str(store.manifest.get("embedder") or store.embedder.name)
    dense_compatible = (
        store.embedder.name == index_embedder
        or (
            store.embedder.name.startswith("hash")
            and index_embedder.startswith("hash")
        )
    )
    qvec = store.embedder.encode_query(query) if dense_compatible else np.zeros((1, 384), dtype=np.float32)
    timings["embed"] = (time.perf_counter() - t0) * 1000

    def _dense():
        t = time.perf_counter()
        if not dense_compatible:
            return [], (time.perf_counter() - t) * 1000
        hits = dense_search(qvec, settings.dense_k)
        return hits, (time.perf_counter() - t) * 1000

    def _bm25():
        t = time.perf_counter()
        hits = bm25_search(query, settings.bm25_k)
        return hits, (time.perf_counter() - t) * 1000

    dense_f = _pool.submit(_dense)
    bm25_f = _pool.submit(_bm25)
    dense_hits, timings["dense"] = dense_f.result()
    bm25_hits, timings["bm25"] = bm25_f.result()

    t1 = time.perf_counter()
    fused = rrf_fuse(dense_hits, bm25_hits, settings.rrf_k)

    weighted: list[tuple[int, float, float, float]] = []
    for idx, fused_s, d_s, b_s in fused:
        chunk = store.chunks[idx]
        w = weights.get(chunk.get("strategy", "native"), 1.0) * lang_boost(chunk, script)
        weighted.append((idx, fused_s * w, d_s, b_s))
    weighted.sort(key=lambda x: x[1], reverse=True)

    # Expand children → unique parents for generation, keep best child score
    citations: list[Citation] = []
    seen_parents: set[str] = set()
    for idx, fused_s, d_s, b_s in weighted:
        chunk = store.chunks[idx]
        parent_id = chunk.get("parent_id") or chunk["id"]
        if parent_id in seen_parents:
            continue
        seen_parents.add(parent_id)
        text = chunk.get("parent_text") or chunk["text"]
        bm25_n = float(np.tanh(b_s / 4.0)) if b_s else 0.0
        if store.embedder.name.startswith("hash"):
            combined = max(bm25_n, float(fused_s) * 0.35)
        else:
            combined = max(float(d_s), bm25_n, float(fused_s))
        citations.append(
            Citation(
                id=chunk["id"],
                title=chunk.get("title") or parent_id,
                text=text[:1200],
                lang=chunk.get("lang", "en"),
                source=chunk.get("source", ""),
                strategy=chunk.get("strategy", "native"),
                score=round(combined, 4),
                parent_id=parent_id,
            )
        )
        if len(citations) >= settings.fuse_k:
            break
    timings["fuse"] = (time.perf_counter() - t1) * 1000
    timings["retrieve"] = timings["dense"] + timings["bm25"] + timings["fuse"]
    return citations, timings
