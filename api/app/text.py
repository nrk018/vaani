from __future__ import annotations

import re

TOKEN = re.compile(r"[A-Za-z0-9\u0900-\u097F]+")
BM25_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "what",
    "who",
    "when",
    "where",
    "how",
    "why",
    "which",
    "does",
    "do",
    "did",
    "please",
    "tell",
    "me",
    "about",
    "will",
    "would",
    "can",
    "could",
    "next",
    "with",
    "from",
    "that",
    "this",
    "it",
    "ka",
    "ki",
    "ke",
    "hai",
    "kya",
    "hain",
    "क्या",
    "है",
    "की",
    "के",
    "का",
    "में",
    "और",
}


def tokenize(text: str, drop_stop: bool = False) -> list[str]:
    toks = [t.lower() for t in TOKEN.findall(text)]
    if drop_stop:
        toks = [t for t in toks if t not in BM25_STOP and len(t) > 1]
    return toks
