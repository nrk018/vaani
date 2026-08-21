import type { AskResult, Health, MetricsSnapshot } from "./types";

export const API =
  typeof window === "undefined"
    ? process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000"
    : "/backend";

async function parseSseAsk(
  query: string,
  language: string | undefined,
  onToken: (t: string) => void,
  onMeta: (m: Partial<AskResult>) => void,
): Promise<AskResult> {
  const res = await fetch(`${API}/v1/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, language, stream: true }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`ask failed: ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let answer = "";
  let donePayload: AskResult | null = null;
  let event = "message";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const block of parts) {
      let dataLine = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) dataLine += line.slice(5).trim();
      }
      if (!dataLine) continue;
      const data = JSON.parse(dataLine);
      if (event === "token") {
        answer += data.text || "";
        onToken(data.text || "");
      } else if (event === "meta") {
        onMeta(data);
      } else if (event === "done") {
        donePayload = data as AskResult;
      }
      event = "message";
    }
  }
  if (donePayload) return donePayload;
  return {
    answer,
    verdict: "GROUNDED",
    language: language || "en",
    citations: [],
    timings: [],
    rag_ms: 0,
    ttft_ms: null,
    refuse_reason: null,
    tools: [],
    model: "",
  };
}

export async function askStream(
  query: string,
  onToken: (t: string) => void,
  onMeta: (m: Partial<AskResult>) => void,
  language?: string,
): Promise<AskResult> {
  return parseSseAsk(query, language, onToken, onMeta);
}

export async function fetchHealth(): Promise<Health> {
  const res = await fetch(`${API}/v1/health`);
  if (!res.ok) throw new Error("health failed");
  return res.json();
}

export async function fetchMetrics(): Promise<MetricsSnapshot> {
  const res = await fetch(`${API}/v1/metrics`);
  if (!res.ok) throw new Error("metrics failed");
  return res.json();
}

export async function fetchScribeToken(): Promise<string | null> {
  const res = await fetch(`${API}/v1/session/scribe-token`, { method: "POST" });
  if (!res.ok) return null;
  const data = await res.json();
  return data.token ?? null;
}

export async function speak(text: string): Promise<ArrayBuffer> {
  const res = await fetch(`${API}/v1/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`tts failed: ${res.status}`);
  const buf = await res.arrayBuffer();
  if (buf.byteLength < 64) throw new Error("tts returned empty audio");
  return buf;
}
