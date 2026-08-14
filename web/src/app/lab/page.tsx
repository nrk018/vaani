"use client";

import { useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { fetchMetrics } from "@/lib/api";
import type { MetricsSnapshot, Percentiles } from "@/lib/types";

function Meter({ label, p }: { label: string; p?: Percentiles }) {
  if (!p) return null;
  const bar = (v: number) => Math.min(100, (v / 200) * 100);
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-sea/80">
        {label}
      </p>
      <div className="mt-4 grid grid-cols-3 gap-3">
        {(["p50", "p70", "p100"] as const).map((k) => (
          <div key={k}>
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/40">
              {k}
            </p>
            <p className="font-serif text-3xl tabular-nums text-gold">
              {p[k].toFixed(0)}
              <span className="text-sm text-white/40">ms</span>
            </p>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full bg-gradient-to-r from-sea to-gold"
                style={{ width: `${bar(p[k])}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <p className="mt-3 font-mono text-[10px] text-white/35">
        n={p.n} · mean {p.mean.toFixed(1)}ms
      </p>
    </div>
  );
}

export default function LabPage() {
  const [data, setData] = useState<MetricsSnapshot | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics()
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  const bench = data?.bench;
  const live = data?.live;

  return (
    <>
      <Nav active="lab" />
      <main className="mx-auto max-w-6xl px-6 pb-20 pt-24">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-sea/80">
          latency laboratory
        </p>
        <h1 className="mt-2 font-serif text-5xl text-white">P50 / P70 / P100</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-white/55">
          The scored clock is embed + retrieve + first generated token. STT and
          TTS are streamed around it. Numbers below come from the live harness
          ring and the last eval/results.json bench.
        </p>

        {err ? (
          <p className="mt-8 text-laterite">
            {err}. Start the API with <code>make api</code>.
          </p>
        ) : null}

        <section className="mt-10 grid gap-4 md:grid-cols-2">
          <Meter label="Bench RAG total" p={bench?.latency.rag} />
          <Meter label="Bench generate TTFT" p={bench?.latency.ttft} />
          <Meter label="Live RAG total" p={live?.rag} />
          <Meter label="Live generate TTFT" p={live?.ttft} />
        </section>

        {bench ? (
          <p className="mt-6 font-mono text-xs text-white/45">
            {bench.n} queries · {bench.under_200ms} under 200ms (
            {bench.under_200ms_pct}%) · grounded {bench.verdicts.GROUNDED ?? 0} ·
            refused {bench.verdicts.REFUSED ?? 0}
          </p>
        ) : (
          <p className="mt-6 text-sm text-white/40">
            Run <code className="text-gold">make bench</code> to write
            eval/results.json.
          </p>
        )}

        <h2 className="mt-14 font-serif text-3xl text-white">Node waterfall</h2>
        <div className="mt-4 overflow-x-auto rounded-2xl border border-white/10">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40">
              <tr>
                <th className="px-4 py-3">node</th>
                <th className="px-4 py-3">p50</th>
                <th className="px-4 py-3">p70</th>
                <th className="px-4 py-3">p100</th>
                <th className="px-4 py-3">n</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(bench?.latency.nodes ?? live?.nodes ?? {}).map(
                ([name, p]) => (
                  <tr key={name} className="border-t border-white/8">
                    <td className="px-4 py-2 font-mono text-xs text-gold/80">
                      {name}
                    </td>
                    <td className="px-4 py-2 tabular-nums">{p.p50.toFixed(1)}</td>
                    <td className="px-4 py-2 tabular-nums">{p.p70.toFixed(1)}</td>
                    <td className="px-4 py-2 tabular-nums">{p.p100.toFixed(1)}</td>
                    <td className="px-4 py-2 tabular-nums text-white/40">{p.n}</td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>

        <h2 className="mt-14 font-serif text-3xl text-white">Harness traces</h2>
        <ul className="mt-4 space-y-3">
          {(live?.traces ?? []).map((tr, i) => (
            <li
              key={i}
              className="rounded-2xl border border-white/10 bg-white/5 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-gold">
                  {tr.verdict}
                </span>
                <span className="font-mono text-xs text-sea">
                  {tr.rag_ms.toFixed(1)}ms rag · {tr.ttft_ms.toFixed(1)}ms ttft
                </span>
              </div>
              <p className="mt-2 text-sm text-white/70">{tr.answer}</p>
              <p className="mt-2 font-mono text-[10px] text-white/35">
                {tr.tools.join(" → ")}
              </p>
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
