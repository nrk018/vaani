from __future__ import annotations

import httpx
from fastapi.responses import StreamingResponse

from app.config import settings

ELEVEN = "https://api.elevenlabs.io"


async def scribe_token() -> dict:
    if not settings.elevenlabs_api_key:
        return {"token": None, "error": "ELEVENLABS_API_KEY missing"}
    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.post(
            f"{ELEVEN}/v1/single-use-token/realtime_scribe",
            headers={"xi-api-key": settings.elevenlabs_api_key},
        )
        res.raise_for_status()
        data = res.json()
        return {"token": data.get("token") or data.get("single_use_token")}


async def tts_stream(text: str) -> StreamingResponse:
    if not settings.elevenlabs_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY missing")

    async def gen():
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{ELEVEN}/v1/text-to-speech/{settings.elevenlabs_voice_id}/stream",
                headers={
                    "xi-api-key": settings.elevenlabs_api_key,
                    "accept": "audio/mpeg",
                    "content-type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": settings.elevenlabs_tts_model,
                    "voice_settings": {
                        "stability": 0.48,
                        "similarity_boost": 0.8,
                        "style": 0.25,
                        "speed": 0.96,
                    },
                },
            ) as res:
                res.raise_for_status()
                async for chunk in res.aiter_bytes():
                    yield chunk

    return StreamingResponse(gen(), media_type="audio/mpeg")
