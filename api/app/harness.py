from __future__ import annotations

import json
import time
from collections.abc import Iterator

from app.config import settings
from app.guardrails import inbound, is_greeting, outbound, refuse_text, retrieval_floor
from app.metrics import metrics
from app.models import AskResponse, Citation, NodeTiming
from app.retrieve import detect_script, retrieve

SYSTEM = """You are Vaani, a voice-grounded assistant for Hacker House Goa.
Answer ONLY using the retrieved passages. If the passages do not contain the answer, say you do not have evidence.
Match the user's language (English, Hindi, or Marathi). Two or three short spoken sentences. No markdown. No preamble.
Never invent facts, dates, or names that are not in the passages.
If the user only greets you, greet back briefly and invite a question about Goa, Hacker House Goa, or Vaani.
"""


def _lang_of(query: str, hint: str | None) -> str:
    if hint:
        return hint
    script = detect_script(query)
    return "hi" if script == "deva" else "en"


def _context_block(citations: list[Citation]) -> str:
    lines = []
    for i, c in enumerate(citations, start=1):
        lines.append(f"[{i}] ({c.lang}/{c.strategy}/{c.source}) {c.title}: {c.text}")
    return "\n".join(lines)


def _extractive(query: str, citations: list[Citation], language: str) -> str:
    if not citations:
        return refuse_text(language, "no_evidence")
    top = citations[0]
    # Prefer the most overlapping sentence with the query
    q = set(query.lower().split())
    best = top.text
    best_score = -1
    for sent in top.text.replace("।", ".").split("."):
        sent = sent.strip()
        if len(sent) < 20:
            continue
        score = len(q & set(sent.lower().split()))
        if score > best_score:
            best_score = score
            best = sent
    if language.startswith("hi"):
        return f"{best.strip()}."
    return f"{best.strip()}."


def _groq_complete(query: str, citations: list[Citation], language: str) -> tuple[str, float]:
    if not settings.groq_api_key:
        t0 = time.perf_counter()
        text = _extractive(query, citations, language)
        return text, (time.perf_counter() - t0) * 1000

    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    t0 = time.perf_counter()
    ttft_ms = None
    chunks: list[str] = []
    stream = client.chat.completions.create(
        model=settings.groq_model,
        temperature=0,
        max_tokens=120,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Language: {language}\nQuestion: {query}\n\nPassages:\n{_context_block(citations)}",
            },
        ],
    )
    for event in stream:
        delta = event.choices[0].delta.content or ""
        if delta and ttft_ms is None:
            ttft_ms = (time.perf_counter() - t0) * 1000
        chunks.append(delta)
    if ttft_ms is None:
        ttft_ms = (time.perf_counter() - t0) * 1000
    return "".join(chunks).strip(), ttft_ms


def _groq_stream(query: str, citations: list[Citation], language: str) -> Iterator[tuple[str, float | None]]:
    """Yield (token, ttft_ms_once)."""
    if not settings.groq_api_key:
        text = _extractive(query, citations, language)
        yield text, 0.0
        return

    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    t0 = time.perf_counter()
    ttft_sent = False
    stream = client.chat.completions.create(
        model=settings.groq_model,
        temperature=0,
        max_tokens=120,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Language: {language}\nQuestion: {query}\n\nPassages:\n{_context_block(citations)}",
            },
        ],
    )
    for event in stream:
        delta = event.choices[0].delta.content or ""
        if not delta:
            continue
        ttft = None if ttft_sent else (time.perf_counter() - t0) * 1000
        ttft_sent = True
        yield delta, ttft


def run_ask(query: str, language_hint: str | None = None) -> AskResponse:
    t_all = time.perf_counter()
    tools: list[str] = ["normalize"]
    language = _lang_of(query, language_hint)
    timings: list[NodeTiming] = []

    t0 = time.perf_counter()
    ok, reason = inbound(query)
    timings.append(NodeTiming(node="inbound_guard", ms=(time.perf_counter() - t0) * 1000))
    tools.append("inbound_guard")
    if not ok:
        answer = refuse_text(language, reason or "unsafe")
        rag_ms = (time.perf_counter() - t_all) * 1000
        resp = AskResponse(
            answer=answer,
            verdict="REFUSED",
            language=language,
            citations=[],
            timings=timings,
            rag_ms=rag_ms,
            ttft_ms=rag_ms,
            refuse_reason=reason,
            tools=tools,
            model=settings.groq_model,
        )
        metrics.record(resp)
        return resp

    if is_greeting(query):
        answer = (
            "नमस्ते। मैं वाणी हूँ — गोवा, हैकर हाउस, या ज्ञान आधार से पूछें।"
            if language.startswith("hi")
            else "Dev borem korum. I am Vaani. Ask me about Goa, Hacker House Goa, or what is in the knowledge base."
        )
        rag_ms = (time.perf_counter() - t_all) * 1000
        resp = AskResponse(
            answer=answer,
            verdict="GROUNDED",
            language=language,
            citations=[],
            timings=timings,
            rag_ms=rag_ms,
            ttft_ms=rag_ms,
            refuse_reason=None,
            tools=tools + ["greet"],
            model="greet",
        )
        metrics.record(resp)
        return resp

    tools.append("retrieve")
    citations, retrieve_t = retrieve(query)
    for name, ms in retrieve_t.items():
        timings.append(NodeTiming(node=name, ms=ms))

    t1 = time.perf_counter()
    grounded, ground_reason = retrieval_floor(citations, settings.ground_min_dense, query)
    timings.append(NodeTiming(node="ground", ms=(time.perf_counter() - t1) * 1000))
    tools.append("ground")

    if not grounded:
        # one retrieve retry with a lightly expanded query
        tools.append("retrieve_retry")
        citations2, retrieve_t2 = retrieve(query + " " + " ".join(query.split()[:4]))
        citations = citations2 or citations
        for name, ms in retrieve_t2.items():
            timings.append(NodeTiming(node=f"retry_{name}", ms=ms))
        grounded, ground_reason = retrieval_floor(citations, settings.ground_min_dense * 0.9, query)

    if not grounded:
        answer = refuse_text(language, ground_reason or "no_evidence")
        rag_ms = (time.perf_counter() - t_all) * 1000
        resp = AskResponse(
            answer=answer,
            verdict="REFUSED",
            language=language,
            citations=citations[:3],
            timings=timings,
            rag_ms=rag_ms,
            ttft_ms=rag_ms,
            refuse_reason=ground_reason,
            tools=tools,
            model=settings.groq_model,
        )
        metrics.record(resp)
        return resp

    tools.append("generate")
    answer, ttft = _groq_complete(query, citations, language)
    timings.append(NodeTiming(node="generate_ttft", ms=ttft))

    tools.append("outbound_guard")
    t2 = time.perf_counter()
    verdict, overlap = outbound(answer, citations, False)
    timings.append(NodeTiming(node="outbound_guard", ms=(time.perf_counter() - t2) * 1000))
    refuse_reason = None

    rag_ms = (time.perf_counter() - t_all) * 1000
    resp = AskResponse(
        answer=answer,
        verdict=verdict,
        language=language,
        citations=citations,
        timings=timings,
        rag_ms=rag_ms,
        ttft_ms=ttft,
        refuse_reason=refuse_reason,
        tools=tools,
        model=settings.groq_model if settings.groq_api_key else "extractive",
    )
    metrics.record(resp)
    return resp


