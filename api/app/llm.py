from __future__ import annotations

from groq import Groq

from app.config import settings

_client: Groq | None = None


def groq_client() -> Groq | None:
    global _client
    if not settings.groq_api_key:
        return None
    if _client is None:
        # Rewrite runs off the 200ms clock; 2s was cutting Groq mid-sentence.
        _client = Groq(api_key=settings.groq_api_key, timeout=8.0)
    return _client
