from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from app.config import settings
from app.embeddings import Embedder
from app.text import tokenize


class IndexStore:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.embedder = Embedder()
        self.chunks: list[dict] = []
        self.vectors: np.ndarray = np.zeros((0, 384), dtype=np.float32)
        self.bm25: BM25Okapi | None = None
        self.faiss_index = None
        self.manifest: dict = {}
        self.warm = False

    def load_or_build(self) -> None:
        path = settings.index_path
        dense = path / "dense.npy"
        chunks_path = path / "chunks.jsonl"
        if dense.exists() and chunks_path.exists():
            self._load(path)
        else:
            self._build(path)
        self.warm = True
        self.warm_retriever()

    def warm_retriever(self) -> None:
        """Prime torch / FAISS so the first user query is not a cold load."""
        try:
            for q in ("What is the capital of Goa?", "वाणी क्या है?", "Panaji"):
                vec = self.embedder.encode_query(q)
            if self.faiss_index is not None and vec is not None:
                self.faiss_index.search(vec.astype(np.float32), min(8, max(1, len(self.chunks))))
        except Exception:
            pass

    def _load(self, path: Path) -> None:
        self.vectors = np.load(path / "dense.npy").astype(np.float32)
        self.chunks = [
            json.loads(line)
            for line in chunks_path_lines(path / "chunks.jsonl")
        ]
        tokenized = [tokenize(c["text"]) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized)
        manifest_path = path / "manifest.json"
        if manifest_path.exists():
            self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            self.manifest = {"n_chunks": len(self.chunks), "embedder": self.embedder.name}
        faiss_path = path / "hnsw.faiss"
        if faiss_path.exists():
            try:
                import faiss

                self.faiss_index = faiss.read_index(str(faiss_path))
            except Exception:
                self.faiss_index = None

    def _build(self, path: Path) -> None:
        import sys

        root = settings.root
        sys.path.insert(0, str(root))
        from ingest.build_index import build

        build(path, with_xi=False, xi_rows=0, xi_langs=["hi"])
        self._load(path)

    def info(self) -> dict:
        return {
            "n_chunks": len(self.chunks),
            "dim": int(self.vectors.shape[1]) if self.vectors.size else 0,
            "embedder": self.embedder.name,
            "faiss": self.faiss_index is not None,
            "path": str(settings.index_path),
            **{k: v for k, v in self.manifest.items() if k not in {"embedder"}},
        }


def chunks_path_lines(path: Path) -> list[str]:
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


store = IndexStore()