def iter_sse(query: str, language_hint: str | None = None) -> Iterator[str]:
    """SSE: meta, token, done. Citations known before generation."""
    t_all = time.perf_counter()
    language = _lang_of(query, language_hint)
    tools = ["normalize", "inbound_guard"]

    ok, reason = inbound(query)
    if not ok:
        answer = refuse_text(language, reason or "unsafe")
        payload = AskResponse(
            answer=answer,
            verdict="REFUSED",
            language=language,
            citations=[],
            timings=[NodeTiming(node="inbound_guard", ms=0)],
            rag_ms=(time.perf_counter() - t_all) * 1000,
            ttft_ms=0,
            refuse_reason=reason,
            tools=tools,
            model=settings.groq_model,
        )
        metrics.record(payload)
        yield _sse("meta", payload.model_dump())
        yield _sse("token", {"text": answer})
        yield _sse("done", payload.model_dump())
        return

    if is_greeting(query):
        answer = (
            "नमस्ते। मैं वाणी हूँ — गोवा, हैकर हाउस, या ज्ञान आधार से पूछें।"
            if language.startswith("hi")
            else "Dev borem korum. I am Vaani. Ask me about Goa, Hacker House Goa, or what is in the knowledge base."
        )
        payload = AskResponse(
            answer=answer,
            verdict="GROUNDED",
            language=language,
            citations=[],
            timings=[NodeTiming(node="inbound_guard", ms=0)],
            rag_ms=(time.perf_counter() - t_all) * 1000,
            ttft_ms=0,
            refuse_reason=None,
            tools=tools + ["greet"],
            model="greet",
        )
        metrics.record(payload)
        yield _sse("meta", payload.model_dump())
        yield _sse("token", {"text": answer})
        yield _sse("done", payload.model_dump())
        return

    citations, retrieve_t = retrieve(query)
    tools.append("retrieve")
    grounded, ground_reason = retrieval_floor(citations, settings.ground_min_dense, query)
    tools.append("ground")
    if not grounded:
        citations2, _ = retrieve(query)
        citations = citations2 or citations
        grounded, ground_reason = retrieval_floor(citations, settings.ground_min_dense * 0.9, query)

    timings = [NodeTiming(node=k, ms=v) for k, v in retrieve_t.items()]
    meta = {
        "language": language,
        "citations": [c.model_dump() for c in citations],
        "tools": tools,
        "timings": [t.model_dump() for t in timings],
        "verdict": "GROUNDED" if grounded else "REFUSED",
    }
    yield _sse("meta", meta)

    if not grounded:
        answer = refuse_text(language, ground_reason or "no_evidence")
        payload = AskResponse(
            answer=answer,
            verdict="REFUSED",
            language=language,
            citations=citations[:3],
            timings=timings,
            rag_ms=(time.perf_counter() - t_all) * 1000,
            ttft_ms=0,
            refuse_reason=ground_reason,
            tools=tools,
            model=settings.groq_model,
        )
        metrics.record(payload)
        yield _sse("token", {"text": answer})
        yield _sse("done", payload.model_dump())
        return

    tools.append("generate")
    pieces: list[str] = []
    ttft = 0.0
    for token, maybe_ttft in _groq_stream(query, citations, language):
        if maybe_ttft is not None:
            ttft = maybe_ttft
            yield _sse("ttft", {"ms": ttft})
        pieces.append(token)
        yield _sse("token", {"text": token})

    answer = "".join(pieces).strip()
    tools.append("outbound_guard")
    verdict, _ = outbound(answer, citations, False)
    refuse_reason = None

    rag_ms = (time.perf_counter() - t_all) * 1000
    timings.append(NodeTiming(node="generate_ttft", ms=ttft))
    payload = AskResponse(
        answer=answer,
        verdict=verdict,
        language=language,
        citations=citations,
        timings=timings,
        rag_ms=rag_ms,
        ttft_ms=ttft,
        refuse_reason=refuse_reason,
        tools=tools,
        model=settings.groq_model if settings.groq_api_key else "extractive",
    )
    metrics.record(payload)
    yield _sse("done", payload.model_dump())


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
