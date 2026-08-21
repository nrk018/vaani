from __future__ import annotations

from groq import Groq

from app.config import settings

_client: Groq | None = None


def groq_client() -> Groq | None:
    global _client
    if not settings.groq_api_key:
        return None
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key, timeout=2.0)
    return _client
