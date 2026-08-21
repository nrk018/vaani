"use client";

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
        const wave = Math.sin(i * 0.31) * 0.5 + 0.5;
        const live = 10 + (wave * 26 + energy * 28) * (0.35 + (i % 7) / 10);
        const h = active ? Math.min(maxH, Math.round(live)) : base;
        return (
          <span
            key={i}
            className={`rounded-t-full bg-gradient-to-t from-[#0B6839]/50 to-[#FEE101] transition-[height,opacity] duration-150 ${
              variant === "dock" ? "min-w-0 flex-1" : "w-[3px]"
            } ${active ? "opacity-100" : "opacity-40"}`}
            style={{ height: `${h}px` }}
          />
        );
      })}
    </div>
  );
}
