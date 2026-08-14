from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

GuardVerdict = Literal["GROUNDED", "LOW_CONFIDENCE", "REFUSED"]
OrbState = Literal["idle", "listening", "thinking", "speaking"]


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    language: Optional[str] = None
    stream: bool = True


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: Optional[str] = None


class Citation(BaseModel):
    id: str
    title: str
    text: str
    lang: str
    source: str
    strategy: str
    score: float
    parent_id: str


class NodeTiming(BaseModel):
    node: str
    ms: float


class AskResponse(BaseModel):
    answer: str
    verdict: GuardVerdict
    language: str
    citations: list[Citation]
    timings: list[NodeTiming]
    rag_ms: float
    ttft_ms: Optional[float] = None
    refuse_reason: Optional[str] = None
    tools: list[str] = []
    model: str = ""


class HealthResponse(BaseModel):
    ok: bool
    warm: bool
    index: dict[str, Any]
    groq: bool
    elevenlabs: bool
