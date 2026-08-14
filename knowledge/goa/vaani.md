# Vaani

Vaani (वाणी) is a voice-grounded RAG studio built for Hacker House Goa 2026 Task 2. A user speaks. ElevenLabs Scribe transcribes. A hybrid index retrieves evidence from MSMARCO-XI (English, Hindi, Marathi) plus a Goa knowledge pack. A harnessed generator answers only from that evidence. ElevenLabs Flash speaks the answer back.

Vaani never chunks at query time. Four chunking strategies run offline: native MS MARCO passages, parent-child hierarchical windows, semantic breakpoint splits, and proposition (atomic fact) slices. At query time, dense kNN and BM25 run in parallel, Reciprocal Rank Fusion merges them, and parent passages are expanded for generation.

If retrieval scores are weak, if the question is off-corpus, or if the draft answer is not faithful to the passages, Vaani refuses. It is designed to know when not to answer.

The latency lab reports P50, P70, and P100 for embed, BM25, dense retrieve, fuse, generation time-to-first-token, and RAG total. The scored budget is embed + retrieve + first generated token, targeting under 200ms.
