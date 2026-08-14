# Vaani — voice-grounded RAG

**Vaani** (वाणी, “voice”) is a cinematic voice RAG studio for [Hacker House Goa 2026 Task 2](https://hhgoa.com/). Speak in English or Hindi. The orb transcribes with ElevenLabs Scribe, retrieves evidence from a multi-strategy MSMARCO-XI index plus a Goa knowledge pack, and speaks a grounded answer — or refuses.

Live target: RAG embed + retrieve + first generated token **under 200ms**, with P50 / P70 / P100 on `/lab`.

## Quick start

```bash
cp .env.example .env
# set GROQ_API_KEY and ELEVENLABS_API_KEY (optional for text-only RAG)

python3 -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
# optional multilingual-e5 + MSMARCO-XI:
# pip install -r api/requirements-ml.txt

make ingest          # local Goa pack + seed passages
make bench           # writes eval/results.json
make api             # FastAPI :8000
# in another terminal
make web             # Next.js :3000
```

Open [http://localhost:3000](http://localhost:3000). Type a question if you do not have Scribe keys: *What is the capital of Goa?* / *भारत की राजधानी क्या है?*

Scale the corpus (needs Hugging Face):

```bash
make ingest-xi       # + MSMARCO-XI hi,mr sample
```

## Architecture

```
Voice → Scribe v2 Realtime → inbound guard
     → hybrid retrieve (dense + BM25, RRF, parent expand)
     → Groq generate → outbound faithfulness
     → ElevenLabs Flash TTS
```

Chunking is **offline** and four-way: native passages, parent–child, semantic sentence groups, proposition slices. Query time never chunks.

## Repo

| Path | Role |
|---|---|
| `web/` | Next.js stage, lab, about |
| `api/` | FastAPI harness |
| `ingest/` | sampler + chunker + index builder |
| `knowledge/goa/` | Goa / HH Goa / Konkani pack |
| `eval/` | golden queries + bench |

## Deploy

**API (Fly.io)** — from the repo root:

```bash
fly auth login
fly launch --copy-config --no-deploy   # first time only; keep app name in fly.toml
fly secrets set GROQ_API_KEY=... ELEVENLABS_API_KEY=...
fly secrets set CORS_ORIGINS=https://YOUR-APP.vercel.app,http://localhost:3000
fly deploy
fly status
```

Health check: `https://<app>.fly.dev/v1/health`

**Frontend (Vercel)** — Root Directory = `web`:

```bash
cd web
npx vercel login
npx vercel --prod --yes
```

Set `NEXT_PUBLIC_API_URL` to the Fly URL (no trailing slash), then redeploy. Secrets stay in Fly / Vercel — never commit `.env`.

## Videos

See [`eval/DEMO.md`](eval/DEMO.md) for the 90s process script and the product demo script. Tag **#RAGInGoa**.
