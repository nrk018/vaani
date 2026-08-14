"""Four chunking strategies over the same corpus.

1. native     — keep source passages as retrieval units
2. parent_child — short overlapping children, full parent for generation
3. semantic   — sentence breakpoint splits with overlap
4. proposition — atomic claim slices for factoid queries
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Iterable, Literal

Strategy = Literal["native", "parent_child", "semantic", "proposition"]

SENT_SPLIT = re.compile(r"(?<=[.!?।؟])\s+")
WORD_RE = re.compile(r"\S+")


@dataclass
class Chunk:
    id: str
    text: str
    parent_id: str
    parent_text: str
    lang: str
    source: str
    strategy: Strategy
    query_type: str
    title: str
    token_estimate: int

    def to_dict(self) -> dict:
        return asdict(self)


def _tokens(text: str) -> list[str]:
    return WORD_RE.findall(text)


def _n_tokens(text: str) -> int:
    return len(_tokens(text))


def _cid(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENT_SPLIT.split(text.strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def windows(words: list[str], size: int, overlap: int) -> list[list[str]]:
    if not words:
        return []
    if len(words) <= size:
        return [words]
    step = max(1, size - overlap)
    out: list[list[str]] = []
    i = 0
    while i < len(words):
        out.append(words[i : i + size])
        if i + size >= len(words):
            break
        i += step
    return out


def native_chunks(passage: dict) -> list[Chunk]:
    text = passage["text"].strip()
    pid = passage["id"]
    return [
        Chunk(
            id=_cid("native", pid),
            text=text,
            parent_id=pid,
            parent_text=text,
            lang=passage.get("lang", "en"),
            source=passage.get("source", "seed"),
            strategy="native",
            query_type=passage.get("query_type", "DESCRIPTION"),
            title=passage.get("title", ""),
            token_estimate=_n_tokens(text),
        )
    ]


def parent_child_chunks(
    passage: dict, child_size: int = 100, overlap: int = 20
) -> list[Chunk]:
    text = passage["text"].strip()
    pid = passage["id"]
    words = _tokens(text)
    out: list[Chunk] = []
    for i, win in enumerate(windows(words, child_size, overlap)):
        child = " ".join(win)
        out.append(
            Chunk(
                id=_cid("pc", pid, str(i)),
                text=child,
                parent_id=pid,
                parent_text=text,
                lang=passage.get("lang", "en"),
                source=passage.get("source", "seed"),
                strategy="parent_child",
                query_type=passage.get("query_type", "DESCRIPTION"),
                title=passage.get("title", ""),
                token_estimate=len(win),
            )
        )
    return out or native_chunks(passage)


def semantic_chunks(passage: dict, group: int = 3, overlap_sents: int = 1) -> list[Chunk]:
    """Breakpoint grouping: pack ~3 sentences, overlap 1 sentence.

    A true embedding-cosine splitter runs at index-build time when an embedder
    is available; this function is the deterministic fallback and is already
    more structured than a single fixed window.
    """
    text = passage["text"].strip()
    pid = passage["id"]
    sents = sentences(text)
    if len(sents) <= 2:
        return native_chunks(passage)
    out: list[Chunk] = []
    step = max(1, group - overlap_sents)
    i = 0
    n = 0
    while i < len(sents):
        pack = sents[i : i + group]
        child = " ".join(pack)
        out.append(
            Chunk(
                id=_cid("sem", pid, str(n)),
                text=child,
                parent_id=pid,
                parent_text=text,
                lang=passage.get("lang", "en"),
                source=passage.get("source", "seed"),
                strategy="semantic",
                query_type=passage.get("query_type", "DESCRIPTION"),
                title=passage.get("title", ""),
                token_estimate=_n_tokens(child),
            )
        )
        n += 1
        if i + group >= len(sents):
            break
        i += step
    return out


def proposition_chunks(passage: dict) -> list[Chunk]:
    """Atomic claims — one (short) sentence per chunk, skip tiny fragments."""
    text = passage["text"].strip()
    pid = passage["id"]
    sents = sentences(text)
    out: list[Chunk] = []
    for i, sent in enumerate(sents):
        n = _n_tokens(sent)
        if n < 4:
            continue
        out.append(
            Chunk(
                id=_cid("prop", pid, str(i)),
                text=sent,
                parent_id=pid,
                parent_text=text,
                lang=passage.get("lang", "en"),
                source=passage.get("source", "seed"),
                strategy="proposition",
                query_type=passage.get("query_type", "DESCRIPTION"),
                title=passage.get("title", ""),
                token_estimate=n,
            )
        )
    return out or native_chunks(passage)


STRATEGIES = {
    "native": native_chunks,
    "parent_child": parent_child_chunks,
    "semantic": semantic_chunks,
    "proposition": proposition_chunks,
}


def chunk_passage(
    passage: dict, strategies: Iterable[Strategy] | None = None
) -> list[Chunk]:
    selected = list(strategies) if strategies else list(STRATEGIES)
    chunks: list[Chunk] = []
    for name in selected:
        chunks.extend(STRATEGIES[name](passage))
    return chunks
