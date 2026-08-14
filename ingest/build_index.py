#!/usr/bin/env python3
"""Build hybrid indexes: dense matrix + BM25 over multi-strategy chunks."""

from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from ingest.chunk import chunk_passage  # noqa: E402
from ingest.sample import load_all_local, sample_msmarco_xi  # noqa: E402


def _embedder():
    from app.embeddings import Embedder

    return Embedder()


def build(index_dir: Path, with_xi: bool, xi_rows: int, xi_langs: list[str]) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    passages = load_all_local()
    if with_xi:
        print(f"sampling MSMARCO-XI langs={xi_langs} max_rows={xi_rows}", flush=True)
        passages.extend(sample_msmarco_xi(tuple(xi_langs), max_rows=xi_rows))

    chunks = []
    for p in passages:
        chunks.extend(chunk_passage(p))

    # Dedup identical (strategy, text) pairs
    uniq = []
    seen: set[str] = set()
    for c in chunks:
        key = f"{c.strategy}:{c.text}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    chunks = uniq
    print(f"passages={len(passages)} chunks={len(chunks)}")

    embedder = _embedder()
    texts = [c.text for c in chunks]
    vectors = embedder.encode(texts, batch_size=64)
    vectors = vectors.astype(np.float32)

    meta = [c.to_dict() for c in chunks]
    (index_dir / "chunks.jsonl").write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in meta) + "\n",
        encoding="utf-8",
    )
    np.save(index_dir / "dense.npy", vectors)

    from app.text import tokenize
    from rank_bm25 import BM25Okapi

    tokenized = [tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized)
    with (index_dir / "bm25.pkl").open("wb") as fh:
        pickle.dump({"tokenized": tokenized}, fh)

    # Optional FAISS HNSW for larger corpora
    try:
        import faiss

        d = vectors.shape[1]
        index = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = 80
        index.hnsw.efSearch = 64
        index.add(vectors)
        faiss.write_index(index, str(index_dir / "hnsw.faiss"))
        print("wrote hnsw.faiss")
    except Exception as exc:  # noqa: BLE001
        print(f"faiss skipped: {exc}")

    manifest = {
        "n_passages": len(passages),
        "n_chunks": len(chunks),
        "dim": int(vectors.shape[1]),
        "strategies": sorted({c.strategy for c in chunks}),
        "langs": sorted({c.lang for c in chunks}),
        "sources": sorted({c.source for c in chunks}),
        "embedder": embedder.name,
    }
    (index_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-dir", type=Path, default=ROOT / "data" / "index")
    parser.add_argument("--with-xi", action="store_true")
    parser.add_argument("--xi-rows", type=int, default=8000)
    parser.add_argument("--xi-langs", default="hi,mr")
    args = parser.parse_args()
    langs = [x.strip() for x in args.xi_langs.split(",") if x.strip()]
    build(args.index_dir, args.with_xi, args.xi_rows, langs)


if __name__ == "__main__":
    main()
