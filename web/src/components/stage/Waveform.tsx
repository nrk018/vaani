"use client";

import { useEffect, useState } from "react";

const INLINE_BARS = 32;
const DOCK_BARS = 96;

function idleHeights(n: number) {
  return Array.from({ length: n }, (_, i) => {
    const wave = Math.sin(i * 0.31) * 0.5 + 0.5;
    return Math.round(4 + wave * 8);
  });
}

const INLINE_IDLE = idleHeights(INLINE_BARS);
const DOCK_IDLE = idleHeights(DOCK_BARS);

export function Waveform({
  active,
  energy,
  variant = "inline",
}: {
  active: boolean;
  energy: number;
  variant?: "inline" | "dock";
}) {
  const idle = variant === "dock" ? DOCK_IDLE : INLINE_IDLE;
  const maxH = variant === "dock" ? 52 : 40;
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    if (!active) return;
    let id = 0;
    const loop = (now: number) => {
      setPhase(now / 160);
      id = requestAnimationFrame(loop);
    };
    id = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(id);
  }, [active]);

  return (
    <div
      className={
        variant === "dock"
          ? "flex h-14 w-full items-end gap-px"
          : "flex h-10 items-end justify-center gap-[3px]"
      }
      aria-hidden
    >
      {idle.map((base, i) => {
        const pulse =
          (Math.sin(i * 0.31 + phase) * 0.5 + 0.5) * 0.65 +
          (Math.sin(i * 0.17 - phase * 1.35) * 0.5 + 0.5) * 0.35;
        const live = 6 + pulse * (18 + energy * 38) * (0.45 + (i % 7) / 12);
        const h = active ? Math.min(maxH, Math.round(live)) : base;
        return (
          <span
            key={i}
            className={`rounded-t-full bg-gradient-to-t from-[#0B6839]/50 to-[#FEE101] ${
              variant === "dock" ? "min-w-0 flex-1" : "w-[3px]"
            } ${active ? "opacity-100" : "opacity-40"}`}
            style={{ height: `${h}px` }}
          />
        );
      })}
    </div>
  );
}
