"use client";

import { useState } from "react";
import type { Citation } from "@/lib/types";

export function Constellation({
  citations,
  align = "start",
}: {
  citations: Citation[];
  align?: "start" | "center";
}) {
  const [open, setOpen] = useState<Citation | null>(null);
  const shown = citations.slice(0, 8);
  if (!shown.length) {
    return (
      <p className="text-xs leading-relaxed text-white/35">
        Evidence chips land here after a grounded ask.
      </p>
    );
  }

  return (
    <div className="relative z-10 w-full">
      <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.28em] text-sea/70">
        evidence
      </p>
      <div
        className={`flex flex-wrap gap-2 ${align === "center" ? "justify-center" : "justify-start"}`}
      >
        {shown.map((c) => (
          <button
            key={c.id}
            type="button"
            className="rounded-full border border-gold/45 bg-[#08532e]/80 px-2.5 py-1 text-[10px] tracking-wide text-gold shadow-[0_0_16px_rgba(254,225,1,0.22)] backdrop-blur-sm transition hover:scale-105 hover:border-gold"
            onClick={() => setOpen(c)}
          >
            {c.title.slice(0, 28) || c.strategy}
            <span className="ml-1 text-sea/90">{c.score.toFixed(2)}</span>
          </button>
        ))}
      </div>
      {open ? (
        <div className="mt-3 rounded-none border border-gold/30 bg-[#08532e]/95 p-4 shadow-[6px_8px_0_rgba(0,0,0,0.25)]">
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
    </div>
  );
}
