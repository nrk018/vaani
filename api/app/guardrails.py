from __future__ import annotations

import re

from app.models import Citation, GuardVerdict
from app.text import BM25_STOP, tokenize

JAILBREAK = re.compile(
    r"(ignore (previous|all) instructions|you are now|system prompt|"
    r"dan mode|jailbreak|override your rules|pretend you have no)",
    re.I,
)
ABUSE = re.compile(
    r"(kill yourself|make a bomb|making a bomb|build a weapon|child porn|"
    r"private phone number|credit card number)",
    re.I,
)
GREET = re.compile(
    r"^(hi|hello|hey|yo|namaste|namaskar|dev borem korum)([!.\s]|$)",
    re.I,
)
SCRIBE_JUNK = re.compile(
    r"you('re| are) not even in a call|tap to start voice",
    re.I,
)


def inbound(query: str) -> tuple[bool, str | None]:
    q = query.strip()
    if len(q) < 2:
        return False, "empty"
    if JAILBREAK.search(q):
        return False, "jailbreak"
    if ABUSE.search(q):
        return False, "unsafe"
    if SCRIBE_JUNK.search(q):
        return False, "empty"
    return True, None


def is_greeting(query: str) -> bool:
    q = query.strip()
    if len(q.split()) > 6:
        return False
    return bool(GREET.search(q))


def token_set(text: str) -> set[str]:
    return {t for t in tokenize(text, drop_stop=True) if t not in BM25_STOP and len(t) > 2}


def query_coverage(query: str, citations: list[Citation]) -> float:
    q = token_set(query)
    if not q or not citations:
        return 0.0
    ctx = token_set(" ".join(f"{c.title} {c.text}" for c in citations))
    overlap = len(q & ctx)
    if overlap == 0:
        return 0.0
    # XI titles are the original MS MARCO query. If the user asked that
    # question (or close), treat it as in-corpus even when the body paraphrases.
    titles = token_set(" ".join(c.title for c in citations[:4]))
    if titles and len(q & titles) / len(q) >= 0.45:
        return 1.0
    # Short questions: one real content word in the passages is enough.
    if len(q) <= 6:
        return max(overlap / len(q), 0.5)
    return overlap / len(q)


def retrieval_floor(
    citations: list[Citation], min_dense: float, query: str = ""
) -> tuple[bool, str | None]:
    if not citations:
        return False, "no_evidence"
    cov = query_coverage(query, citations) if query else 1.0
    # e5 cosines sit high even for weak matches. Lexical overlap is the off-topic gate.
    if cov >= 0.12:
        return True, None
    if citations[0].score < min_dense:
        return False, "low_retrieval"
    return False, "off_topic"


def faithfulness(answer: str, citations: list[Citation]) -> float:
    if not answer or not citations:
        return 0.0
    ctx = token_set(" ".join(c.text for c in citations))
    ans = token_set(answer)
    if not ans:
        return 0.0
    return len(ans & ctx) / len(ans)


def outbound(
    answer: str, citations: list[Citation], already_refused: bool
) -> tuple[GuardVerdict, float]:
    if already_refused:
        return "REFUSED", 0.0
    overlap = faithfulness(answer, citations)
    # Retrieval already approved the passages. Keep paraphrases; don't wipe the answer.
    if overlap < 0.12:
        return "LOW_CONFIDENCE", overlap
    return "GROUNDED", overlap


def refuse_text(language: str, reason: str) -> str:
    hi = language.lower().startswith("hi") or language.lower().startswith("mr")
    if reason in {"jailbreak", "unsafe"}:
        return (
            "मैं यह अनुरोध पूरा नहीं कर सकती।"
            if hi
            else "I will not take that request."
        )
    if reason == "empty":
        return (
            "मैंने स्पष्ट प्रश्न नहीं सुना। गोवा, वाणी, या हैकर हाउस के बारे में पूछें।"
            if hi
            else "I did not catch a clear question. Ask about Goa, Vaani, or Hacker House Goa."
        )
    if hi:
        return (
            "यह मेरे ज्ञान आधार में नहीं है, इसलिए मैं अनुमान नहीं लगाऊँगी। "
            "पूछें: गोवा की राजधानी क्या है? वाणी क्या है? हैकर हाउस गोवा क्या है?"
        )
    return (
        "That is not in my knowledge base, so I will not guess. "
        "Try: What is the capital of Goa? What is Vaani? What is Hacker House Goa?"
    )
