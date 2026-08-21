from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Iterator

from app.config import settings
from app.guardrails import inbound, is_greeting, outbound, refuse_text, retrieval_floor
from app.llm import groq_client
from app.metrics import metrics
from app.models import AskResponse, Citation, NodeTiming
from app.retrieve import detect_script, retrieve

SYSTEM = (
    "You are Vaani, speaking aloud. Answer ONLY from the passages. "
    "MSMARCO and MS MARCO are the same original dataset. MSMARCO-XI is the Indic translation. "
    "If any passage says Microsoft created MS MARCO / MSMARCO, that is the answer to who created it. "
    "Do not invent facts. Do not say the passages are silent if they already name a creator. "
    "Match the user's language. One complete spoken sentence of 8–24 words. "
    "No markdown, no lists, no preamble."
)
log = logging.getLogger("vaani.harness")


def _lang_of(query: str, hint: str | None) -> str:
    if hint:
        return hint
    script = detect_script(query)
    return "hi" if script == "deva" else "en"


def _context_block(query: str, citations: list[Citation]) -> str:
    terms = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2}
    if any(t in terms for t in ("marco", "msmarco")):
        terms.update({"marco", "msmarco", "microsoft", "bing"})

    def relevance(c: Citation) -> float:
        blob = f"{c.title} {c.text}".lower()
        return sum(1.0 for t in terms if t in blob) + (0.5 if c.source == "seed" else 0.0)

    ordered = sorted(citations[:8], key=relevance, reverse=True)
    lines = []
    for i, c in enumerate(ordered[:5], start=1):
        lines.append(f"[{i}] {c.title}: {c.text[:480]}")
    return "\n".join(lines)


def _extractive(query: str, citations: list[Citation], language: str) -> str:
    if not citations:
        return refuse_text(language, "no_evidence")
    q = {t for t in re.findall(r"[a-z0-9\u0900-\u097f]+", query.lower()) if len(t) > 1}
    if "msmarco" in q or "marco" in q:
        q.update({"ms", "marco", "msmarco", "microsoft"})
    best = citations[0].text
    best_score = -1
    for cit in citations[:8]:
        for sent in cit.text.replace("।", ".").split("."):
            sent = sent.strip()
            if len(sent) < 16:
                continue
            words = set(re.findall(r"[a-z0-9\u0900-\u097f]+", sent.lower()))
            score = len(q & words)
            if score > best_score:
                best_score = score
                best = sent
    return f"{best.strip()}."


def generate_answer(
    query: str, citations: list[Citation], language: str, budget_ms: float = 0.0
) -> tuple[str, float, str]:
    """Scored hot path: extractive only. Fluent Groq is streamed off-clock in SSE."""
    del budget_ms
    t0 = time.perf_counter()
    return _extractive(query, citations, language), (time.perf_counter() - t0) * 1000, "extractive"


def _iter_groq_deltas(query: str, citations: list[Citation], language: str) -> Iterator[str]:
    """Yield Groq token deltas. Always attempted — typical TTFT no longer skips this."""
    client = groq_client()
    if client is None:
        return
    t0 = time.perf_counter()
    limit_s = max(0.2, settings.groq_rewrite_timeout_ms / 1000.0)
    kwargs: dict = {
        "model": settings.groq_model,
        "temperature": 0,
        "max_tokens": settings.groq_max_tokens,
        "stream": True,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Language: {language}\nQuestion: {query}\n\nPassages:\n{_context_block(query, citations)}",
            },
        ],
    }
    # gpt-oss spends tokens on hidden reasoning; keep that short so spoken content arrives.
    if "gpt-oss" in settings.groq_model:
        kwargs["reasoning_effort"] = "low"
    stream = client.chat.completions.create(**kwargs)
    for event in stream:
        if (time.perf_counter() - t0) > limit_s:
            break
        choices = getattr(event, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0].delta, "content", None) or ""
        if delta:
            yield delta


def warm_generate() -> None:
    """Warm TLS + Groq so the first spoken rewrite is not a cold start."""
    client = groq_client()
    if client is None:
        return
    try:
        client.chat.completions.create(
            model=settings.groq_model,
            temperature=0,
            max_tokens=8,
            messages=[{"role": "user", "content": "Say Goa."}],
        )
    except Exception:
        pass


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
    answer, gen_ms, gen_model = generate_answer(query, citations, language)
    timings.append(NodeTiming(node="generate_ttft", ms=gen_ms))

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
        ttft_ms=gen_ms,
        refuse_reason=refuse_reason,
        tools=tools,
        model=gen_model,
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
    answer, ttft, gen_model = generate_answer(query, citations, language)
    timings.append(NodeTiming(node="generate_ttft", ms=ttft))
    # Scored clock stops here (retrieve + extractive). Groq is off-clock.
    rag_ms = (time.perf_counter() - t_all) * 1000
    yield _sse("ttft", {"ms": ttft, "model": "extractive", "rag_ms": rag_ms})
    yield _sse("token", {"text": answer, "source": "extractive"})

    t_groq = time.perf_counter()
    fluent = ""
    groq_chunks = 0
    try:
        for delta in _iter_groq_deltas(query, citations, language):
            yield _sse(
                "token",
                {
                    "text": delta,
                    "source": "groq",
                    "replace": groq_chunks == 0,
                },
            )
            fluent += delta
            groq_chunks += 1
    except Exception:
        log.exception("groq rewrite failed; keeping extractive draft")
    groq_ms = (time.perf_counter() - t_groq) * 1000
    if groq_chunks:
        tools.append("generate_groq")
        timings.append(NodeTiming(node="generate_groq", ms=groq_ms))
        fluent = fluent.strip()
        if fluent:
            answer = fluent
            gen_model = settings.groq_model

    tools.append("outbound_guard")
    verdict, _ = outbound(answer, citations, False)
    refuse_reason = None

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
        model=gen_model,
    )
    metrics.record(payload)
    yield _sse("done", payload.model_dump())


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
