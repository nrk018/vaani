# Hacker House Goa 2026

Hacker House Goa (HH Goa) is a builder residency and shortlisting program held in Goa, India. The 2026 cycle includes Task 2: a voice-enabled Retrieval-Augmented Generation (RAG) system.

## Task 2 — Voice-Enabled RAG

Builders must ship an end-to-end pipeline: a user speaks a question, speech is transcribed, relevant context is retrieved from a provided dataset, and a grounded answer is returned.

Required shape: Voice input → Speech-to-text → Chunking/Retrieval (vector DB) → Answer generation.

The dataset for the RAG pipeline is ai4bharat/MSMARCO-XI on Hugging Face — an Indic-language translation of MS MARCO. The original MS MARCO dataset (also written MSMARCO) was created by Microsoft from Bing search queries.

Speech-to-text must use either Sarvam or ElevenLabs. Vaani uses ElevenLabs Scribe v2 Realtime.

Chunking must be engineered: multiple strategies, overlap, semantic versus fixed-size splitting, and metadata-aware indexing. A single naive fixed-size split is not enough.

Latency target: chunking is offline. Online retrieval plus generation should complete in under 200 milliseconds. Submissions must report P50, P70, and P100 latency across many test queries.

The model must run inside a harness — structured orchestration with tool calls, retries, structured input/output, and error recovery — not a raw prompt-in, text-out call.

Guardrails are required: off-topic queries, unsafe inputs, hallucination checks, and answers that are not grounded in retrieved context. The system must know when not to answer.

## Submission

Fill the Google Form, share a GitHub repo, a live working link, and two videos. No resubmissions.

Video 1 (90 seconds) is a team/process video. Video 2 is an end-to-end product demo.

Both videos must be posted to Instagram, X, and LinkedIn by every team member with the hashtag #RAGInGoa. At least one Instagram account must be public.

Timeline: task launch 13 August 2026; deadline 22 August 2026, 11:59 PM IST.
