"use client";

import type { AskResult, Citation } from "@/lib/types";
import { Constellation } from "./Constellation";

export function LatencyHud({
  result,
  citations = [],
}: {
  result: AskResult | null;
  citations?: Citation[];
}) {
  const nodes = result?.timings ?? [];
  const rag = result?.rag_ms;
  const ok = rag !== undefined && rag < 200;

  return (
    <aside className="flex h-full flex-col gap-6 overflow-y-auto p-5">
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-sea/70">
          instrument
        </p>
        <h2 className="font-serif text-2xl text-white/90">Latency</h2>
        <p className="mt-1 font-mono text-xs text-white/40">RAG budget 200ms</p>
        <div className="mt-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">
            last RAG
          </p>
          <p
            className={`font-serif text-5xl tabular-nums ${ok ? "text-sea" : "text-laterite"}`}
          >
            {rag !== undefined ? rag.toFixed(0) : "—"}
            <span className="ml-1 text-lg text-white/40">ms</span>
          </p>
        </div>
        <ul className="mt-5 space-y-2">
          {nodes.map((n) => (
            <li key={n.node} className="flex items-center justify-between gap-3">
              <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/45">
                {n.node}
              </span>
              <span className="font-mono text-xs tabular-nums text-gold/80">
                {n.ms.toFixed(1)}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <Constellation citations={citations} align="start" />

      {result ? (
        <div className="mt-auto rounded-xl border border-white/10 p-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-gold/70">
            {result.verdict}
            {result.model ? ` · ${result.model}` : ""}
          </p>
          <p className="mt-1 text-xs text-white/50">{result.tools.join(" → ")}</p>
        </div>
      ) : (
        <p className="mt-auto text-xs text-white/35">
          Ask something. The waterfall fills from a real harness, not a mock.
        </p>
      )}
    </aside>
  );
}
