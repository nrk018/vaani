"use client";

import { useState } from "react";
import type { Citation } from "@/lib/types";

export function Constellation({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState<Citation | null>(null);
  const shown = citations.slice(0, 8);
  if (!shown.length) return null;

  return (
    <>
      <div className="pointer-events-none absolute inset-0">
        {shown.map((c, i) => {
          const angle = -Math.PI / 2 + (i / shown.length) * Math.PI * 2;
          const r = 42;
          const x = 50 + Math.cos(angle) * r;
          const y = 50 + Math.sin(angle) * r * 0.78;
          return (
            <button
              key={c.id}
              type="button"
              className="pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2 rounded-full border border-gold/40 bg-teal-950/80 px-2 py-1 text-[10px] tracking-wide text-gold/90 shadow-[0_0_18px_rgba(232,195,106,0.25)] backdrop-blur-sm transition hover:scale-105 hover:border-gold"
              style={{ left: `${x}%`, top: `${y}%` }}
              onClick={() => setOpen(c)}
            >
              {c.strategy}
              <span className="ml-1 text-sea/80">{c.score.toFixed(2)}</span>
            </button>
          );
        })}
      </div>
      {open ? (
        <div className="absolute bottom-4 left-1/2 z-20 w-[min(420px,90vw)] -translate-x-1/2 rounded-2xl border border-white/10 bg-[#071216]/95 p-4 shadow-2xl backdrop-blur-md">
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="font-serif text-lg text-gold">{open.title}</p>
            <button
              className="text-xs uppercase tracking-[0.2em] text-white/50 hover:text-white"
              onClick={() => setOpen(null)}
            >
              close
            </button>
          </div>
          <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-sea/80">
            {open.lang} · {open.source} · {open.strategy}
          </p>
          <p className="max-h-40 overflow-y-auto text-sm leading-relaxed text-white/75">
            {open.text}
          </p>
        </div>
      ) : null}
    </>
  );
}
