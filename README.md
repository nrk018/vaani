# Vaani — voice-grounded RAG

**Vaani** (वाणी, “voice”) is a voice-enabled Retrieval-Augmented Generation system for [Hacker House Goa 2026 Task 2](https://docs.google.com/document/d/1gzPyuYMaJGnv7mjPZ7Z_e20VxP0j5PMOPi8WmBi8rFk/edit?tab=t.0#heading=h.cozv1rf55la6).

A user speaks a question. The pipeline transcribes it, retrieves context from [ai4bharat/MSMARCO-XI](https://huggingface.co/datasets/ai4bharat/MSMARCO-XI) plus a Goa knowledge pack, and returns a grounded answer — or refuses.

Required pipeline shape from the brief:

```
Voice input → Speech-to-text → Chunking/Retrieval (vector DB) → Answer generation
```

Vaani implements that as:

```
Voice → ElevenLabs Scribe v2 Realtime → inbound guard
     → hybrid retrieve (FAISS HNSW + BM25, RRF, parent expand)
     → harnessed generate → outbound faithfulness
     → ElevenLabs Flash TTS
```

Repo: [github.com/nrk018/vaani](https://github.com/nrk018/vaani) · local UI: [http://localhost:3000](http://localhost:3000)

## Project details

| | |
|---|---|
| Product | Vaani (वाणी) |
| Task | HH Goa 2026 Shortlisting Task 2 — Voice-Enabled RAG |
| Brief | [Google Doc](https://docs.google.com/document/d/1gzPyuYMaJGnv7mjPZ7Z_e20VxP0j5PMOPi8WmBi8rFk/edit?tab=t.0#heading=h.cozv1rf55la6) |
| Dataset | [ai4bharat/MSMARCO-XI](https://huggingface.co/datasets/ai4bharat/MSMARCO-XI) (MS MARCO translated into Indic languages) plus `knowledge/goa/` |
| Languages | English, Hindi; Marathi as Konkani-nearest (MSMARCO-XI has no Konkani split) |
| Deadline | 22 August 2026, 11:59 PM |
| Hashtag | **#RAGInGoa** |

Chunking is **offline**. Query time never chunks. Last 100-query bench (`eval/results.json`): **P50 9.8ms · P70 10.2ms · P100 20.5ms · 100% under 200ms**.

## Tech stack

| Layer | Choice |
|---|---|
| Speech-to-text | **ElevenLabs Scribe v2 Realtime** (Sarvam was the other allowed option) |
| Text-to-speech | ElevenLabs Flash |
| Embeddings | `intfloat/multilingual-e5-small` (hashed n-gram fallback) |
| Vector index | FAISS HNSW (in-memory) |
| Sparse retrieve | BM25 (`rank-bm25`) |
| Fusion | Reciprocal Rank Fusion |
| Generation | Groq `openai/gpt-oss-20b`; extractive fallback when Groq would miss the 200ms budget |
| API harness | FastAPI + Uvicorn |
| Frontend | Next.js 16, React 19, Tailwind, Framer Motion, Paper mesh shaders |
| Eval | `eval/bench.py` → `/lab` P50 / P70 / P100 |
| Deploy | Vercel (`web/`) + Fly.io (`api/`) |

## Technical requirements

From the [task brief](https://docs.google.com/document/d/1gzPyuYMaJGnv7mjPZ7Z_e20VxP0j5PMOPi8WmBi8rFk/edit?tab=t.0#heading=h.cozv1rf55la6):

### 1. Speech-to-text

Use either Sarvam or ElevenLabs. **Vaani uses ElevenLabs Scribe v2 Realtime.** Chrome speech is only a fallback if the Scribe key is missing.

### 2. Chunking

Not a single naive fixed-size split. Four strategies over the same corpus (`ingest/chunk.py`), with overlap and metadata (`lang`, `source`, `strategy`, `title`, `query_type`):

| Strategy | Split |
|---|---|
| native | keep source passages |
| parent–child | ~100-token children, 20-token overlap; parent used at generate time |
| semantic | sentence groups with overlap |
| proposition | atomic claim slices for factoids |

Retrieve is hybrid dense + BM25, RRF, then parent expand. `make ingest-xi` samples MSMARCO-XI (`hi`, `mr`).

### 3. Latency target

The brief asks for chunking + retrieval + final output **under 200ms**. Chunking is precomputed. The scored hot path is embed + retrieve + first generated token. After warmup that path is extractive from retrieved passages when Groq’s typical TTFT (~590ms) would blow the budget.

### 4. Latency analytics

P50 / P70 / P100 across **100 queries** (not a single lucky run), written to `eval/results.json` and shown on `/lab`. Latest:

| | RAG ms |
|---|---|
| P50 | 9.79 |
| P70 | 10.19 |
| P100 | 20.45 |
| Under 200ms | 100 / 100 |

```bash
make bench
```

### 5. Harness

Not a raw prompt-in, text-out call. `api/app/harness.py` is a timed graph:

```
normalize → inbound_guard → retrieve → ground → (retrieve retry) → generate → outbound_guard → emit
```

Structured JSON / SSE, Groq timeout + extractive recovery, per-node timings.

### 6. Guardrails

The system knows when **not** to answer:

- inbound: empty, jailbreak, unsafe
- retrieval floor / off-topic (e.g. Champions League)
- outbound faithfulness (answer must overlap retrieved passages)
- refuse in the user’s language instead of guessing

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

Open [http://localhost:3000](http://localhost:3000). Type if you do not have Scribe keys: *What is the capital of Goa?* / *भारत की राजधानी क्या है?*

```bash
make ingest-xi       # + MSMARCO-XI hi,mr sample (needs Hugging Face)
```

## Repo

| Path | Role |
|---|---|
| `web/` | Next.js stage, lab, about |
| `api/` | FastAPI harness |
| `ingest/` | sampler + chunker + index builder |
| `knowledge/goa/` | Goa / HH Goa / Konkani pack |
| `eval/` | golden queries + bench + demo scripts |

## Submission

From the brief — no resubmissions:

- Form: https://forms.gle/MNvCjcv23Hn2Eeu58
- GitHub repo
- Live working link
- Two videos (process 90s + product demo)

Both videos must be posted to **Instagram and X by every team member**, not one shared post. At least one Instagram account must be public. Every post must include **#RAGInGoa**.

Scripts: [`eval/DEMO.md`](eval/DEMO.md).

## Deploy

**API (Fly.io)** — from the repo root:

```bash
fly auth login
fly launch --copy-config --no-deploy
fly secrets set GROQ_API_KEY=... ELEVENLABS_API_KEY=...
fly secrets set CORS_ORIGINS=https://YOUR-APP.vercel.app,http://localhost:3000
fly deploy
```

Health: `https://<app>.fly.dev/v1/health`

**Frontend (Vercel)** — Root Directory = `web`:

```bash
cd web
npx vercel login
npx vercel --prod --yes
```

Set `NEXT_PUBLIC_API_URL` to the Fly URL (no trailing slash). Never commit `.env`.
