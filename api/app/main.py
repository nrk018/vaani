from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
from app.eleven import scribe_token, tts_stream
from app.harness import iter_sse, run_ask
from app.index_store import store
from app.metrics import metrics
from app.models import AskRequest, HealthResponse, SpeakRequest


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.load_or_build()
    yield


app = FastAPI(title="Vaani", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        warm=store.warm,
        index=store.info(),
        groq=bool(settings.groq_api_key),
        elevenlabs=bool(settings.elevenlabs_api_key),
    )


@app.post("/v1/ask")
def ask(body: AskRequest):
    if body.stream:
        return StreamingResponse(
            iter_sse(body.query, body.language),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return run_ask(body.query, body.language)


@app.post("/v1/ask/sync")
def ask_sync(body: AskRequest):
    return run_ask(body.query, body.language)


@app.post("/v1/session/scribe-token")
async def session_scribe_token():
    try:
        return await scribe_token()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/speak")
async def speak(body: SpeakRequest):
    try:
        return await tts_stream(body.text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/v1/metrics")
def get_metrics():
    snap = metrics.snapshot()
    disk = settings.root / "eval" / "results.json"
    bench = None
    if disk.exists():
        bench = json.loads(disk.read_text(encoding="utf-8"))
    return {"live": snap, "bench": bench}


@app.get("/v1/lab/results")
def lab_results():
    disk = settings.root / "eval" / "results.json"
    if not disk.exists():
        return {"error": "no bench yet", "live": metrics.snapshot()}
    return json.loads(disk.read_text(encoding="utf-8"))
