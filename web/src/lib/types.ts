export type GuardVerdict = "GROUNDED" | "LOW_CONFIDENCE" | "REFUSED";

export type Citation = {
  id: string;
  title: string;
  text: string;
  lang: string;
  source: string;
  strategy: string;
  score: number;
  parent_id: string;
};

export type NodeTiming = {
  node: string;
  ms: number;
};

export type TokenInfo = {
  replace?: boolean;
  source?: "extractive" | "groq" | string;
};

export type AskResult = {
  answer: string;
  verdict: GuardVerdict;
  language: string;
  citations: Citation[];
  timings: NodeTiming[];
  rag_ms: number;
  ttft_ms: number | null;
  refuse_reason: string | null;
  tools: string[];
  model: string;
};

export type Percentiles = {
  n: number;
  p50: number;
  p70: number;
  p100: number;
  mean: number;
};

export type MetricsSnapshot = {
  live: {
    rag: Percentiles;
    ttft: Percentiles;
    nodes: Record<string, Percentiles>;
    verdicts: Record<string, number>;
    traces: Array<{
      answer: string;
      verdict: string;
      rag_ms: number;
      ttft_ms: number;
      tools: string[];
      citations: Array<{ title: string; strategy: string; score: number }>;
    }>;
  };
  bench: {
    n: number;
    under_200ms: number;
    under_200ms_pct: number;
    latency: {
      rag: Percentiles;
      ttft: Percentiles;
      nodes: Record<string, Percentiles>;
    };
    verdicts: Record<string, number>;
    index?: Record<string, unknown>;
  } | null;
};

export type Health = {
  ok: boolean;
  warm: boolean;
  groq: boolean;
  elevenlabs: boolean;
  index: {
    n_chunks: number;
    dim: number;
    embedder: string;
    faiss: boolean;
    langs?: string[];
    strategies?: string[];
  };
};

export type Turn = {
  id: string;
  role: "user" | "vaani";
  text: string;
  partial?: boolean;
  result?: AskResult;
};

export type OrbState = "idle" | "listening" | "thinking" | "speaking";
