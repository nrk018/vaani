"""Multilingual embedder with a hashed n-gram fallback.

Query-time encode must match index-time encode. The hashed fallback lets
the product boot without downloading a transformer; ingest with
sentence-transformers when available for real Indic cross-lingual recall.
"""

from __future__ import annotations

import hashlib
import os
import threading

# Torch + faiss-cpu both ship libomp; on macOS that double-load segfaults.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import numpy as np

DIM = 384


def _normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-8, None)
    return (mat / norms).astype(np.float32)


def hashed_ngrams(texts: list[str], dim: int = DIM) -> np.ndarray:
    mat = np.zeros((len(texts), dim), dtype=np.float32)
    for i, text in enumerate(texts):
        t = f"query: {text.lower()}"
        chars = t.replace(" ", "")
        for n in (3, 4):
            for j in range(max(0, len(chars) - n + 1)):
                gram = chars[j : j + n]
                h = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
                idx = int.from_bytes(h[:4], "little") % dim
                sign = 1.0 if h[4] % 2 == 0 else -1.0
                mat[i, idx] += sign
    return _normalize(mat)


class Embedder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model = None
        self.name = "hash-ngram-384"
        self._try_load()

    def _try_load(self) -> None:
        if os.environ.get("VAANI_HASH_EMBEDDINGS") == "1":
            return
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                "intfloat/multilingual-e5-small",
                device="cpu",
            )
            self._model = model
            self.name = "intfloat/multilingual-e5-small"
        except Exception:
            self._model = None
            self.name = "hash-ngram-384"

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.zeros((0, DIM), dtype=np.float32)
        if self._model is None:
            return hashed_ngrams(texts)
        prefixed = [f"query: {t}" if i == 0 else f"passage: {t}" for i, t in enumerate(texts)]
        # e5 convention: queries vs passages. For a mixed list we treat all as passages
        # except we cannot know. Index-time we use passage:, query-time query:.
        prefixed = [f"passage: {t}" for t in texts]
        with self._lock:
            vecs = self._model.encode(
                prefixed,
                batch_size=min(batch_size, 16),
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
                device="cpu",
            )
        return vecs.astype(np.float32)

    def encode_query(self, text: str) -> np.ndarray:
        if self._model is None:
            return hashed_ngrams([text])
        with self._lock:
            vec = self._model.encode(
                [f"query: {text}"],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
                device="cpu",
            )
        return vec.astype(np.float32)
